"""技能点驱动管线 — 选择技能点 → 自适应消化 → 进度回写

核心逻辑:
  用户选择要攻克的技能点
    → 系统自动判断当前掌握程度
    → 匹配最合适的难度档位
    → 消化内容后自动萃取+验证
    → 结果归档回技能树节点

使用方式:
  engine = SkillPipeline(pipeline, tree, config)
  
  # 情景A: 用户主动选择技能点
  engine.read_with_skill(text, title, "蒙特卡洛模拟")
  
  # 情景B: 用户自由输入, 自动匹配
  engine.read_and_match(text, title, "信息增益解释")
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json, time, re, copy
from typing import Optional

from agent_digester import DigestionPipeline, DigestionLevel, UserProfile
from agent_digester.skills.tree import SkillTree, SkillLeaf, SkillBranch, SkillTrunk
from agent_digester.skills.extractor import KnowledgeExtractor
from agent_digester.agents.verification import VerificationEngine


# 技能掌握程度 → 推荐消化档位
_SKILL_TO_LEVEL = {
    "untouched": "naive",     # 没学过的 → 入门类比
    "learning":  "explain",   # 学过的 → 通俗解读
    "mastered":  None,        # 掌握的 → 不需消化
    "paused":    "explain",   # 暂停的 → 继续通俗解读
}

# 默认档位
_DEFAULT_LEVEL: DigestionLevel = "explain"


@dataclass
class ReadSession:
    """一次阅读学习的完整记录"""
    skill_name: str
    original_level: str          # 原技能掌握状态
    used_level: DigestionLevel   # 实际使用的难度档位
    article: str                 # 消化后的文章
    verification: dict           # 三阶验证结果
    concepts: list[dict]         # 萃取的概念
    new_status: str              # 学习后的状态更新
    elapsed: float               # 耗时


class SkillPipeline:
    """技能驱动管线 — 技能树 ↔ 消化管线 双向联动"""
    
    def __init__(
        self,
        pipeline: DigestionPipeline,
        tree: SkillTree,
        config_path: str = "config/models.yaml",
    ):
        self.pipeline = pipeline
        self.tree = tree
        self.config_path = config_path
        self.extractor = KnowledgeExtractor(config_path)
        self.verifier = VerificationEngine(config_path)
    
    # ═══════════════════════════════
    # A: 用户主动选择技能点
    # ═══════════════════════════════
    
    async def read_with_skill(
        self,
        text: str,
        title: str,
        skill_name: str,
        source_type: str = "自动",
    ) -> ReadSession:
        """选定技能点 → 自适应消化 → 进度回写"""
        # 1. 查找技能点
        leaf = self.tree.find_leaf(skill_name)
        if leaf is None:
            raise ValueError(f"技能点 '{skill_name}' 不存在")
        
        old_status = leaf.mastery_status
        
        # 2. 根据掌握程度选档位
        level = _SKILL_TO_LEVEL.get(old_status, _DEFAULT_LEVEL)
        if level is None:
            # 已掌握 → 跳过消化, 直接返回
            return ReadSession(
                skill_name=skill_name, original_level=old_status,
                used_level=None, article="", verification={},
                concepts=[], new_status="mastered", elapsed=0,
            )
        
        # 3. 执行消化
        t0 = time.time()
        result = await self.pipeline.digest_leveled(
            text=text, title=title, level=level,
            source_type=source_type,
        )
        article = result.final_output.one_line_essence if result.final_output else ""
        
        # 4. 三阶验证
        vfy = self.verifier.generate(article, text)
        
        # 5. 知识萃取 + 映射
        concepts = self.extractor.extract_concepts(article)
        mappings = self.extractor.map_to_tree(concepts, self.tree)
        self.extractor.sync_to_tree(mappings, self.tree, title)
        
        # 6. 更新技能点状态
        if old_status in ("untouched",):
            self.tree.mark_learning(skill_name)
        self.tree.add_digestion_note(skill_name, f"[{title}] 已阅读")
        
        elapsed = time.time() - t0
        new_leaf = self.tree.find_leaf(skill_name)
        new_status = new_leaf.mastery_status if new_leaf else old_status
        
        return ReadSession(
            skill_name=skill_name, original_level=old_status,
            used_level=level, article=article[:300],
            verification=vfy, concepts=mappings,
            new_status=new_status, elapsed=elapsed,
        )
    
    # ═══════════════════════════════
    # B: 用户自由输入, 自动匹配
    # ═══════════════════════════════
    
    async def read_and_match(self, text: str, title: str, source_type: str = "自动") -> dict:
        """自由输入 → 先消化 → 再匹配技能树 → 提出添加建议"""
        t0 = time.time()
        
        # 1. 默认消化 (explain档)
        result = await self.pipeline.digest_leveled(
            text=text, title=title, level="explain",
            source_type=source_type,
        )
        article = result.final_output.one_line_essence if result.final_output else ""
        
        # 2. 知识萃取
        concepts = self.extractor.extract_concepts(article)
        mappings = self.extractor.map_to_tree(concepts, self.tree)
        
        # 3. 匹配技能点建议
        new_concepts = [m for m in mappings if m["is_new"]]
        matched = [m for m in mappings if not m["is_new"]]
        
        return {
            "article": article[:500],
            "concepts": concepts,
            "mappings": mappings,
            "matched_count": len(matched),
            "new_concepts": new_concepts,  # 建议添加的技能
            "matched": matched,            # 已更新的技能
            "elapsed": f"{time.time()-t0:.1f}s",
        }
    
    def render_session(self, session: ReadSession) -> str:
        """渲染阅读记录"""
        lines = [
            f"技能点: {session.skill_name}",
            f"状态: {session.original_level}→{session.new_status}",
            f"档位: {session.used_level}",
            f"耗时: {session.elapsed:.1f}s",
            "",
        ]
        if session.article:
            lines.append(f"📖 {session.article[:200]}")
            lines.append("")
        if session.verification.get("verification", {}).get("stage2_practice", {}).get("task"):
            lines.append(f"🎯 实践任务: {session.verification['verification']['stage2_practice']['task']}")
        return "\n".join(lines)
