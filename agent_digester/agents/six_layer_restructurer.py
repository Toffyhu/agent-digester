"""③ 六层重构Agent — 按认知六层结构重写内容

这是消化流水线的核心Agent。
输入：原文 + 难度评估 + 锚点映射
输出：完整的 DigestedOutput 六层结构
"""

import json
import re

from agent_core import ModelRegistry, AgentResult
from agent_digester.agents.base import DigesterAgent
from agent_digester.core.output import DigestedOutput, SkeletonPoint
from agent_digester.models.profile import UserProfile


def _extract_json(text: str) -> str:
    """从LLM响应中提取JSON，处理```json...```代码块包裹"""
    text = text.strip()
    # 去除 ```json ... ``` 包裹
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


class SixLayerRestructurer(DigesterAgent):
    agent_name = "six_layer_restructurer"
    agent_description = "核心消化引擎 — 将任意内容重写为认知六层结构"

    def execute(
        self,
        text: str,
        title: str = "",
        difficulty_assessment: dict = None,
        anchor_mapping: dict = None,
        profile: UserProfile = None,
        source_type: str = "article",
    ) -> AgentResult:
        self.profile = profile

        system, user = self._default_prompt()
        user = user.format(
            text=text[:12000],
            title=title,
            difficulty=json.dumps(difficulty_assessment or {}, ensure_ascii=False),
            anchors=json.dumps(anchor_mapping or {}, ensure_ascii=False),
           source_type=source_type,
        )

        response, ctx = self._call_llm(
            system_prompt=system,
            user_prompt=user,
            temperature=0.4,
            max_tokens=4096,
        )

        # 解析输出（处理```json代码块包裹）
        try:
            clean_json = _extract_json(response)
            data = json.loads(clean_json)
            output = DigestedOutput(
                core_analogy=data.get("core_analogy", ""),
               one_line_essence=data.get("one_line_essence", ""),
                why_you_care=data.get("why_you_care", ""),
                concrete_entry=data.get("concrete_entry", ""),
                abstract_ascent=data.get("abstract_ascent", ""),
                skeleton_points=[
                    SkeletonPoint(
                        title=sp.get("title", ""),
                        content=sp.get("content", ""),
                        visual_hint=sp.get("visual_hint", ""),
                    )
                    for sp in data.get("skeleton_points", [])
                ],
                micro_action=data.get("micro_action", ""),
                source_title=title,
                source_type=source_type,
                difficulty_level=difficulty_assessment.get("difficulty_level", "medium") if difficulty_assessment else "medium",
                digested_by="six_layer_restructurer_v0.1",
            )
            return AgentResult(
                success=True,
                data={"output": output, "raw_json": data},
                context=ctx,
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: 用 raw text
            output = DigestedOutput(
                core_analogy="",
                one_line_essence=response[:200],
                source_title=title,
                difficulty_level="medium",
                digested_by="six_layer_restructurer_v0.1 (fallback)",
            )
            return AgentResult(
                success=True,
                data={"output": output, "raw_text": response},
                context=ctx,
                warnings=[f"JSON解析失败: {e}, 使用raw text回退"],
            )

    def _default_prompt(self):
        system = """你是认知消化专家。将输入内容重写为六层结构。

⚠️ 重要：直接返回纯JSON，不要用```json ... ```包裹，不要加任何前缀说明。

你需要输出严格的JSON格式，包含以下字段：

{
  "core_analogy": "用一句话具象类比画面概括核心概念（Layer 0）",
  "one_line_essence": "一句话本质总结，不超过50字（Layer 1）",
  "why_you_care": "解释这个概念为什么与读者相关，建立动机（Layer 2）",
  "concrete_entry": "从读者熟悉的场景/例子出发，引导进入主题（Layer 3 入口）",
  "abstract_ascent": "从具象入口逐步抽象到核心概念（Layer 3 登顶）",
  "skeleton_points": [
    {
      "title": "要点标题（一句话）",
      "content": "展开说明（不超过200字，去冗余）",
      "visual_hint": "可视化的类比或画面描述"
    }
  ],
  "micro_action": "一个读者可以立刻尝试的具体行动或一个值得思考的追问"
}

硬约束（违反任意一条则输出无效）：
1. skeleton_points 必须是 3-5 个，不能多也不能少
2. one_line_essence 必须 ≤50字，且不能是标题的复述
3. core_analogy 必须是具体的画面描述，不能用抽象术语
4. micro_action 必须是可执行的具体行为或具体问题，不能是笼统建议
5. 全部输出必须用用户的语言（中文），避免术语堆砌

遵照认知铁律检查清单逐条自查后再输出。"""

        user = """请将以下内容消化为六层结构：

标题：{title}
来源类型：{source_type}

难度评估：
{difficulty}

锚点映射：
{anchors}

原文：
{text}"""
        return system, user
