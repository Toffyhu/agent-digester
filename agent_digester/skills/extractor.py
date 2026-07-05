"""知识萃取引擎 v1.0 — 从消化输出提取关键概念, 映射到技能树

核心流程:
  消化文章 → [概念提取] → [语义匹配] → 映射到技能树叶节点 → 更新掌握进度
"""

import json, re, os, sys
from typing import Optional

sys.path.insert(0, "/workspace")

from agent_core import ModelRegistry
from agent_digester.pipeline.orchestrator import _Agent
from agent_digester.skills.tree import SkillTree, SkillLeaf

PROMPT_EXTRACT = """从文章中提取3-5个核心概念。每个概念标注:
- concept: 概念名
- domain: 所属领域(哲学/科学/技术/经济/心理学/其他)
- one_liner: 一句话定义
- why_matters: 为什么这个概念重要

输出JSON数组: [{"concept":"","domain":"","one_liner":"","why_matters":""},...]
只输出JSON."""


class KnowledgeExtractor:
    """知识萃取 — 文章→概念词→技能树节点"""
    
    def __init__(self, config_path="config/models.yaml"):
        self.registry = ModelRegistry(config_path)
    
    def extract_concepts(self, article: str) -> list[dict]:
        """从消化文章中提取核心概念"""
        agent = _Agent(self.registry, "ke_extract", PROMPT_EXTRACT)
        resp, cost = agent.execute(f"文章:\n{article[:3000]}", temperature=0.2, max_tokens=1024)
        try:
            return json.loads(re.search(r'\[.*\]', resp, re.DOTALL).group(0))
        except:
            return []
    
    def map_to_tree(self, concepts: list[dict], tree: SkillTree) -> list[dict]:
        """将概念映射到技能树叶节点（基于语义相似度）"""
        mappings = []
        for concept in concepts:
            concept_name = concept.get("concept", "")
            domain = concept.get("domain", "")
            
            # 在技能树中查找最匹配的叶片
            best_leaf = None
            best_score = 0
            
            all_leaves = []
            for t in tree.trunks:
                all_leaves.extend(t.leaves)
            for b in tree.branches:
                all_leaves.extend(b.leaves)
            
            for leaf in all_leaves:
                score = self._match_score(concept_name, domain, leaf)
                if score > best_score:
                    best_score = score
                    best_leaf = leaf
            
            mappings.append({
                "concept": concept_name,
                "domain": domain,
                "one_liner": concept.get("one_liner", ""),
                "matched_leaf": best_leaf.name if best_leaf else "未匹配",
                "match_score": best_score,
                "is_new": best_score < 0.3 or best_leaf is None,
            })
        
        return mappings
    
    def _match_score(self, concept: str, domain: str, leaf: SkillLeaf) -> float:
        """概念→叶片匹配度评分（简单关键词重叠）"""
        score = 0.0
        leaf_text = f"{leaf.name} {leaf.knowledge_scope} {leaf.verification}"
        
        # 精确包含
        if concept.lower() in leaf.name.lower():
            score += 0.8
        elif any(c in leaf.name for c in concept):
            score += 0.4
        
        # 关键词重叠
        concept_words = set(concept)
        leaf_words = set(leaf_text)
        overlap = concept_words & leaf_words
        score += len(overlap) * 0.1
        
        # 领域匹配
        if domain.lower() in leaf_text.lower():
            score += 0.2
        
        return min(score, 1.0)
    
    def sync_to_tree(self, mappings: list[dict], tree: SkillTree, article_ref: str = ""):
        """将萃取结果同步到技能树——更新已学概念，标记新概念待添加"""
        for m in mappings:
            if m["is_new"]:
                # 建议添加新叶片
                pass  # 暂不自动创建，由用户手动决策
            else:
                leaf_name = m["matched_leaf"]
                tree.mark_learning(leaf_name)
                tree.add_digestion_note(leaf_name, f"[{article_ref}] {m['concept']}: {m['one_liner']}")
    
    def render_mapping_report(self, mappings: list[dict]) -> str:
        """渲染概念映射报告"""
        lines = ["## 知识萃取 — 概念映射", ""]
        matched = [m for m in mappings if not m["is_new"]]
        new = [m for m in mappings if m["is_new"]]
        
        if matched:
            lines.append("### 已匹配到技能树")
            for m in matched:
                lines.append(f"- **{m['concept']}** → {m['matched_leaf']} (匹配度: {m['match_score']:.0%})")
                lines.append(f"  {m['one_liner']}")
            lines.append("")
        
        if new:
            lines.append("### 新概念（建议加入技能树）")
            for m in new:
                lines.append(f"- [{m['domain']}] **{m['concept']}**: {m['one_liner']}")
            lines.append("")
        
        return "\n".join(lines)
