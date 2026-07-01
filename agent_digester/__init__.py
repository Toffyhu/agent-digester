"""agent_digester — 认知消化工具

基于 agent-core 的认知友好内容转换引擎。
六层输出结构 + 七条认知铁律 + 用户个性化适配。

Author: Toffyhu / 灵栖Invest
"""
from agent_digester.core.laws import IronLaw, generate_law_checklist
from agent_digester.core.output import DigestedOutput, SkeletonPoint
from agent_digester.pipeline.orchestrator import DigestionPipeline, DigestionResult
from agent_digester.models.profile import UserProfile, CognitiveStyle

__version__ = "0.1.0"

__all__ = [
    "DigestionPipeline",
    "DigestionResult",
    "DigestedOutput",
    "SkeletonPoint",
    "UserProfile",
    "CognitiveStyle",
    "IronLaw",
    "generate_law_checklist",
]
