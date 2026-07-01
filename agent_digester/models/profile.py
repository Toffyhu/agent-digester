"""用户认知画像 — 个性化层的六维模型

泛化层保证「不会错」，个性化层决定「好不好」。
六维画像随交互行为无感积累，不需要用户填写。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CognitiveStyle(str, Enum):
    """认知风格"""
    INDUCTIVE = "inductive"       # 归纳型: 先案例后规律
    DEDUCTIVE = "deductive"       # 演绎型: 先规律后案例
    MIXED = "mixed"              # 混合


class DensityPreference(str, Enum):
    """密度偏好"""
    HIGH = "high"         # 喜欢高密度浓缩
    MEDIUM = "medium"     # 适中
    LOW = "low"           # 喜欢娓娓道来


class LanguagePreference(str, Enum):
    """语言偏好"""
    CONCISE = "concise"     # 简洁
    DETAILED = "detailed"   # 详细
    ORAL = "oral"           # 口语化
    ACADEMIC = "academic"   # 学术化


class ThinkingChannel(str, Enum):
    """思维通道"""
    VERBAL = "verbal"        # 文字型
    VISUAL = "visual"        # 视觉型
    MIXED = "mixed"          # 混合型


@dataclass
class TopicWeight:
    """主题权重"""
    topic: str
    weight: float  # 0.0 ~ 1.0, 随时间衰减
    last_read: str = ""  # ISO时间戳


@dataclass
class UserProfile:
    """用户认知画像

    使用方式:
    ```python
    profile = UserProfile(user_id="user_001")
    profile.update_from_behavior("skipped_layer2", weight=0.1)
    ```
    """
    user_id: str

    # 六维画像
    cognitive_style: CognitiveStyle = CognitiveStyle.MIXED
    density_preference: DensityPreference = DensityPreference.MEDIUM
    language_preference: LanguagePreference = LanguagePreference.CONCISE
    thinking_channel: ThinkingChannel = ThinkingChannel.MIXED
    knowledge_topography: set[str] = field(default_factory=set)  # 已知概念集合
    interest_weights: dict[str, float] = field(default_factory=dict)  # 主题权重

    def update_from_behavior(self, signal: str, weight: float = 0.1):
        """
        从用户行为无感更新画像。

        Args:
            signal: 行为信号，如 'skipped_layer2', 'long_gaze_chart', 'marked_too_deep'
            weight: 更新权重（0-1），累积学习速率
        """
        old = getattr(self, '_signal_history', [])
        old.append(signal)
        object.__setattr__(self, '_signal_history', old)

        if signal == "skipped_layer2":
            # 跳过关联动机层 → 偏演绎，偏高密度
            if self.cognitive_style == CognitiveStyle.MIXED:
                self.cognitive_style = CognitiveStyle.DEDUCTIVE
            if self.density_preference == DensityPreference.MEDIUM:
                self.density_preference = DensityPreference.HIGH

        elif signal == "replayed_analogy":
            # 反复看类比 → 偏归纳，该领域可能较浅
            if self.cognitive_style == CognitiveStyle.MIXED:
                self.cognitive_style = CognitiveStyle.INDUCTIVE
            if self.density_preference == DensityPreference.HIGH:
                self.density_preference = DensityPreference.MEDIUM

        elif signal == "long_gaze_chart":
            # 看图时间长 → 视觉通道优先
            self.thinking_channel = ThinkingChannel.VISUAL

        elif signal == "marked_too_deep":
            # 标注太难 → 降密度
            if self.density_preference == DensityPreference.HIGH:
                self.density_preference = DensityPreference.MEDIUM
            elif self.density_preference == DensityPreference.MEDIUM:
                self.density_preference = DensityPreference.LOW

        elif signal == "marked_too_shallow":
            # 标注太浅 → 升密度
            if self.density_preference == DensityPreference.LOW:
                self.density_preference = DensityPreference.MEDIUM
            elif self.density_preference == DensityPreference.MEDIUM:
                self.density_preference = DensityPreference.HIGH

    def add_knowledge(self, concept: str):
        """添加已知概念"""
        self.knowledge_topography.add(concept)

    def update_interest(self, topic: str, weight_delta: float = 0.05):
        """更新主题兴趣权重"""
        current = self.interest_weights.get(topic, 0.5)
        self.interest_weights[topic] = min(1.0, max(0.0, current + weight_delta))

    def get_analogy_domain(self) -> str:
        """根据知识地貌返回推荐类比领域"""
        domains = {
            "量化投资": "finance",
            "机器学习": "ml",
            "技术架构": "engineering",
            "内容创作": "writing",
            "产品管理": "product",
        }
        for keyword, domain in domains.items():
            if keyword in self.knowledge_topography or any(
                keyword in k for k in self.knowledge_topography
            ):
                return domain
        return "daily_life"  # 默认日常类比

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "cognitive_style": self.cognitive_style.value,
            "density_preference": self.density_preference.value,
            "language_preference": self.language_preference.value,
            "thinking_channel": self.thinking_channel.value,
            "knowledge_topography": list(self.knowledge_topography),
            "interest_weights": self.interest_weights,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        profile = cls(user_id=data["user_id"])
        profile.cognitive_style = CognitiveStyle(data.get("cognitive_style", "mixed"))
        profile.density_preference = DensityPreference(data.get("density_preference", "medium"))
        profile.language_preference = LanguagePreference(data.get("language_preference", "concise"))
        profile.thinking_channel = ThinkingChannel(data.get("thinking_channel", "mixed"))
        profile.knowledge_topography = set(data.get("knowledge_topography", []))
        profile.interest_weights = data.get("interest_weights", {})
        return profile
