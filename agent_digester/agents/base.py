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
            # 安全获取 enum value（兼容字符串和枚举）
            def ev(v):
                return v.value if hasattr(v, 'value') else str(v)
            
            cs = ev(self.profile.cognitive_style)
            dp = ev(self.profile.density_preference)
            tc = ev(self.profile.thinking_channel)
            
            style_map = {
                'inductive': '先案例再规律', 'deductive': '先规律再案例',
                'mixed': '灵活切换',
            }
            density_map = {
                'high': '精简浓缩', 'medium': '适中', 'low': '娓娓道来',
            }
            channel_map = {
                'verbal': '多用文字', 'visual': '多用画面', 'mixed': '图文并茂',
            }
            
            profile_hint = f"""
## 👤 用户画像（输出风格指导）
- 认知风格: {cs}（{style_map.get(cs, cs)}）
- 密度偏好: {dp}（{density_map.get(dp, dp)}）
- 思维通道: {tc}（{channel_map.get(tc, tc)}）
- 已知领域: {', '.join(self.profile.knowledge_topography) if self.profile.knowledge_topography else '未知'}
"""

        system_prompt = f"""{system_prompt}
{profile_hint}
{law_checklist}"""

        return system_prompt
