"""⑤ 认知缺口Agent — 生成追问/微行动，触发主动思考

核心职责（生成效应）：
- 基于消化后的内容生成 1-3 个追问
- 生成 1 个可执行的微行动
- 可选：生成简单的自测题目
"""

from agent_core import ModelRegistry, AgentResult
from agent_digester.agents.base import DigesterAgent
from agent_digester.core.output import DigestedOutput
from agent_digester.models.profile import UserProfile


class CognitiveGapAgent(DigesterAgent):
    agent_name = "cognitive_gap"
    agent_description = "认知缺口触发 — 生成追问和微行动"

    def execute(
        self,
        output: DigestedOutput,
        profile: UserProfile = None,
    ) -> AgentResult:
        self.profile = profile
        current_md = output.to_markdown()
        known = ", ".join(profile.knowledge_topography) if profile and profile.knowledge_topography else "未知"

        system, user = self._default_prompt()
        user = user.format(current_output=current_md, known_concepts=known)

        response, ctx = self._call_llm(
            system_prompt=system,
            user_prompt=user,
            temperature=0.6,
            max_tokens=2048,
        )

        return AgentResult(
            success=True,
            data={
                "gap_triggers": response,
            },
            context=ctx,
        )

    def _default_prompt(self):
        system = """你是认知缺口设计专家。基于消化后的内容，设计触发主动思考的追问和行动。

设计原则：
1. 追问应该在「恰好不会」和「恰好能推导」之间的甜区
2. 微行动必须具体、可执行、5分钟内能完成
3. 可以设置一个认知陷阱（常见误解），让读者先想再纠正

输出JSON格式：
{
  "questions": [
    {
      "question": "具体问题",
      "difficulty": "easy|medium|hard",
      "hint": "如果卡住了，看这个提示",
      "target_concept": "这个问题帮你巩固哪个概念"
    }
  ],
  "micro_action": {
    "description": "5分钟内可完成的具体行动",
    "expected_outcome": "完成后你会得到什么",
    "difficulty": "easy|medium"
  },
  "cognitive_trap": {
    "misconception": "一个常见的错误理解",
    "correction": "正确的理解方式",
    "why_it_matters": "为什么纠正这个误解很重要"
  }
}"""
        user = """为以下消化内容设计认知缺口：

已知概念：{known_concepts}

消化后的内容：
{current_output}"""
        return system, user
