"""agent_digester v0.5 — 认知消化 + 技能成长系统

10条认知铁律 + 六层输出结构 + 四档难度切换 + 用户个性化适配 + 技能树驱动
四个层次: 消化(四档) → 验证(三阶) → 萃取(概念→技能) → 驱动(技能驱动消化)

Author: Toffyhu / 灵栖Invest
"""
from agent_digester.core.laws import IronLaw, generate_law_checklist, LAWS
from agent_digester.core.output import DigestedOutput, SkeletonPoint
from agent_digester.pipeline.orchestrator import DigestionPipeline, DigestionResult, DigestionLevel
from agent_digester.agents.topic_scout import TopicScout, TopicResult, TopicCard
from agent_digester.agents.verification import VerificationEngine
from agent_digester.agents.truth_guardian import TruthGuardian
from agent_digester.models.profile import UserProfile, CognitiveStyle
from agent_digester.skills.tree import SkillTree, SkillLeaf, SkillBranch, SkillTrunk
from agent_digester.skills.driver import SkillPipeline, ReadSession
from agent_digester.skills.extractor import KnowledgeExtractor

__version__ = "0.5.0"

__all__ = [
    "DigestionPipeline",
    "DigestionResult",
    "DigestionLevel",
    "DigestedOutput",
    "SkeletonPoint",
    "TopicScout", "TopicResult", "TopicCard",
    "VerificationEngine",
    "TruthGuardian",
    "UserProfile", "CognitiveStyle",
    "SkillTree", "SkillLeaf", "SkillBranch", "SkillTrunk",
    "SkillPipeline", "ReadSession",
    "KnowledgeExtractor",
    "IronLaw", "generate_law_checklist", "LAWS",
]
