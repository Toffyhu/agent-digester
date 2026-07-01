"""认知消化Agent基类 — 继承agent-core，注入认知铁律

所有消化Agent扩展此类，自动获得铁律自检能力。
"""

from __future__ import annotations

from typing import Optional

from agent_core import BaseAgent as CoreBaseAgent, ModelRegistry

from agent_digester.core.laws import generate_law_checklist
from agent_digester.models.profile import UserProfile


class DigesterAgent(CoreBaseAgent):
    """认知消化Agent基类

    特点：
    - 自动注入七条认知铁律检查清单到 system prompt
    - 携带用户画像，Agent 可根据画像调整输出风格
    """

    agent_name: str = "digester_base"
    agent_description: str = "认知消化Agent基类"

    def __init__(
        self,
        model_registry: Optional[ModelRegistry] = None,
        asset_store: object = None,
        user_profile: Optional[UserProfile] = None,
    ):
        super().__init__(
            model_registry=model_registry,
            asset_store=asset_store,
            mode="digest",
        )
        self.profile = user_profile

    def _inject_knowledge(self, system_prompt: str) -> str:
        """注入认知铁律检查清单"""
        law_checklist = generate_law_checklist()

        profile_hint = ""
        if self.profile:
            profile_hint = f"""
## 👤 用户画像（输出风格指导）
- 认知风格: {self.profile.cognitive_style.value}（{'先案例再规律' if self.profile.cognitive_style.value == 'inductive' else '先规律再案例' if self.profile.cognitive_style.value == 'deductive' else '灵活切换'}）
- 密度偏好: {self.profile.density_preference.value}（{'精简浓缩' if self.profile.density_preference.value == 'high' else '适中' if self.profile.density_preference.value == 'medium' else '娓娓道来'}）
- 思维通道: {self.profile.thinking_channel.value}（{'多用文字' if self.profile.thinking_channel.value == 'verbal' else '多用画面' if self.profile.thinking_channel.value == 'visual' else '图文并茂'}）
- 已知领域: {', '.join(self.profile.knowledge_topography) if self.profile.knowledge_topography else '未知'}
"""

        system_prompt = f"""{system_prompt}
{profile_hint}
{law_checklist}"""

        return system_prompt
