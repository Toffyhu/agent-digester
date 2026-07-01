"""agent_digester v0.2 — 认知消化工具

基于学习科学文献优化的6 Agent分工架构。
10条认知铁律 + 六层输出结构 + 用户个性化适配。

Author: Toffyhu / 灵栖Invest
"""
from agent_digester.core.laws import IronLaw, generate_law_checklist, LAWS
from agent_digester.core.output import DigestedOutput, SkeletonPoint
from agent_digester.pipeline.orchestrator import DigestionPipeline, DigestionResult
from agent_digester.models.profile import UserProfile, CognitiveStyle

__version__ = "0.2.0"

__all__ = [
    "DigestionPipeline",
    "DigestionResult",
    "DigestedOutput",
    "SkeletonPoint",
    "UserProfile",
    "CognitiveStyle",
    "IronLaw",
    "generate_law_checklist",
    "LAWS",
]
