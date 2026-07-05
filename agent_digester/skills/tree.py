"""技能树引擎 v1.0 — 三层结构: 树干→分支→叶片

设计原则:
- 用户绝对自主: 可以增删改任意节点
- 模块化: 每个叶片是独立单元, 可以自由点亮/熄灭
- 可验证: 每个叶片有明确掌握标准
"""

from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from typing import Optional

# ═══════════════════════════════
# 三级结构
# ═══════════════════════════════

@dataclass
class SkillLeaf:
    """叶片 — 最小可验证能力单元
    
    示例: 
    SkillLeaf(
        name="理解黑格尔辩证法",
        mastery_status="learning",  # untouched|learning|mastered|paused
        prerequisite_hints=["了解正反合基本概念"],
        knowledge_scope="正题、反题、合题的三段运动及扬弃机制",
        verification="能用日常故事类比解释黑格尔辩证法",
    )
    """
    name: str
    mastery_status: str = "untouched"
    prerequisite_hints: list[str] = field(default_factory=list)
    knowledge_scope: str = ""
    verification: str = ""
    digested_notes: list[str] = field(default_factory=list)  # 关联的消化记录


@dataclass
class SkillBranch:
    """分支 — 按领域划分的能力大类"""
    name: str
    description: str = ""
    leaves: list[SkillLeaf] = field(default_factory=list)
    icon: str = "📚"


@dataclass  
class SkillTrunk:
    """树干 — 跨领域通用基础能力"""
    name: str
    description: str = ""
    leaves: list[SkillLeaf] = field(default_factory=list)
    icon: str = "🧠"


@dataclass
class SkillTree:
    """完整技能树 — 一用户一树"""
    user_id: str
    trunks: list[SkillTrunk] = field(default_factory=list)
    branches: list[SkillBranch] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    
    def add_trunk(self, name: str, **kw) -> SkillTrunk:
        t = SkillTrunk(name=name, **kw)
        self.trunks.append(t)
        return t
    
    def add_branch(self, name: str, **kw) -> SkillBranch:
        b = SkillBranch(name=name, **kw)
        self.branches.append(b)
        return b
    
    def add_leaf(self, parent, name: str, **kw) -> SkillLeaf:
        leaf = SkillLeaf(name=name, **kw)
        parent.leaves.append(leaf)
        return leaf
    
    def find_leaf(self, name: str) -> Optional[SkillLeaf]:
        for t in self.trunks:
            for l in t.leaves:
                if l.name == name: return l
        for b in self.branches:
            for l in b.leaves:
                if l.name == name: return l
        return None
    
    def mark_mastered(self, name: str):
        leaf = self.find_leaf(name)
        if leaf: leaf.mastery_status = "mastered"
    
    def mark_learning(self, name: str):
        leaf = self.find_leaf(name)
        if leaf: leaf.mastery_status = "learning"
    
    def paused(self, name: str):
        leaf = self.find_leaf(name)
        if leaf: leaf.mastery_status = "paused"
    
    def add_digestion_note(self, leaf_name: str, note: str):
        leaf = self.find_leaf(leaf_name)
        if leaf: leaf.digested_notes.append(note)
    
    def get_progress(self) -> dict:
        """技能树进度统计"""
        total = 0
        mastered = 0
        learning = 0
        for t in self.trunks:
            for l in t.leaves:
                total += 1
                if l.mastery_status == "mastered": mastered += 1
                if l.mastery_status == "learning": learning += 1
        for b in self.branches:
            for l in b.leaves:
                total += 1
                if l.mastery_status == "mastered": mastered += 1
                if l.mastery_status == "learning": learning += 1
        
        return {
            "total_leaves": total,
            "mastered": mastered,
            "learning": learning,
            "untouched": total - mastered - learning,
            "mastery_pct": round(mastered / max(total, 1) * 100),
            "engagement_pct": round((mastered + learning) / max(total, 1) * 100),
        }
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "trunks": [
                {"name": t.name, "description": t.description, "icon": t.icon,
                 "leaves": [{"name": l.name, "status": l.mastery_status,
                            "prerequisites": l.prerequisite_hints,
                            "scope": l.knowledge_scope,
                            "verification": l.verification,
                            "notes": l.digested_notes} for l in t.leaves]}
                for t in self.trunks
            ],
            "branches": [
                {"name": b.name, "description": b.description, "icon": b.icon,
                 "leaves": [{"name": l.name, "status": l.mastery_status,
                            "prerequisites": l.prerequisite_hints,
                            "scope": l.knowledge_scope,
                            "verification": l.verification,
                            "notes": l.digested_notes} for l in b.leaves]}
                for b in self.branches
            ],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SkillTree":
        tree = cls(user_id=data["user_id"])
        for t in data.get("trunks", []):
            trunk = SkillTrunk(name=t["name"], description=t.get("description",""), icon=t.get("icon","🧠"))
            for l in t.get("leaves", []):
                trunk.leaves.append(SkillLeaf(
                    name=l["name"], mastery_status=l.get("status","untouched"),
                    prerequisite_hints=l.get("prerequisites",[]),
                    knowledge_scope=l.get("scope",""),
                    verification=l.get("verification",""),
                    digested_notes=l.get("notes",[]),
                ))
            tree.trunks.append(trunk)
        for b in data.get("branches", []):
            branch = SkillBranch(name=b["name"], description=b.get("description",""), icon=b.get("icon","📚"))
            for l in b.get("leaves", []):
                branch.leaves.append(SkillLeaf(
                    name=l["name"], mastery_status=l.get("status","untouched"),
                    prerequisite_hints=l.get("prerequisites",[]),
                    knowledge_scope=l.get("scope",""),
                    verification=l.get("verification",""),
                    digested_notes=l.get("notes",[]),
                ))
            tree.branches.append(branch)
        return tree
    
    def render_summary(self) -> str:
        """渲染技能树总览"""
        p = self.get_progress()
        lines = [
            f"# {self.user_id} 的技能树",
            f"进度: {p['mastered']}/{p['total_leaves']} 已掌握 ({p['mastery_pct']}%)",
            f"学习中: {p['learning']}, 未开始: {p['untouched']}",
            "",
        ]
        for t in self.trunks:
            lines.append(f"## {t.icon} {t.name}")
            for l in t.leaves:
                icon = {"mastered":"✅","learning":"🔄","untouched":"⬜","paused":"⏸️"}.get(l.mastery_status,"?")
                lines.append(f"  {icon} {l.name}")
            lines.append("")
        for b in self.branches:
            lines.append(f"## {b.icon} {b.name}")
            for l in b.leaves:
                icon = {"mastered":"✅","learning":"🔄","untouched":"⬜","paused":"⏸️"}.get(l.mastery_status,"?")
                lines.append(f"  {icon} {l.name}")
            lines.append("")
        return "\n".join(lines)
