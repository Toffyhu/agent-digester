"""② 锚点识别Agent — 找到用户已知体系中的关联点

核心职责：
- 扫描输入文本的核心概念
- 从用户知识地貌中匹配已知概念
- 输出推荐的类比域和锚点路径
"""

from agent_core import ModelRegistry, AgentResult
from agent_digester.agents.base import DigesterAgent
from agent_digester.models.profile import UserProfile


class AnchorFinder(DigesterAgent):
    agent_name = "anchor_finder"
    agent_description = "识别认知锚点，为新知识找到已知参照系"

    def execute(
        self,
        text: str,
        core_concepts: list[str],
        profile: UserProfile,
    ) -> AgentResult:
        known_concepts = ", ".join(profile.knowledge_topography) if profile.knowledge_topography else "未记录"
        analogy_domain = profile.get_analogy_domain()

        system, user = self._default_prompt()
        user = user.format(
            text=text[:5000],
            core_concepts=", ".join(core_concepts),
            known_concepts=known_concepts,
            analogy_domain=analogy_domain,
        )

        response, ctx = self._call_llm(
            system_prompt=system,
            user_prompt=user,
            temperature=0.3,
            max_tokens=2048,
        )

        return AgentResult(
            success=True,
            data={
                "anchor_mapping": response,
                "analogy_domain": analogy_domain,
            },
            context=ctx,
        )

    def _default_prompt(self):
        system = """你是认知锚点专家。为每个新概念找到一个用户已知体系中的锚点。

规则：
1. 锚点必须来自用户已知概念集合
2. 如果用户已知概念中没有，使用最通用的日常类比
3. 每个锚点包含：类比源 → 映射关系 → 新概念

输出JSON格式：
{
  "anchors": [
    {
      "new_concept": "新概念名称",
      "anchor_source": "类比来源（用户已知概念或日常经验）",
      "mapping": "具体映射关系描述",
      "confidence": "high|medium|low"
    }
  ],
  "best_entry_concept": "最适合作为入口的概念（最接近用户认知的那个）",
  "progression": "从入口到核心的认知递进路径"
}"""
        user = """为新概念找到认知锚点：

核心概念：{core_concepts}
用户已知概念：{known_concepts}
推荐类比域：{analogy_domain}

原文摘要：
{text}"""
        return system, user
