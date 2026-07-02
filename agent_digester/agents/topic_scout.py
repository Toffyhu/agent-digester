"""TopicScout — 话题探索Agent

无原文输入时，自主构建话题的知识渐进解释。
不同于文章消化（有原文→简化→解释），TopicScout从LLM已有知识出发，
组织成知识树后逐层生成渐进式消化卡片。

管线:
  话题词 → [知识树构建] → [层级定义] → [逐层消化] → 渐进卡片
"""

from __future__ import annotations

import json, re
from dataclasses import dataclass, field
from typing import Optional

from agent_core import ModelRegistry
from agent_digester.pipeline.orchestrator import _Agent
from agent_digester.core.output import DigestedOutput, SkeletonPoint


PROMPT_EXPLORE = """你是知识组织专家。用户想了解一个话题。

请从你的知识出发，构建这个话题的三层知识树。

规则:
1. 第一层: 本质定义（一句话 + 一个精准类比）
2. 第二层: 关键机制（3个要点，每个包含解释+具体例子）
3. 第三层: 延伸思考（2个关联概念 + 1个反直觉问题）

输出JSON:
{
  "topic": "话题名称",
  "layer1_essence": {
    "one_liner": "一句话核心",
    "analogy": "一个精准类比（2-3句场景）",
    "misconception": "常见误解",
    "correction": "纠正"
  },
  "layer2_mechanism": [
    {
      "title": "要点标题",
      "explanation": "解释（不超过80字）",
      "example": "具体例子（不超过60字）",
      "counterfactual": "如果不是这样会怎样"
    }
  ],
  "layer3_extension": [
    {
      "related_concept": "关联概念名",
      "connection": "与主概念的关联（不超过60字）"
    }
  ],
  "hook_question": "一个让人忍不住开始想的问题"
}

只输出JSON。"""


@dataclass
class TopicCard:
    """渐进式知识卡片"""
    topic: str
    depth: int  # 1=本质, 2=机制, 3=延伸
    content: str
    is_complete: bool = False


@dataclass
class TopicResult:
    """话题探索完整结果"""
    success: bool
    topic: str
    knowledge_tree: dict
    cards: list[TopicCard] = field(default_factory=list)
    total_cost_usd: float = 0.0
    summary: str = ""


class TopicScout:
    """话题探索Agent v0.1
    
    用法:
    ```python
    scout = TopicScout(config_path="config/models.yaml")
    result = scout.explore("量子纠缠")
    for card in result.cards:
        print(card.content)
    ```
    """
    
    def __init__(self, config_path: str = "config/models.yaml"):
        self.registry = ModelRegistry(config_path)
        self._explorer = None
    
    @property
    def explorer(self):
        if self._explorer is None:
            self._explorer = _Agent(self.registry, "ts_explore", PROMPT_EXPLORE)
        return self._explorer
    
    def explore(self, topic: str) -> TopicResult:
        """探索一个话题，返回渐进式知识卡片"""
        import time
        
        t0 = time.time()
        
        # ── 知识树构建 ──
        resp, cost = self.explorer.execute(
            f"请构建以下话题的知识树：{topic}",
            temperature=0.3, max_tokens=3072,
        )
        
        try:
            tree = json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group(0))
        except:
            return TopicResult(success=False, topic=topic, knowledge_tree={},
                             summary=f"知识树解析失败: {resp[:100]}")
        
        # ── 渐进卡片生成 ──
        cards = []
        
        # 卡片1: 本质层
        l1 = tree.get("layer1_essence", {})
        mc = l1.get("misconception", "")
        corr = l1.get("correction", "")
        essence_card = f"""🔰 {topic} — 一句话

{l1.get('one_liner', '')}

💡 打个比方：
{l1.get('analogy', '')}"""

        if mc and corr:
            essence_card += f"\n\n⚡ 别搞混了：{mc}。实际上{corr}"
        
        cards.append(TopicCard(topic=topic, depth=1, content=essence_card))
        
        # 卡片2: 机制层
        mechanisms = tree.get("layer2_mechanism", [])
        mech_parts = [f"🔧 {topic} — 怎么工作的"]
        for i, m in enumerate(mechanisms[:3], 1):
            mech_parts.append(f"\n{i}. {m.get('title', '')}")
            mech_parts.append(f"   {m.get('explanation', '')}")
            example = m.get("example", "")
            if example:
                mech_parts.append(f"   例: {example}")
            cf = m.get("counterfactual", "")
            if cf:
                mech_parts.append(f"   🔀 {cf}")
        cards.append(TopicCard(topic=topic, depth=2, content="\n".join(mech_parts)))
        
        # 卡片3: 延伸层
        extensions = tree.get("layer3_extension", [])
        ext_parts = [f"🌐 {topic} — 还该知道什么"]
        for i, e in enumerate(extensions[:2], 1):
            ext_parts.append(f"\n{i}. → {e.get('related_concept', '')}")
            ext_parts.append(f"   关联: {e.get('connection', '')}")
        
        hook = tree.get("hook_question", "")
        if hook:
            ext_parts.append(f"\n💭 {hook}")
        
        cards.append(TopicCard(topic=topic, depth=3, content="\n".join(ext_parts)))
        
        elapsed = time.time() - t0
        return TopicResult(
            success=True,
            topic=topic,
            knowledge_tree=tree,
            cards=cards,
            total_cost_usd=cost,
            summary=f"3层渐进卡片 | {elapsed:.1f}s | ${cost:.4f}",
        )
