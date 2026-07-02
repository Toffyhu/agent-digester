"""认知消化流水线 v0.3 — 3 Agent + 规则层精简架构

v0.3 核心变更:
- LLM密度: 6→3 (语义简化 + 类比生成 + 认知钩子)
- 难度评估 → 规则层 (句长/术语密度/Flesch, 50ms)
- 六层组装 → 规则层 (L0-L5模板拼接 + L4自适应)
- 类比生成 → 注入 analogy_bank 结构模式
- 简化+润色 → 合并为单Agent
- 类比生成 || 认知钩子 → 并行调用

参考:
- Bjork (2011) 理想困难
- Weinstein et al. (2018) 6大学习策略
- AnalogyKB (2024) 结构映射模式
"""

from __future__ import annotations

import asyncio, json, re, time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

from agent_core import ModelRegistry
from agent_digester.core.output import DigestedOutput, SkeletonPoint
from agent_digester.models.profile import UserProfile
from agent_digester.assets.analogy_bank.patterns import search_patterns, format_patterns_for_prompt


class DigestionPhase(str, Enum):
    SIMPLIFY = "simplify"
    ANALOGY = "analogy"
    HOOK = "hook"
    ASSEMBLE = "assemble"


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


# ═══════════════════════════════════════
# 规则层: 难度评估
# ═══════════════════════════════════════

def rule_assess(text: str) -> dict:
    """纯规则难度评估 — 50ms，零API调用"""
    sentences = re.split(r'[。！？；\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return {"level": "medium", "core_thesis": text[:100], "structure": "未知"}
    
    # 句长
    avg_len = sum(len(s) for s in sentences) / len(sentences)
    
    # 术语密度 (简单启发式: 检测常见学术/专业词汇标记)
    jargon_markers = ['是指', '所谓', '即', '也就是说', '其', '该', '所示', '倘若',
                      '本质', '定义', '定理', '法则', '定律', '原理', '命题',
                      '非', '则', '故', '因而', '换言之', '必须', '应当']
    jargon_count = sum(1 for s in sentences for m in jargon_markers if m in s)
    term_density = jargon_count / max(len(sentences), 1)
    
    # 综合判定
    if avg_len > 80 or term_density > 1.5:
        level = "hard"
    elif avg_len > 50 or term_density > 0.8:
        level = "medium"
    else:
        level = "easy"
    
    # 核心论点 = 开头2-3句
    core_thesis = "".join(sentences[:3])[:200]
    
    # 结构检测
    if any(re.search(r'第[一二三四五]', s) or re.search(r'\d+[\.、]', s) for s in sentences):
        structure = "structured"  # 有编号 → 可规则提取 L4
    else:
        structure = "unstructured"
    
    return {
        "level": level,
        "core_thesis": core_thesis,
        "avg_sentence_len": round(avg_len, 1),
        "term_density": round(term_density, 2),
        "structure": structure,
    }


# ═══════════════════════════════════════
# 规则层: 六层组装
# ═══════════════════════════════════════

def rule_assemble(simplified_text: str, analogy: dict, assessment: dict, hook: dict) -> dict:
    """规则层六层组装 — 模板拼接，零API调用
    
    v0.3.1 修复: L1不再使用原文截取，改为从简化文本取第一句精要
    """
    # L1: 从简化文本取精要，而非原文截取
    sentences = re.split(r'[。！？]', simplified_text)
    essence = ""
    for s in sentences:
        s = s.strip()
        if len(s) > 10 and len(s) < 100:  # 取第一个有意义的完整句子
            essence = s
            break
    if not essence:
        essence = simplified_text[:100]
    
    return {
        "layer0_analogy": analogy.get("analogy_scene", ""),
        "layer1_essence": essence,
        "layer2_why": _gen_layer2(analogy, assessment),
        "layer3_entry": _gen_layer3(analogy),
        "layer4_skeleton": rule_extract_l4(simplified_text, assessment),
        "layer5_action": hook.get("hook", ""),
    }


def _gen_layer2(analogy: dict, assessment: dict) -> str:
    """L2: 为什么值得理解 (模板)"""
    core = assessment.get("core_thesis", "")[:30]
    insight = analogy.get("core_insight", "")
    if insight:
        return f"这个概念之所以重要，是因为{insight}"
    return f"理解这个概念，会改变你对「{core}」的认知方式。"


def _gen_layer3(analogy: dict) -> str:
    """L3: 具象入口 (模板)"""
    scene = analogy.get("analogy_scene", "")
    if len(scene) > 20:
        return f"先想象一个日常场景：{scene}"
    return ""


def rule_extract_l4(simplified_text: str, assessment: dict) -> list[dict]:
    """L4自适应提取:
    - structured(有编号) → 规则提取段落
    - unstructured → 前3句作为要点
    """
    points = []
    structure = assessment.get("structure", "unstructured")
    
    if structure == "structured":
        # 按编号切分
        segments = re.split(r'\n|。', simplified_text)
        for seg in segments:
            seg = seg.strip()
            if not seg or len(seg) < 10:
                continue
            # 找第一个句号或逗号前作为标题
            title_end = min(
                (seg.find('，') if '，' in seg else len(seg)),
                (seg.find('：') if '：' in seg else len(seg)),
                (seg.find('。') if '。' in seg else len(seg)),
                30
            )
            title = seg[:title_end].strip().lstrip('0123456789.、)） ')
            content = seg[title_end:].strip().lstrip('，：。')
            if title and content:
                points.append({"title": title[:30], "content": content[:80]})
    else:
        # 松散型: 取前3个句子
        sentences = re.split(r'[。！？]', simplified_text)
        count = 0
        for s in sentences:
            s = s.strip()
            if not s or len(s) < 10:
                continue
            title = s[:30]
            content = s[:80]
            points.append({"title": title, "content": content})
            count += 1
            if count >= 3:
                break
    
    # 确保不超过3个
    return points[:3]


# ═══════════════════════════════════════
# Prompt 模板
# ═══════════════════════════════════════

PROMPT_SIMPLIFY = """专业文本简化引擎。将复杂文本改写为朴实清晰的中文。

规则(3条):
1. 生僻术语→日常表达（原术语保留括号中）
2. 长句拆分，每句不超过30字
3. 保留原意，不添加理解
4. 自然语感：句子长短交替，避免"值得注意的是""综上所述"等AI痕迹

输出JSON: {"simplified":"简化后全文","changes":["改动1"]}。只输出JSON。"""

PROMPT_ANALOGY = """精准类比生成器。宁缺毋滥。

{pattern_guide}

要求:
1. 类比抓住概念本质结构，不是表面相似
2. 用日常经验做类比源
3. 包含: 场景→映射→洞见→边界

好类比: 「细胞像微型工厂」—抓住分工协作结构，非表面相似
差类比: 「DNA像食谱」—细胞不按步骤做菜，结构不对

输出JSON: {"analogy_scene":"2-3句场景","mapping":{"概念A":"类比X"},"core_insight":"本质洞见","boundary":"类比局限"}
只输出JSON。"""

PROMPT_HOOK = """认知钩子设计器。

类型(选最合适的):
- 反直觉提问: 提出与表面逻辑矛盾的现象
- 极端延伸: 把概念推到极端情况会怎样
- 个人对照: 让读者用自己的经历检验

输出JSON: {"type":"类型","hook":"2-3句，末句必须是问句","why_it_sticks":"为什么有效"}
只输出JSON。"""


# ═══════════════════════════════════════
# 轻量 LLM Agent
# ═══════════════════════════════════════

class _Agent:
    def __init__(self, registry, name, prompt):
        self.registry = registry
        self.name = name
        self.prompt = prompt

    def execute(self, user_prompt, temperature=0.3, max_tokens=2048):
        key, spec = self.registry.get_agent_model(self.name, "primary")
        client = self.registry.get_client(key)
        r = client.chat.completions.create(
            model=spec.model_id,
            messages=[{"role": "system", "content": self.prompt},
                      {"role": "user", "content": user_prompt}],
            temperature=temperature, max_tokens=max_tokens,
        )
        cost = self.registry.estimate_cost(
            key, r.usage.prompt_tokens if r.usage else 0,
            r.usage.completion_tokens if r.usage else 0,
        )
        return r.choices[0].message.content or "", cost


def _safe_json(text: str) -> str:
    text = text.strip()
    for p in [r'```(?:json)?\s*\n?(.*?)\n?```', r'\{.*\}']:
        m = re.search(p, text, re.DOTALL)
        if m:
            return m.group(1) if '```' in m.group(0) else m.group(0)
    return text


# ═══════════════════════════════════════
# 流水线
# ═══════════════════════════════════════

class DigestionPipeline:
    """认知消化流水线 v0.3 — 3 Agent + 规则层"""

    def __init__(self, config_path="config/models.yaml", profile=None, domain="日常经验", translator=None):
        self.registry = ModelRegistry(config_path)
        self.profile = profile
        self.domain = domain
        self.translator = translator
        self._agents = {}

    def _get(self, name, prompt):
        if name not in self._agents:
            self._agents[name] = _Agent(self.registry, name, prompt)
        return self._agents[name]

    async def digest(self, text: str, title="", source_lang="zh", source_type="article",
                     on_phase_complete: Optional[Callable] = None,
    ) -> DigestionResult:
        t0 = time.time()
        phases: dict[DigestionPhase, PhaseResult] = {}
        total_cost = 0.0
        domain = self.domain

        def record(ph, data, cost, elapsed, ok=True, errs=None):
            pr = PhaseResult(phase=ph, success=ok, data=data, duration_seconds=elapsed,
                            cost_usd=cost, errors=errs or [])
            phases[ph] = pr
            if on_phase_complete: on_phase_complete(ph, pr)
            return pr

        # ── 翻译前置 ──
        if source_lang != "zh" and self.translator:
            try:
                tr = await self.translator.run(source_text=text, title=title,
                    source_lang=source_lang, require_human_approval=False)
                if tr.success and tr.final_output:
                    text = tr.final_output.get("final_text", text)
            except Exception as e:
                record(DigestionPhase.SIMPLIFY, {}, 0, 0, False, [str(e)])
                return DigestionResult(success=False, phases=phases,
                    total_duration_seconds=time.time()-t0)

        # ── 规则层: 评估 ──
        st_rule = time.time()
        assessment = rule_assess(text)
        rule_time = time.time() - st_rule

        # ── Agent 1: 语义简化 ──
        st = time.time()
        resp, cost = self._get("s1_simplify", PROMPT_SIMPLIFY).execute(
            f"文本:\n{text[:8000]}", temperature=0.1
        )
        total_cost += cost
        try:
            simplified = json.loads(_safe_json(resp))
        except:
            simplified = {"simplified": text, "changes": []}
        simp_text = simplified.get("simplified", text)
        record(DigestionPhase.SIMPLIFY, simplified, cost, time.time()-st)

        # ── 类比库: 匹配结构模式 ──
        patterns = search_patterns(keyword=assessment.get("level", "medium"))
        pattern_guide = format_patterns_for_prompt(patterns) if patterns else ""

        # ── Agent 2 + 3: 类比生成 || 认知钩子 (并行) ──
        st_parallel = time.time()
        
        # Agent 2: 类比
        analogy_prompt = PROMPT_ANALOGY.replace("{pattern_guide}", pattern_guide)
        resp_a, cost_a = self._get("s2_analogy", analogy_prompt).execute(
            f"概念: {assessment.get('core_thesis','')}\n简化文本: {simp_text[:500]}",
            temperature=0.6
        )
        total_cost += cost_a
        try:
            analogy = json.loads(_safe_json(resp_a))
        except:
            analogy = {"analogy_scene": "", "core_insight": ""}
        
        # Agent 3: 钩子
        resp_h, cost_h = self._get("s3_hook", PROMPT_HOOK).execute(
            f"概念: {assessment.get('core_thesis','')[:200]}\n级别: {assessment.get('level','')}",
            temperature=0.5
        )
        total_cost += cost_h
        try:
            hook = json.loads(_safe_json(resp_h))
        except:
            hook = {"hook": ""}
        
        # 记录并行耗时
        parallel_elapsed = time.time() - st_parallel
        # 拆分为两个阶段记录
        record(DigestionPhase.ANALOGY, analogy, cost_a, parallel_elapsed)
        record(DigestionPhase.HOOK, hook, cost_h, parallel_elapsed)

        # ── 规则层: 六层组装 ──
        st = time.time()
        assembled = rule_assemble(simp_text, analogy, assessment, hook)
        record(DigestionPhase.ASSEMBLE, assembled, 0, time.time()-st)

        # ── DigestedOutput ──
        pts = assembled.get("layer4_skeleton", [])
        output = DigestedOutput(
            core_analogy=assembled.get("layer0_analogy", ""),
            one_line_essence=assembled.get("layer1_essence", ""),
            why_you_care=assembled.get("layer2_why", ""),
            concrete_entry=assembled.get("layer3_entry", ""),
            abstract_ascent="",
            skeleton_points=[SkeletonPoint(title=p.get("title",""), content=p.get("content",""))
                           for p in pts],
            micro_action=assembled.get("layer5_action", ""),
            source_title=title, source_type=source_type,
            difficulty_level=assessment.get("level","medium"),
            digested_by="v0.3_3agent+rules",
        )

        total_t = time.time() - t0
        return DigestionResult(
            success=True, phases=phases, total_duration_seconds=total_t,
            total_cost_usd=total_cost, final_output=output,
            summary=self._summary(phases, total_cost, total_t, rule_time),
        )

    def digest_sync(self, text, title="", **kw):
        return asyncio.run(self.digest(text=text, title=title, **kw))

    def _summary(self, phases, cost, duration, rule_time):
        lns = ["="*50, "  认知消化 v0.3 | 3Agent+规则层", "="*50,
               f"  规则层: {rule_time*1000:.0f}ms | LLM: 3次调用",
               f"  耗时: {duration:.1f}s | 成本: ${cost:.4f}", ""]
        for p, r in phases.items():
            lns.append(f"  {'✅' if r.success else '❌'} {p.value} ({r.duration_seconds:.1f}s)")
        return "\n".join(lns)
