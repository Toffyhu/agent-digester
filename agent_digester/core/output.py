"""认知消化输出结构 — 六层模型定义

Layer 0: 核心类比（一句话画面）← 锚定 + 双编码
Layer 1: 一句话本质 ← 记忆瓶颈
Layer 2: 跟你有什么关系 ← 认知负荷（先建立筛选依据）
Layer 3: 具象入口 → 抽象登顶 ← 锚定
Layer 4: 核心骨架（3-5 要点 + 视觉映射）← 记忆瓶颈 + 双编码
Layer 5: 一个微行动 / 一个追问 ← 生成效应
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LayerLevel(int, Enum):
    ANALOGY = 0        # 核心类比
    ESSENCE = 1        # 一句话本质
    RELEVANCE = 2      # 跟你有什么关系
    ENTRY = 3          # 具象入口 → 抽象登顶
    SKELETON = 4       # 核心骨架
    ACTION = 5         # 微行动/追问


@dataclass
class SkeletonPoint:
    """Layer 4 骨架要点"""
    title: str          # 要点标题（一句话）
    content: str        # 展开说明
    visual_hint: str = ""  # 视觉映射提示


@dataclass
class DigestedOutput:
    """认知消化后的完整六层输出"""
    # Layer 0
    core_analogy: str = ""          # 核心类比画面

    # Layer 1
    one_line_essence: str = ""      # 一句话本质（≤50字）

    # Layer 2
    why_you_care: str = ""          # 跟你有什么关系

    # Layer 3
    concrete_entry: str = ""        # 具象入口
    abstract_ascent: str = ""       # 抽象登顶

    # Layer 4
    skeleton_points: list[SkeletonPoint] = field(default_factory=list)

    # Layer 5
    micro_action: str = ""          # 微行动或追问

    # Metadata
    source_title: str = ""
    source_type: str = ""           # article / paper / topic
    difficulty_level: str = ""      # easy / medium / hard
    digested_by: str = ""           # agent version
    personalization_note: str = ""  # 本次个性化适配说明

    def to_markdown(self) -> str:
        """输出为Markdown格式"""
        parts = []

        # Layer 0: 核心类比
        if self.core_analogy:
            parts.append(f"> 💡 {self.core_analogy}")
            parts.append("")

        # Layer 1: 一句话本质
        if self.one_line_essence:
            parts.append(f"## 一句话")
            parts.append(self.one_line_essence)
            parts.append("")

        # Layer 2: 跟你有什么关系
        if self.why_you_care:
            parts.append(f"## 为什么你应该关心")
            parts.append(self.why_you_care)
            parts.append("")

        # Layer 3: 具象入口 → 抽象登顶
        if self.concrete_entry or self.abstract_ascent:
            parts.append(f"## 从具象到抽象")
            if self.concrete_entry:
                parts.append(f"**入口**：{self.concrete_entry}")
            if self.abstract_ascent:
                parts.append(f"**登顶**：{self.abstract_ascent}")
            parts.append("")

        # Layer 4: 核心骨架
        if self.skeleton_points:
            parts.append(f"## 核心骨架（{len(self.skeleton_points)} 个要点）")
            for i, sp in enumerate(self.skeleton_points, 1):
                parts.append(f"### {i}. {sp.title}")
                parts.append(sp.content)
                if sp.visual_hint:
                    parts.append(f"> 🎨 {sp.visual_hint}")
                parts.append("")

        # Layer 5: 微行动
        if self.micro_action:
            parts.append("## 试试这个")
            parts.append(f"> 🎯 {self.micro_action}")
            parts.append("")

        # Footer
        parts.append("---")
        parts.append(f"*难度: {self.difficulty_level} | 来源: {self.source_title}*")
        if self.personalization_note:
            parts.append(f"*适配: {self.personalization_note}*")

        return "\n".join(parts)

    def to_wechat(self) -> str:
        """输出为公众号友好格式（对 to_markdown 的微调）"""
        # 公众号输出与 Markdown 基本相同，但块引用格式更适合移动端阅读
        parts = []

        if self.core_analogy:
            parts.append(f"💡 **{self.core_analogy}**")
            parts.append("")

        if self.one_line_essence:
            parts.append(f"**一句话**：{self.one_line_essence}")
            parts.append("")

        if self.why_you_care:
            parts.append(f"### 为什么你应该关心")
            parts.append(self.why_you_care)
            parts.append("")

        if self.concrete_entry:
            parts.append(f"### 从一个熟悉的场景出发")
            parts.append(self.concrete_entry)
            parts.append("")

        if self.skeleton_points:
            parts.append(f"### 核心要点")
            for i, sp in enumerate(self.skeleton_points, 1):
                parts.append(f"**{i}. {sp.title}**")
                parts.append(sp.content)
                parts.append("")

        if self.micro_action:
            parts.append(f"### 🎯 试一试")
            parts.append(self.micro_action)

        return "\n".join(parts)
