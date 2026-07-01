"""认知消化流水线调度器

五阶段流水线：
Phase 0: 难度评估 → Phase 1: 锚点识别 → Phase 2: 六层重构
→ Phase 3: 叙事优化 → Phase 4: 认知缺口 → 交付

可选：如果输入是外文，翻译前置（依赖 agent-translator）
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

from agent_core import ModelRegistry

from agent_digester.agents.base import DigesterAgent
from agent_digester.agents.difficulty_assessor import DifficultyAssessor
from agent_digester.agents.anchor_finder import AnchorFinder
from agent_digester.agents.six_layer_restructurer import SixLayerRestructurer
from agent_digester.agents.narrative_optimizer import NarrativeOptimizer
from agent_digester.agents.cognitive_gap import CognitiveGapAgent
from agent_digester.core.output import DigestedOutput
from agent_digester.models.profile import UserProfile


class DigestionPhase(str, Enum):
    ASSESS = "assess"
    ANCHOR = "anchor"
    RESTRUCTURE = "restructure"
    OPTIMIZE = "optimize"
    GAP = "gap"
    DELIVER = "deliver"


@dataclass
class PhaseResult:
    phase: DigestionPhase
    success: bool
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class DigestionResult:
    """消化流水线完整结果"""
    success: bool
    phases: dict[DigestionPhase, PhaseResult] = field(default_factory=dict)
    total_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0
    final_output: Optional[DigestedOutput] = None
    summary: str = ""


class DigestionPipeline:
    """
    认知消化流水线

    使用方式：
    ```python
    pipeline = DigestionPipeline(config_path="config/models.yaml")
    result = await pipeline.digest(
        text="任意文本...",
        title="文章标题",
        profile=user_profile,
    )
    print(result.final_output.to_wechat())
    ```
    """

    def __init__(
        self,
        config_path: str = "config/models.yaml",
        user_profile: Optional[UserProfile] = None,
        translator=None,  # Optional: TranslationPipeline 实例
    ):
        self.registry = ModelRegistry(config_path)
        self.profile = user_profile

        # 可选翻译插件
        self.translator = translator

        # Agent 延迟初始化
        self._difficulty_assessor: Optional[DifficultyAssessor] = None
        self._anchor_finder: Optional[AnchorFinder] = None
        self._restructurer: Optional[SixLayerRestructurer] = None
        self._optimizer: Optional[NarrativeOptimizer] = None
        self._gap_agent: Optional[CognitiveGapAgent] = None

    # ── 属性 ──

    @property
    def difficulty_assessor(self) -> DifficultyAssessor:
        if self._difficulty_assessor is None:
            self._difficulty_assessor = DifficultyAssessor(
                self.registry, user_profile=self.profile,
            )
        return self._difficulty_assessor

    @property
    def anchor_finder(self) -> AnchorFinder:
        if self._anchor_finder is None:
            self._anchor_finder = AnchorFinder(
                self.registry, user_profile=self.profile,
            )
        return self._anchor_finder

    @property
    def restructurer(self) -> SixLayerRestructurer:
        if self._restructurer is None:
            self._restructurer = SixLayerRestructurer(
                self.registry, user_profile=self.profile,
            )
        return self._restructurer

    @property
    def optimizer(self) -> NarrativeOptimizer:
        if self._optimizer is None:
            self._optimizer = NarrativeOptimizer(
                self.registry, user_profile=self.profile,
            )
        return self._optimizer

    @property
    def gap_agent(self) -> CognitiveGapAgent:
        if self._gap_agent is None:
            self._gap_agent = CognitiveGapAgent(
                self.registry, user_profile=self.profile,
            )
        return self._gap_agent

    # ── 主入口 ──

    async def digest(
        self,
        text: str,
        title: str = "",
        source_lang: str = "zh",
        source_type: str = "article",
        profile: Optional[UserProfile] = None,
        on_phase_complete: Optional[Callable] = None,
    ) -> DigestionResult:
        """
        执行完整认知消化流水线。

        Args:
            text: 输入文本
            title: 文章/主题标题
            source_lang: 源语言（非zh时自动调用翻译前置）
            source_type: 来源类型 (article/paper/topic)
            profile: 用户画像（覆盖默认）
            on_phase_complete: 阶段完成回调
        """
        start_time = time.time()
        phases: dict[DigestionPhase, PhaseResult] = {}
        total_cost = 0.0
        user_profile = profile or self.profile

        # ── 翻译前置（可选） ──
        if source_lang != "zh" and self.translator:
            try:
                trans_result = await self.translator.run(
                    source_text=text, title=title, source_lang=source_lang,
                    require_human_approval=False,
                )
                if trans_result.success and trans_result.final_output:
                    text = trans_result.final_output.get("final_text", text)
            except Exception as e:
                phases[DigestionPhase.ASSESS] = PhaseResult(
                    phase=DigestionPhase.ASSESS, success=False,
                    errors=[f"翻译前置失败: {e}"],
                )
                return DigestionResult(
                    success=False, phases=phases,
                    total_duration_seconds=time.time() - start_time,
                    summary="翻译前置失败",
                )

        # ── Phase 0: 难度评估 ──
        t0 = time.time()
        assess_result = self.difficulty_assessor.execute(text=text, title=title)
        test_time = time.time() - t0
        total_cost += assess_result.context.cost_usd
        phases[DigestionPhase.ASSESS] = PhaseResult(
            phase=DigestionPhase.ASSESS, success=assess_result.success,
            data=assess_result.data,
            errors=[assess_result.error] if assess_result.error else [],
            duration_seconds=test_time,
        )
        if on_phase_complete:
            on_phase_complete(DigestionPhase.ASSESS, phases[DigestionPhase.ASSESS])

        difficulty_data = assess_result.data

        # ── Phase 1: 锚点识别 ──
        t0 = time.time()
        # 从难度评估中提取核心概念
        core_concepts = self._extract_concepts(difficulty_data)
        anchor_result = self.anchor_finder.execute(
            text=text, core_concepts=core_concepts,
            profile=user_profile or UserProfile("default"),
        )
        test_time = time.time() - t0
        total_cost += anchor_result.context.cost_usd
        phases[DigestionPhase.ANCHOR] = PhaseResult(
            phase=DigestionPhase.ANCHOR, success=anchor_result.success,
            data=anchor_result.data,
            duration_seconds=test_time,
        )
        if on_phase_complete:
            on_phase_complete(DigestionPhase.ANCHOR, phases[DigestionPhase.ANCHOR])

        # ── Phase 2: 六层重构 ──
        t0 = time.time()
        restructure_result = self.restructurer.execute(
            text=text, title=title,
            difficulty_assessment=difficulty_data,
            anchor_mapping=anchor_result.data,
            profile=user_profile,
            source_type=source_type,
        )
        test_time = time.time() - t0
        total_cost += restructure_result.context.cost_usd
        phases[DigestionPhase.RESTRUCTURE] = PhaseResult(
            phase=DigestionPhase.RESTRUCTURE, success=restructure_result.success,
            data=restructure_result.data,
            duration_seconds=test_time,
        )
        if on_phase_complete:
            on_phase_complete(DigestionPhase.RESTRUCTURE, phases[DigestionPhase.RESTRUCTURE])

        output = restructure_result.data.get("output")
        if not output:
            return DigestionResult(
                success=False, phases=phases,
                total_duration_seconds=time.time() - start_time,
                summary="六层重构失败，无有效输出",
            )

        # ── Phase 3: 叙事优化 ──
        t0 = time.time()
        optimize_result = self.optimizer.execute(output=output)
        test_time = time.time() - t0
        total_cost += optimize_result.context.cost_usd
        phases[DigestionPhase.OPTIMIZE] = PhaseResult(
            phase=DigestionPhase.OPTIMIZE, success=optimize_result.success,
            data=optimize_result.data,
            duration_seconds=test_time,
        )
        if on_phase_complete:
            on_phase_complete(DigestionPhase.OPTIMIZE, phases[DigestionPhase.OPTIMIZE])

        # ── Phase 4: 认知缺口 ──
        t0 = time.time()
        gap_result = self.gap_agent.execute(output=output, profile=user_profile)
        test_time = time.time() - t0
        total_cost += gap_result.context.cost_usd
        phases[DigestionPhase.GAP] = PhaseResult(
            phase=DigestionPhase.GAP, success=gap_result.success,
            data=gap_result.data,
            duration_seconds=test_time,
        )
        if on_phase_complete:
            on_phase_complete(DigestionPhase.GAP, phases[DigestionPhase.GAP])

        # ── Phase 5: 交付 ──
        t0 = time.time()
        phases[DigestionPhase.DELIVER] = PhaseResult(
            phase=DigestionPhase.DELIVER, success=True,
            data={"output": output},
            duration_seconds=time.time() - t0,
        )

        total_duration = time.time() - start_time
        success = all(p.success for p in phases.values())

        summary = self._build_summary(phases, total_cost, total_duration)

        return DigestionResult(
            success=success,
            phases=phases,
            total_duration_seconds=total_duration,
            total_cost_usd=total_cost,
            final_output=output,
            summary=summary,
        )

    def digest_sync(
        self, text: str, title: str = "", **kwargs,
    ) -> DigestionResult:
        """同步版本"""
        return asyncio.run(self.digest(text=text, title=title, **kwargs))

    # ── 辅助 ──

    def _extract_concepts(self, difficulty_data: dict) -> list[str]:
        """从难度评估中提取核心概念列表"""
        assessment = difficulty_data.get("assessment", "")
        # 简单提取: 从 JSON 中读取 known_terms 和 unknown_terms
        import json
        try:
            data = json.loads(assessment)
            return data.get("unknown_terms", []) + data.get("known_terms", [])
        except (json.JSONDecodeError, TypeError):
            return []

    def _build_summary(self, phases, total_cost, total_duration) -> str:
        lines = [
            "=" * 60,
            "  认知消化流水线执行摘要",
            "=" * 60,
            f"  总耗时: {total_duration:.1f}s",
            f"  总成本: ${total_cost:.4f}",
            "",
        ]
        for phase, result in phases.items():
            status = "✅" if result.success else "❌"
            lines.append(f"  {status} {phase.value} ({result.duration_seconds:.1f}s)")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
