"""agent_digester v0.3 — 认知消化工具

10条认知铁律 + 六层输出结构 + 用户个性化适配
两种模式: 文章消化(DigestionPipeline) + 话题探索(TopicScout)

Author: Toffyhu / 灵栖Invest
"""
from agent_digester.core.laws import IronLaw, generate_law_checklist, LAWS
from agent_digester.core.output import DigestedOutput, SkeletonPoint
from agent_digester.pipeline.orchestrator import DigestionPipeline, DigestionResult
from agent_digester.agents.topic_scout import TopicScout, TopicResult, TopicCard
from agent_digester.models.profile import UserProfile, CognitiveStyle

__version__ = "0.3.5"

__all__ = [
    "DigestionPipeline",
    "DigestionResult",
    "DigestedOutput",
    "SkeletonPoint",
    "TopicScout",
    "TopicResult",
    "TopicCard",
    "UserProfile",
    "CognitiveStyle",
    "IronLaw",
    "generate_law_checklist",
    "LAWS",
]
