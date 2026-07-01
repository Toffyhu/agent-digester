"""① 难度评估Agent — 判断输入内容的艰涩等级

输出：
- difficulty_level: easy / medium / hard
- 艰涩来源：术语密度、句式复杂度、前置知识缺口
- 建议处理策略：轻加工 / 标准消化 / 深度解构
"""

from agent_core import ModelRegistry, AgentResult
from agent_digester.agents.base import DigesterAgent


class DifficultyAssessor(DigesterAgent):
    agent_name = "difficulty_assessor"
    agent_description = "评估输入内容的认知难度，决定消化深度"

    def execute(self, text: str, title: str = "") -> AgentResult:
        system, user = self._default_prompt()
        user = user.format(text=text[:8000], title=title)

        response, ctx = self._call_llm(
            system_prompt=system,
            user_prompt=user,
            temperature=0.1,
            max_tokens=1024,
        )

        return AgentResult(
            success=True,
            data={
                "assessment": response,
                "title": title,
            },
            context=ctx,
        )

    def _default_prompt(self):
        system = """你是内容难度评估专家。分析文本的认知难度并给出处理建议。

评估维度：
1. 术语密度：每千字专业术语数量
2. 句式复杂度：平均句长、嵌套层级
3. 前置知识缺口：需要多少背景知识才能理解

输出JSON格式：
{
  "difficulty_level": "easy|medium|hard",
  "term_density": "low|medium|high",
  "avg_sentence_complexity": "low|medium|high",
  "prerequisite_gap": "none|some|significant",
  "recommended_processing": "light_digest|standard_digest|deep_deconstruct",
  "known_terms": [],
  "unknown_terms": []
}"""
        user = """分析以下文本的认知难度：

标题：{title}

{text}"""
        return system, user
