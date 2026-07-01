"""认知消化流水线调度器 v0.2 — 多Agent分工协作

v0.2 核心升级（基于学习科学文献优化）:
- 6 Agent 均匀分工，每 Agent 约束数 3-5（vs v0.1 单体 18 条）
- 引入逐句简化 Agent（借鉴 EaseText）
- 类比生成独立为专职 Agent（1 个精准类比 > 4 个牵强）
- 六层组装降级为轻量格式编排（不做深度加工）
- 认知钩子独立生成（聚焦生成效应 + 精细加工）
- 语感润色（去 AI 味）

管线:
  Assess → FragmentSimplify → AnalogyPair → LayerAssemble → CognitiveHook → Polish
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

from agent_core import ModelRegistry

from agent_digester.core.output import DigestedOutput, SkeletonPoint
from agent_digester.models.profile import UserProfile


class DigestionPhase(str, Enum):
    ASSESS = "assess"
    SIMPLIFY = "simplify"
    ANALOGY = "analogy"
    ASSEMBLE = "assemble"
    HOOK = "hook"
    POLISH = "polish"


@dataclass
class PhaseResult:
    phase: DigestionPhase
    success: bool
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    cost_usd: float = 0.0


@dataclass
class DigestionResult:
    success: bool
    phases: dict[DigestionPhase, PhaseResult] = field(default_factory=dict)
    total_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0
    final_output: Optional[DigestedOutput] = None
    summary: str = ""


def _safe_json(text: str) -> str:
    """从 LLM 响应中安全提取 JSON"""
    text = text.strip()
    for pattern in [r'```(?:json)?\s*\n?(.*?)\n?```', r'\{.*\}', r'\[.*\]']:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            return m.group(1) if '```' in m.group(0) else m.group(0)
    return text


def _parse_json(text: str) -> dict:
    return json.loads(_safe_json(text))


# ═══════════════════════════════════════════════
# Agent Prompt 模板
# ═══════════════════════════════════════════════

PROMPT_ASSESS = """分析文本的认知难度。只输出纯JSON。

{"level":"easy|medium|hard","core_thesis":"一句话核心论点","key_terms":[{"term":"术语","explanation":"简短解释"}],"blockers":["阻碍理解的3个最大障碍"],"structure":"文本的逻辑结构描述"}

只输出JSON，不要其他文字。"""

PROMPT_SIMPLIFY = """你是一个专业文本简化引擎。将复杂文本逐句改写为朴实、清晰的中文。

规则（只遵守这3条）:
1. 替换生僻术语为日常表达（保留原术语在括号中）
2. 拆解长句，每句不超过30字
3. 不丢失原意，不添加自己的理解

输出格式（纯JSON）:
{"simplified":"简化后完整文本","changes":["改动1","改动2"]}

只输出JSON。"""

PROMPT_ANALOGY = """为核心概念生成一个精准的类比。宁缺毋滥。

要求:
1. 类比源来自{DOMAIN}领域
2. 类比必须抓住概念的本质结构，不是表面相似
3. 包含: 场景→映射→洞见→边界→备选

输出格式（纯JSON）:
{"analogy_scene":"具象场景（2-3句）","mapping":{"概念A":"类比X","概念B":"类比Y"},"core_insight":"本质洞见","boundary":"类比局限性","alternative":"备选视角"}

只输出JSON。"""

PROMPT_ASSEMBLE = """将已简化的文本和类比，组装为6层消化输出。

你有3个输入:
- simplified_text: 已逐句简化好的文本
- analogy: 已生成好的精准类比
- assessment: 难度评估和核心论点

你只需要把材料组装成6层格式。可以做适度提炼，但不要添加原文没有的实质性内容。

输出格式（纯JSON）:
{"layer0_analogy":"一句话类比画面","layer1_essence":"一句话核心","layer2_why":"这个概念为什么值得理解（思想价值，不要关联用户职业）","layer3_entry":"从类比场景过渡到概念","layer4_skeleton":[{"title":"要点标题","content":"要点内容"}],"layer5_action":"一个开放问题（以？结尾）"}

约束:
- layer4 的点数 = 3，不能多
- 每个 content 不超过 80 字
- layer5 是问题形式
- layer2 不要提到具体职业

只输出JSON。"""

PROMPT_HOOK = """基于内容，设计一个认知钩子。只做一个。

类型选一个:
- 反直觉提问: 提出表面与内容矛盾的现象
- 极端延伸: 把概念推到极端情况
- 个人对照: 让读者对照自己经历检验概念

输出格式（纯JSON）:
{"type":"反直觉提问|极端延伸|个人对照","hook":"钩子内容（2-3句，末句必须是问句）","why_it_sticks":"为什么有效"}

只输出JSON。"""

PROMPT_POLISH = """为已消化的文本做最后润色。

只做三件事:
1. 删除AI写作痕迹（"值得注意的是"、"综上所述"、"从某种程度上说"）
2. 确保句子长短交替
3. 让人感觉像在跟朋友对话

输入是JSON格式，输出润色后的JSON（相同结构，只改文本内容）。只输出JSON。"""


# ═══════════════════════════════════════════════
# 轻量 Agent（独立部署，不依赖 agent-digester 包循环）
# ═══════════════════════════════════════════════

class _Agent:
    """内部轻量Agent — 每个Agent独立运行，约束数 3-5"""
    
    def __init__(self, registry, name, system_prompt):
        self.registry = registry
        self.name = name
        self.system = system_prompt
    
    def execute(self, user_prompt, temperature=0.3, max_tokens=2048):
        model_key, spec = self.registry.get_agent_model(self.name, "primary")
        client = self.registry.get_client(model_key)
        
        response = client.chat.completions.create(
            model=spec.model_id,
            messages=[
                {"role": "system", "content": self.system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        usage = response.usage
        cost = self.registry.estimate_cost(
            model_key,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )
        
        return response.choices[0].message.content or "", cost


class DigestionPipeline:
    """认知消化流水线 v0.2 — 6 Agent 分工"""

    def __init__(
        self,
        config_path: str = "config/models.yaml",
        user_profile: Optional[UserProfile] = None,
        domain: str = "日常经验",
        translator=None,
    ):
        self.registry = ModelRegistry(config_path)
        self.profile = user_profile
        self.domain = domain
        self.translator = translator
        
        self._agents = {}

    def _get_agent(self, name, prompt):
        if name not in self._agents:
            self._agents[name] = _Agent(self.registry, name, prompt)
        return self._agents[name]

    async def digest(
        self,
        text: str,
        title: str = "",
        source_lang: str = "zh",
        source_type: str = "article",
        on_phase_complete: Optional[Callable] = None,
    ) -> DigestionResult:
        """执行完整消化流水线"""
        total_start = time.time()
        phases = {}
        total_cost = 0.0
        
        domain = self.domain

        def record(phase, data, cost, elapsed, success=True, errors=None):
            pr = PhaseResult(
                phase=phase, success=success, data=data,
                duration_seconds=elapsed, cost_usd=cost,
                errors=errors or [],
            )
            phases[phase] = pr
            if on_phase_complete:
                on_phase_complete(phase, pr)
            return pr

        # ── 翻译前置（可选） ──
        if source_lang != "zh" and self.translator:
            try:
                tr = await self.translator.run(
                    source_text=text, title=title,
                    source_lang=source_lang, require_human_approval=False,
                )
                if tr.success and tr.final_output:
                    text = tr.final_output.get("final_text", text)
            except Exception as e:
                record(DigestionPhase.ASSESS, {}, 0, 0, False, [str(e)])
                return DigestionResult(success=False, phases=phases,
                    total_duration_seconds=time.time()-total_start)

        # ── Agent 1: 难度评估 ──
        st = time.time()
        resp, cost = self._get_agent("a1_assess", PROMPT_ASSESS).execute(
            f"文本:\n{text[:8000]}", temperature=0.1
        )
        total_cost += cost
        try:
            assessment = _parse_json(resp)
        except:
            assessment = {"level": "medium", "core_thesis": text[:100]}
        record(DigestionPhase.ASSESS, assessment, cost, time.time()-st)

        # ── Agent 2: 逐句简化 ──
        st = time.time()
        resp, cost = self._get_agent("a2_simplify", PROMPT_SIMPLIFY).execute(
            f"文本:\n{text}"
        )
        total_cost += cost
        try:
            simplified = _parse_json(resp)
        except:
            simplified = {"simplified": text, "changes": []}
        record(DigestionPhase.SIMPLIFY, simplified, cost, time.time()-st)
        simp_text = simplified.get("simplified", text)

        # ── Agent 3: 类比生成 ──
        st = time.time()
        core = assessment.get("core_thesis", "")
        resp, cost = self._get_agent("a3_analogy", PROMPT_ANALOGY.replace("{DOMAIN}", domain)).execute(
            f"核心论点: {core}\n\n简化文本: {simp_text[:500]}"
        )
        total_cost += cost
        try:
            analogy = _parse_json(resp)
        except:
            analogy = {"analogy_scene": "", "core_insight": ""}
        record(DigestionPhase.ANALOGY, analogy, cost, time.time()-st)

        # ── Agent 4: 六层组装 ──
        st = time.time()
        resp, cost = self._get_agent("a4_assemble", PROMPT_ASSEMBLE).execute(
            f"simplified_text: {simp_text}\n\nanalogy: {json.dumps(analogy, ensure_ascii=False)}\n\nassessment: {json.dumps(assessment, ensure_ascii=False)}"
        )
        total_cost += cost
        try:
            assembled = _parse_json(resp)
        except:
            assembled = {"layer1_essence": core, "layer4_skeleton": []}
        record(DigestionPhase.ASSEMBLE, assembled, cost, time.time()-st)

        # ── Agent 5: 认知钩子 ──
        st = time.time()
        resp, cost = self._get_agent("a5_hook", PROMPT_HOOK).execute(
            f"核心内容: {core}\n\n要点: {json.dumps(assembled.get('layer4_skeleton',[]), ensure_ascii=False)}"
        )
        total_cost += cost
        try:
            hook = _parse_json(resp)
            assembled["layer5_action"] = hook.get("hook", assembled.get("layer5_action", ""))
        except:
            pass
        record(DigestionPhase.HOOK, hook if 'hook' in dir() else {}, cost, time.time()-st)

        # ── Agent 6: 润色 ──
        st = time.time()
        resp, cost = self._get_agent("a6_polish", PROMPT_POLISH).execute(
            json.dumps(assembled, ensure_ascii=False)
        )
        total_cost += cost
        try:
            final = _parse_json(resp)
        except:
            final = assembled
        record(DigestionPhase.POLISH, final, cost, time.time()-st)

        # ── 构建 DigestedOutput ──
        points = final.get("layer4_skeleton", [])
        output = DigestedOutput(
            core_analogy=final.get("layer0_analogy", ""),
            one_line_essence=final.get("layer1_essence", ""),
            why_you_care=final.get("layer2_why", ""),
            concrete_entry=final.get("layer3_entry", ""),
            abstract_ascent="",
            skeleton_points=[
                SkeletonPoint(title=p.get("title",""), content=p.get("content",""))
                for p in points
            ],
            micro_action=final.get("layer5_action", ""),
            source_title=title,
            source_type=source_type,
            difficulty_level=assessment.get("level", "medium"),
            digested_by="v0.2_6agent",
        )

        total_time = time.time() - total_start
        success = all(p.success for p in phases.values())

        return DigestionResult(
            success=success, phases=phases,
            total_duration_seconds=total_time,
            total_cost_usd=total_cost,
            final_output=output,
            summary=self._build_summary(phases, total_cost, total_time),
        )

    def digest_sync(self, text, title="", **kw):
        return asyncio.run(self.digest(text=text, title=title, **kw))

    def _build_summary(self, phases, cost, duration):
        lines = ["=" * 60, "  认知消化 v0.2 | 6 Agent 分工", "=" * 60,
                 f"  耗时: {duration:.1f}s | 成本: ${cost:.4f}", ""]
        for p, r in phases.items():
            lines.append(f"  {'✅' if r.success else '❌'} {p.value} ({r.duration_seconds:.1f}s)")
        return "\n".join(lines)
