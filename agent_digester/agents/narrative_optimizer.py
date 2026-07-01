"""④ 叙事优化Agent — 把清单转成故事，术语转成类比

核心职责：
- 检查六层输出是否有纯罗列倾向
- 将干涩段落改写为叙事结构
- 确保每个核心概念都有具象类比
"""

from agent_core import ModelRegistry, AgentResult
from agent_digester.agents.base import DigesterAgent
from agent_digester.core.output import DigestedOutput, SkeletonPoint


class NarrativeOptimizer(DigesterAgent):
    agent_name = "narrative_optimizer"
    agent_description = "叙事优化 — 清单→故事，术语→类比"

    def execute(self, output: DigestedOutput) -> AgentResult:
        current_md = output.to_markdown()

        system, user = self._default_prompt()
        user = user.format(current_output=current_md)

        response, ctx = self._call_llm(
            system_prompt=system,
            user_prompt=user,
            temperature=0.5,
            max_tokens=3072,
        )

        return AgentResult(
            success=True,
            data={
                "optimization_suggestions": response,
                "original": output,
            },
            context=ctx,
        )

    def _default_prompt(self):
        system = """你是叙事优化专家。检查认知消化输出，标记需要叙事化的段落。

优化规则：
1. 如果某段是纯列表（3个以上bullet point连续出现），标记为需要叙事化
2. 如果出现未解释的术语，建议添加类比
3. 如果 Layer 3 入口太抽象，建议更具体的场景

输出JSON格式：
{
  "narrative_score": "pass|needs_work|fail",
  "issues": [
    {
      "layer": 0-5,
      "issue_type": "list_bias|unexplained_term|abstract_entry",
      "description": "问题描述",
      "suggestion": "改写建议"
    }
  ],
  "rewritten_sections": {
    "layer_N": "改写后的文本（如果需要）"
  }
}

只标记真正有问题的地方。如果输出已经很好，narrative_score为pass，issues为空数组。"""
        user = """检查以下认知消化输出的叙事质量：

{current_output}"""
        return system, user
