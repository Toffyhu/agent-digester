"""认知铁律引擎 — 人类认知的七条底层规律

这些不是观点，是认知科学几十年的验证结论。
Agent 输出必须同时满足这七条，违反任意一条都会显著降低吸收效率。

引用:
- Miller, G.A. (1956). The magical number seven, plus or minus two.
- Sweller, J. (1988). Cognitive load during problem solving.
- Ausubel, D.P. (1960). The use of advance organizers.
- Bruner, J. (1991). The narrative construction of reality.
- Slamecka & Graf (1978). The generation effect.
- Paivio, A. (1971). Imagery and verbal processes.
- Ebbinghaus, H. (1885). Memory: A contribution to experimental psychology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IronLaw(str, Enum):
    """七条认知铁律"""
    MEMORY_BOTTLENECK  = "memory_bottleneck"     # 工作记忆瓶颈: 4±1 组块
    COGNITIVE_LOAD     = "cognitive_load"        # 认知负荷上限: 去噪
    ANCHORING          = "anchoring"             # 锚定前置: 先类比后抽象
    NARRATIVE_BIAS     = "narrative_bias"        # 叙事编码: 故事 > 列表
    GENERATION_EFFECT  = "generation_effect"     # 生成效应: 推导 > 被动
    DUAL_CODING        = "dual_coding"           # 双编码: 语言 + 视觉
    SPACED_REPETITION  = "spaced_repetition"     # 间隔强化: 分散 > 一次灌满


@dataclass
class LawConstraint:
    """每条铁律对输出的硬约束"""
    law: IronLaw
    constraint: str   # 约束描述
    check_hint: str   # 验证提示（Agent自查用）
    severity: str = "must"  # must | should


# ── 七条铁律的完整约束定义 ──

LAWS: dict[IronLaw, LawConstraint] = {
    IronLaw.MEMORY_BOTTLENECK: LawConstraint(
        law=IronLaw.MEMORY_BOTTLENECK,
        constraint="每个输出单元的核心要点不超过 5 个。超出必须拆分或分级。",
        check_hint="数一下输出中独立概念的个数，超过5个→拆分",
        severity="must",
    ),
    IronLaw.COGNITIVE_LOAD: LawConstraint(
        law=IronLaw.COGNITIVE_LOAD,
        constraint="去掉一切与核心逻辑无关的术语、旁支、铺垫。只留必需信息。",
        check_hint="逐句检查：删掉这句话，理解会变吗？不会→删",
        severity="must",
    ),
    IronLaw.ANCHORING: LawConstraint(
        law=IronLaw.ANCHORING,
        constraint="新概念必须先给出类比/前置概念/熟悉场景，再进入抽象定义。",
        check_hint="每个新概念出现前，是否先给出了具象入口？没有→补",
        severity="must",
    ),
    IronLaw.NARRATIVE_BIAS: LawConstraint(
        law=IronLaw.NARRATIVE_BIAS,
        constraint="输出必须有 '问题→探索→解决' 的叙事线，禁止纯罗列。",
        check_hint="这段内容是讲了一个故事还是列了一份清单？清单→重写",
        severity="must",
    ),
    IronLaw.GENERATION_EFFECT: LawConstraint(
        law=IronLaw.GENERATION_EFFECT,
        constraint="输出结尾必须触发一次主动思考：一个追问 / 一个微行动 / 一次自测。",
        check_hint="读者看完最后一行后，脑子里会自动产生一个行动或问题吗？不会→加",
        severity="must",
    ),
    IronLaw.DUAL_CODING: LawConstraint(
        law=IronLaw.DUAL_CODING,
        constraint="关键概念必须有视觉映射：类比画面 / 简单图表 / 空间关系描述。",
        check_hint="核心概念能否在脑海里形成画面？不能→加一个具象类比",
        severity="should",
    ),
    IronLaw.SPACED_REPETITION: LawConstraint(
        law=IronLaw.SPACED_REPETITION,
        constraint="输出末尾关联到上次阅读的相关内容，形成间隔回顾链。",
        check_hint="是否提醒用户回顾之前的关联内容？没有→补",
        severity="should",
    ),
}


def get_laws_by_severity(severity: str = "must") -> list[LawConstraint]:
    """获取指定严重级别的铁律约束"""
    return [lc for lc in LAWS.values() if lc.severity == severity]


def get_all_laws() -> list[LawConstraint]:
    """获取全部七条铁律"""
    return list(LAWS.values())


def generate_law_checklist() -> str:
    """生成Agent自查用的铁律检查清单（注入prompt用）"""
    lines = ["## 认知铁律检查清单（输出前逐条自查）", ""]
    for i, (law, lc) in enumerate(LAWS.items(), 1):
        icon = "🔴" if lc.severity == "must" else "🟡"
        lines.append(f"{i}. {icon} **{law.value}**: {lc.constraint}")
        lines.append(f"   → 自查: {lc.check_hint}")
        lines.append("")
    return "\n".join(lines)
