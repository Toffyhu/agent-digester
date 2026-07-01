"""认知铁律引擎 v0.2 — 扩展至10条铁律

v0.2 新增（基于学习科学文献综述）:
- 精细加工效应 (Elaboration): 用户主动问why/how → 深层加工
- 理想困难 (Desirable Difficulty): 适度认知摩擦 > 完全消除障碍
- 构建优先 (Construct First): 输出必须触发用户自我生产

引用:
- Weinstein, Madan & Sumeracki (2018). Teaching the science of learning.
- Bjork & Bjork (2011). Making things hard on yourself, but in a good way.
- Chi & Wylie (2014). The ICAP Framework.
- Sweller, van Merriënboer & Paas (2019). Cognitive Architecture and Instructional Design.
- Miller (1956), Bruner (1991), Paivio (1971), Ebbinghaus (1885).
- Hou et al. (2026). MARS: Metacognitive Agent Reflective Self-improvement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IronLaw(str, Enum):
    """认知铁律（10条）"""
    # ── v0.1 七条 ──
    MEMORY_BOTTLENECK  = "memory_bottleneck"
    COGNITIVE_LOAD     = "cognitive_load"
    ANCHORING          = "anchoring"
    NARRATIVE_BIAS     = "narrative_bias"
    GENERATION_EFFECT  = "generation_effect"
    DUAL_CODING        = "dual_coding"
    SPACED_REPETITION  = "spaced_repetition"
    
    # ── v0.2 新增三条 ──
    ELABORATION        = "elaboration"          # 精细加工效应: 用户主动问why/how
    DESIRABLE_DIFFICULTY = "desirable_difficulty"  # 理想困难: 适度认知摩擦
    CONSTRUCT_FIRST    = "construct_first"       # 构建优先: 触发自我生产


@dataclass  
class LawConstraint:
    law: IronLaw
    constraint: str
    check_hint: str
    severity: str = "must"


LAWS: dict[IronLaw, LawConstraint] = {
    # ── v0.1 ──
    IronLaw.MEMORY_BOTTLENECK: LawConstraint(
        law=IronLaw.MEMORY_BOTTLENECK,
        constraint="每个输出单元的核心要点不超过 5 个。超出必须拆分。",
        check_hint="数一下独立概念个数，超过5个→拆分",
    ),
    IronLaw.COGNITIVE_LOAD: LawConstraint(
        law=IronLaw.COGNITIVE_LOAD,
        constraint="去掉一切与核心逻辑无关的术语、旁支、铺垫。",
        check_hint="逐句检查：删掉这句话，理解会变吗？不会→删",
    ),
    IronLaw.ANCHORING: LawConstraint(
        law=IronLaw.ANCHORING,
        constraint="新概念必须先给出类比/前置概念/熟悉场景。",
        check_hint="每个新概念出现前是否给了具象入口？没有→补",
    ),
    IronLaw.NARRATIVE_BIAS: LawConstraint(
        law=IronLaw.NARRATIVE_BIAS,
        constraint="输出必须有'问题→探索→解决'的叙事线。",
        check_hint="这段是讲故事还是列清单？清单→重写",
    ),
    IronLaw.GENERATION_EFFECT: LawConstraint(
        law=IronLaw.GENERATION_EFFECT,
        constraint="结尾须触发主动思考：追问/微行动/自测。",
        check_hint="读者看完整段后会自动产生行动或问题吗？不会→加",
    ),
    IronLaw.DUAL_CODING: LawConstraint(
        law=IronLaw.DUAL_CODING,
        constraint="关键概念必须有视觉映射。",
        check_hint="核心概念能否在脑海形成画面？不能→加类比",
        severity="should",
    ),
    IronLaw.SPACED_REPETITION: LawConstraint(
        law=IronLaw.SPACED_REPETITION,
        constraint="末尾关联到上次阅读的相关内容。",
        check_hint="是否提醒回顾之前内容？没有→补",
        severity="should",
    ),
    
    # ── v0.2 新增 ──
    IronLaw.ELABORATION: LawConstraint(
        law=IronLaw.ELABORATION,
        constraint="输出中必须包含至少一个开放的'how/why'问题，引导用户自己推导。不要代替用户完成推导。",
        check_hint="有没有一个地方让用户必须自己想？没有→在关键推理点插入问题",
    ),
    IronLaw.DESIRABLE_DIFFICULTY: LawConstraint(
        law=IronLaw.DESIRABLE_DIFFICULTY,
        constraint="不能把一切都解释完。保留适度的认知摩擦——类比留边界不适用处、结论留一个未解决的张力。",
        check_hint="这个输出是不是把'正确答案'喂到了嘴边？是→收一点回去",
        severity="should",
    ),
    IronLaw.CONSTRUCT_FIRST: LawConstraint(
        law=IronLaw.CONSTRUCT_FIRST,
        constraint="在给出解释之前，先让用户尝试自己生成——哪怕只是一个猜测。'你觉得为什么...？先想10秒钟，再看下面'。",
        check_hint="输出中是否至少有一处要求用户'先自己试试'？没有→加",
    ),
}


def get_laws_by_severity(severity: str = "must") -> list[LawConstraint]:
    return [lc for lc in LAWS.values() if lc.severity == severity]


def get_all_laws() -> list[LawConstraint]:
    return list(LAWS.values())


def generate_law_checklist() -> str:
    """生成Agent自查用的铁律检查清单"""
    lines = ["## 认知铁律检查清单（输出前逐条自查）", ""]
    for i, (law, lc) in enumerate(LAWS.items(), 1):
        icon = "🔴" if lc.severity == "must" else "🟡"
        lines.append(f"{i}. {icon} **{law.value}**: {lc.constraint}")
        lines.append(f"   → 自查: {lc.check_hint}")
        lines.append("")
    return "\n".join(lines)


def get_core_laws() -> list[LawConstraint]:
    """核心铁律（v0.1 七条）"""
    return [lc for lc in LAWS.values() 
            if lc.law not in (IronLaw.ELABORATION, IronLaw.DESIRABLE_DIFFICULTY, IronLaw.CONSTRUCT_FIRST)]


def get_new_laws() -> list[LawConstraint]:
    """v0.2 新增三条"""
    return [LAWS[l] for l in (IronLaw.ELABORATION, IronLaw.DESIRABLE_DIFFICULTY, IronLaw.CONSTRUCT_FIRST)]
