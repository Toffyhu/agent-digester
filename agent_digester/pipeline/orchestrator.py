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
from typing import Optional, Callable, Literal

from agent_core import ModelRegistry
from agent_digester.core.output import DigestedOutput, SkeletonPoint
from agent_digester.models.profile import UserProfile
from agent_digester.assets.analogy_bank.patterns import search_patterns, format_patterns_for_prompt


class DigestionPhase(str, Enum):
    SIMPLIFY = "simplify"
    ANALOGY = "analogy"
    HOOK = "hook"
    ASSEMBLE = "assemble"


DigestionLevel = Literal["literal", "summary", "explain", "naive"]
# literal:  原文直译 — 只做格式清洁，不加工
# summary:  精要提炼 — 保留术语但压缩逻辑链
# explain:  通俗解读 — 保留类比但用白话（原popular）
# naive:    入门类比 — 零术语，一个类比贯穿全文，不讲概念只讲故事


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

def rule_assemble(simplified_text: str, analogy: dict, assessment: dict, hook: dict, concept_map: list = None) -> dict:
    """规则层六层组装 — 模板拼接，零API调用
    
    v0.3.3: L4提取改用多源提炼(概念映射+类比洞见+简化文本)，不再机械搬用
    """
    sentences = re.split(r'[。！？]', simplified_text)
    essence = ""
    for s in sentences:
        s = s.strip()
        if len(s) > 10 and len(s) < 100:
            essence = s
            break
    if not essence:
        essence = simplified_text[:100]
    
    return {
        "layer0_analogy": analogy.get("analogy_scene", ""),
        "layer1_essence": essence,
        "layer2_why": _gen_layer2(analogy, assessment),
        "layer3_entry": _gen_layer3(analogy),
        "layer4_skeleton": rule_extract_l4(simplified_text, assessment, concept_map, analogy.get("core_insight")),
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


def fuse_narrative(data: dict) -> str:
    """融合六层为一段自然流动的文字 v0.3.4
    
    设计原则: 类比开篇→自然过渡到概念→展开要点(含误解纠偏)→钩子收尾
    不再用标题和列表，像一个朋友在解释一个概念
    """
    parts = []
    analogy = data.get("layer0_analogy", "")
    essence = data.get("layer1_essence", "")
    why = data.get("layer2_why", "")
    points = data.get("layer4_skeleton", [])
    hook = data.get("layer5_action", "")
    
    # 开篇: 类比引入
    if analogy and len(analogy) > 15:
        parts.append(analogy)
    
    # 过渡: 从类比到概念
    if essence:
        connector = "这其实就是在说：" if analogy else ""
        parts.append(connector + essence)
    
    # 展开: 要点串联
    if points:
        pt_texts = []
        for p in points:
            title = p.get("title", "").rstrip("：：")
            content = p.get("content", "")
            if content:
                pt_texts.append(f"{title}——{content}")
            else:
                pt_texts.append(title)
        parts.append("。".join(pt_texts) + "。")
    
    # 关联
    if why and len(why) > 10:
        parts.append(why)
    
    # 收尾: 钩子（自然过渡）
    if hook and len(hook) > 8:
        parts.append(hook)
    
    return "\n\n".join(parts)


def rule_extract_l4(simplified_text: str, assessment: dict, concept_map: list = None, analogy_insight: str = None) -> list[dict]:
    """L4提取 v0.3.5: 多源智能提炼 + 纠偏 + 反事实
    
    优先级:
    - 有概念映射(含misconception) → 纠偏式要点
    - 有概念映射 → 定义式要点
    - 无以上 → 信息密度评分
    """
    points = []
    structure = assessment.get("structure", "unstructured")
    
    if structure == "structured":
        segments = re.split(r'\n|。', simplified_text)
        for seg in segments:
            seg = seg.strip()
            if not seg or len(seg) < 10: continue
            title_end = min((seg.find('，') if '，' in seg else len(seg)),
                          (seg.find('：') if '：' in seg else len(seg)),
                          (seg.find('。') if '。' in seg else len(seg)), 30)
            title = seg[:title_end].strip().lstrip('0123456789.、)） ')
            content = seg[title_end:].strip().lstrip('，：。')
            if title and content and title not in [p['title'] for p in points]:
                points.append({"title": title[:30], "content": content[:80]})
    else:
        if concept_map and len(concept_map) >= 2:
            seen = set()
            for cm in concept_map[:3]:
                term = cm.get("原文", "")[:20]
                mc = cm.get("misconception", "")
                corr = cm.get("correction", "")
                
                if mc and corr:  # 有纠偏 → 纠偏式要点
                    content = f"{corr[:60]}"
                else:
                    content = cm.get("白话", "")[:70]
                
                if term and content and term not in seen:
                    points.append({"title": f"「{term}」", "content": content})
                    seen.add(term)
        
        if len(points) < 3:
            seen_titles = {p['title'] for p in points}
            sentences = re.split(r'[。！？]', simplified_text)
            candidates = []
            for s in sentences:
                s = s.strip()
                if len(s) < 15 or len(s) > 80: continue
                score = sum(1 for kw in ['是','不是','因为','所以','比如','即','指','说明','意味着','关键'] if kw in s)
                candidates.append((score, s[:30], s[:80]))
            candidates.sort(key=lambda x: -x[0])
            for _, t, c in candidates:
                if t not in seen_titles:
                    points.append({"title": t, "content": c})
                    seen_titles.add(t)
                    if len(points) >= 3: break
    
    return points[:3]


# ═══════════════════════════════════════
# Prompt 模板
# ═══════════════════════════════════════

PROMPT_SIMPLIFY = """专业文本简化引擎。将复杂文本改写为通俗清晰的中文。

核心能力: 不仅替换词汇，更要拆解逻辑结构。
遇到抽象概念时: 识别论证链条，把「因为A所以B」拆成两步解释。

规则(5条):
1. 生僻术语→日常表达（括号保留原术语）
2. 长句拆分，每句不超过25字
3. 抽象概念必须附带「概念映射」: 用大白话解释这个术语到底指什么
   - 例: 「共相→抽象的一般概念，比如"动物"概括了所有具体动物」
   - 例: 「范畴→理解世界的基本框架，就像眼镜的镜片决定了你能看到什么」
4. 识别并呈现原文的论证结构: 前提→推理→结论
5. ⚡ 误解纠偏: 对核心概念预判1个最常见的错误理解，先否定它，再给正确理解
   - 格式: "你可能以为X，其实不是。真正的意思是Y。"
   - 例: "你可能以为扬弃就是妥协——不是。妥协是双方各退一步。扬弃是双方都升级了。"
6. 🔀 多角度解释: 对核心概念，除了正面解释，提供一句反事实表述（如果不成立会怎样/如果反过来会怎样）
   - 例: "如果没有扬弃，正题和反题的冲突就只会互相消灭，认知永远停留在原地，不会有真正的进步。"
7. 🪜 前置概念推断: 对每个核心概念，列出理解它所需的一个前置概念或前提假设
   - 格式: "要理解X，首先你得知道Y：..."
   - 例: "要理解正题为什么必然引出反题，首先你得知道：任何判断都不是孤立的，它内部已经包含了对立面的种子。"
8. 自然语感: 长短句交替，像人在说话而非讲课

输出JSON: {"simplified":"简化后全文","concept_map":[{"原文":"术语","白话":"日常理解","misconception":"常见误解","correction":"正确理解","counterfactual":"反事实解释","prerequisite":"前置概念"}],"logic_chain":"逻辑链条","changes":["改动1"]}
只输出JSON。"""

PROMPT_ANALOGY = """精准类比生成器。一个完全命中的类比胜过四个勉强贴边的。

{pattern_guide}

好的类比必须满足:
1. 结构映射: 类比的关系结构 = 概念的关系结构（不是表面相似）
2. 受众匹配: 用日常经验，不用专业知识
3. 揭示洞见: 类比让人产生"哦原来是这样"的瞬间

精选示例:
✅ 好: 「自然选择像筛子——环境是筛孔，变异是颗粒大小。能通过筛孔的活下来繁殖。」
   抓住: 环境(筛孔)筛选变异(颗粒)的结构
❌ 差: 「自然选择像选美比赛——最漂亮的胜出。」
   错误: 不是漂亮是适应，选了表面相似丢掉了结构

✅ 好: 「认知失调像心里卡了一根刺——你知道自己撒了谎，不舒服，不得不想办法拔掉它或说服自己这根刺是合理的。」
   抓住: 矛盾(卡刺)→不适(痛)→消除(拔/合理化)的因果链
❌ 差: 「认知失调像左右手互搏——两个想法在打架。」
   错误: 只说了矛盾，丢了不适感和主动消除的动机

输出JSON: {"analogy_scene":"2-3句场景","mapping":{"概念A":"类比X","概念B":"类比Y"},"core_insight":"本质洞见","boundary":"类比局限(这比喻哪里不适用)"}
只输出JSON。"""

PROMPT_HOOK = """认知钩子设计器。目标是让读者忍不住开始想。

类型(选最合适的):
- 反直觉: 提出一个表面与概念矛盾的现象
- 极端延伸: 把概念推到极限会怎样
- 自我对照: 让读者用亲身经历检验

好钩子示例:
✅ "如果确认偏误是真的，那你上一次改变自己的观点是什么时候？你能回忆起当时的证据吗？"
✅ "根据边际效用递减，吃第十片薯片的快乐几乎为零——但如果它是你人生最后一片呢？"

差钩子示例:
❌ "你有没有类似的经历呢？"（太笼统）
❌ "所以我们要注意避免这种认知偏差。"（说教）

输出JSON: {"type":"类型","hook":"2-3句，末句必须是问句","why_it_sticks":"为什么这个钩子会让人想"}

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
        concept_map = simplified.get("concept_map", [])
        assembled = rule_assemble(simp_text, analogy, assessment, hook, concept_map)
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

    async def digest_leveled(
        self, text: str, title="", level: DigestionLevel = "explain",
        source_lang="zh", source_type="article",
        on_phase_complete=None,
    ):
        """四档难度消化

        - literal:  原文直译 — 清洁格式+长句拆分，不解释
        - summary:  精要提炼 — 去冗余+保留术语+保留逻辑链
        - explain:  通俗解读 — 保留类比+白话+纠正误解 (popular层)
        - naive:    入门类比 — 零术语，一个类比讲完核心，不讲概念只讲画面
        """
        from agent_digester.pipeline.orchestrator import _Agent, rule_assess

        if level == "literal":
            # 零Agent：只做规则层处理
            return await self._level_literal(text, title, source_type)
        elif level == "summary":
            return await self._level_summary(text, title, source_type)
        elif level == "naive":
            return await self._level_naive(text, title, source_type)
        else:
            # explain = 默认，走现有digest逻辑
            return await self.digest(text=text, title=title, source_lang=source_lang,
                                     source_type=source_type, on_phase_complete=on_phase_complete)

    async def _level_literal(self, text, title, source_type):
        """原文直译 — 不调用LLM，只做规则层"""
        import time
        t0 = time.time()
        assessment = rule_assess(text)
        sentences = re.split(r'[。！？]', text)
        lines = []
        for s in sentences:
            s = s.strip().lstrip('0123456789.、)） ')
            if s: lines.append(s)
        cleaned = "。".join(lines)
        parts = [f"# {title}", "", cleaned]
        article = "\n".join(parts)
        o = DigestedOutput(one_line_essence=assessment.get("core_thesis"), source_title=title)
        return DigestionResult(success=True, total_duration_seconds=time.time()-t0,
                              final_output=o, summary="[literal] 原文直译")

    async def _level_summary(self, text, title, source_type):
        """精要提炼 — 一次LLM调用，保留术语但三句话讲完核心逻辑"""
        import time
        from agent_digester.pipeline.orchestrator import _Agent, PROMPT_SIMPLIFY, rule_assess
        t0 = time.time()
        reg = self.registry
        assessment = rule_assess(text)
        agent = _Agent(reg, "s1_simplify", PROMPT_SIMPLIFY)
        resp, cost = agent.execute(f"提取核心逻辑链，精炼为3-5句话。保留关键术语。去掉一切例子和冗余。\n{text[:5000]}", 0.3)
        o = DigestedOutput(one_line_essence=resp[:200], source_title=title, source_type=source_type)
        return DigestionResult(success=True, total_duration_seconds=time.time()-t0,
                              total_cost_usd=cost, final_output=o,
                              summary=f"[summary] 精要提炼 | {time.time()-t0:.1f}s")

    async def _level_naive(self, text, title, source_type):
        """入门类比 — 零术语，一个类比讲完核心，不讲概念只讲故事"""
        import time
        from agent_digester.pipeline.orchestrator import _Agent, rule_assess

        NAIVE_PROMPT = """想象你要把下面这段文字的核心思想讲给一个12岁的孩子听。

        规则：
        1. 不用任何专业术语
        2. 用一个完整的日常故事或场景来讲述核心思想
        3. 不要出现「这个概念」「这个现象」这类词
        4. 用一个人物或一个具体事例开始
        5. 结尾一句话点破「所以这个故事说明了什么」

        直接写，不需要任何前缀说明。200-300字。"""

        reg = self.registry
        t0 = time.time()
        agent = _Agent(reg, "s1_simplify", NAIVE_PROMPT)
        resp, cost = agent.execute(f"需要解释的内容:\n{text[:3000]}", 0.6, 1024)
        o = DigestedOutput(one_line_essence=resp[:200], source_title=title, source_type=source_type)
        return DigestionResult(success=True, total_duration_seconds=time.time()-t0,
                              total_cost_usd=cost, final_output=o,
                              summary=f"[naive] 入门类比 | {time.time()-t0:.1f}s")

    def _summary(self, phases, cost, duration, rule_time):
        lns = ["="*50, "  认知消化 v0.3 | 3Agent+规则层", "="*50,
               f"  规则层: {rule_time*1000:.0f}ms | LLM: 3次调用",
               f"  耗时: {duration:.1f}s | 成本: ${cost:.4f}", ""]
        for p, r in phases.items():
            lns.append(f"  {'✅' if r.success else '❌'} {p.value} ({r.duration_seconds:.1f}s)")
        return "\n".join(lns)
