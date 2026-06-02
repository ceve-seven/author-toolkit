from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.purifier.detector import AITraceDetector, TraceIssue
from src.core.purifier.fixers.sentence_rhythm_fixer import SentenceRhythmFixer
from src.core.purifier.fixers.transition_word_fixer import TransitionWordFixer
from src.core.purifier.fixers.emotion_showing_fixer import EmotionShowingFixer
from src.core.purifier.fixers.dialogue_naturalizer import DialogueNaturalizer
from src.core.purifier.fixers.description_defaulter import DescriptionDefaulter
from src.core.purifier.fixers.simile_fixer import SimileFixer


@dataclass
class PipelineResult:
    """流水线执行结果"""
    passed: bool
    """是否全部自动通过"""
    text: str
    """处理后的文本"""
    issues: List[TraceIssue] = field(default_factory=list)
    """检测到的问题列表"""
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    """L2 半自动修复建议"""
    report: str = ""
    """处理报告"""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class PurificationPipeline:
    """AI 痕迹清除流水线

    三级清除策略：
    - L1 自动修复：无需用户介入，自动执行（句式/过渡词/描写模板）
    - L2 半自动：AI 提供 3 种方案供用户选择（情感表达/对话优化）
    - L3 仅报告：标记位置供用户决策（安全化倾向）
    """

    def __init__(self):
        self.detector = AITraceDetector()
        self.detector.update_thresholds_from_yaml()
        self._init_fixers()

    def _init_fixers(self):
        """初始化所有修复器"""
        self.l1_fixers = [
            ("sentence_rhythm", SentenceRhythmFixer()),
            ("transition_word", TransitionWordFixer()),
            ("description_template", DescriptionDefaulter()),
            ("simile_overuse", SimileFixer()),
        ]
        self.l2_fixers = [
            ("emotion_showing", EmotionShowingFixer()),
            ("dialogue_naturalizer", DialogueNaturalizer()),
        ]

    def purify(self, text: str) -> PipelineResult:
        """执行完整的 AI 痕迹清除流水线

        Args:
            text: 待处理的文本

        Returns:
            流水线执行结果
        """
        issues = self.detector.detect(text)
        if not issues:
            return PipelineResult(
                passed=True,
                text=text,
                issues=[],
                suggestions=[],
                report="✅ 未检测到 AI 痕迹问题",
            )

        l1_issues = [i for i in issues if i.fix_level == 1]
        l2_issues = [i for i in issues if i.fix_level == 2]
        l3_issues = [i for i in issues if i.fix_level == 3]

        text = self._auto_fix(text, l1_issues)

        suggestions = self._generate_suggestions(text, l2_issues) if l2_issues else []

        report = self._build_report(l1_issues, l2_issues, l3_issues)

        return PipelineResult(
            passed=len(issues) == len(l1_issues),
            text=text,
            issues=issues,
            suggestions=suggestions,
            report=report,
        )

    def _auto_fix(self, text: str, issues: List[TraceIssue]) -> str:
        """执行 L1 自动修复

        根据检测到的问题类型，依次执行对应的自动修复器。
        """
        if not issues:
            return text

        issue_types = {i.trait_type for i in issues}
        for fixer_name, fixer in self.l1_fixers:
            should_fix = self._fixer_applies(fixer_name, issue_types)
            if should_fix and fixer.validate(text):
                text = fixer.fix(text)

        return text

    def _generate_suggestions(
        self,
        text: str,
        issues: List[TraceIssue],
    ) -> List[Dict[str, Any]]:
        """生成 L2 半自动修复建议

        每个问题生成 3 种修复方案供用户选择。
        """
        suggestions: List[Dict[str, Any]] = []
        issue_types = {i.trait_type for i in issues}

        for fixer_name, fixer in self.l2_fixers:
            should_fix = self._fixer_applies(fixer_name, issue_types)
            if not should_fix or not fixer.validate(text):
                continue

            variants = []
            for i in range(3):
                variant_text = fixer.fix(text, {"variant": i})
                if variant_text != text:
                    variants.append(variant_text[:200])

            if variants:
                suggestions.append({
                    "fixer": fixer_name,
                    "type": "半自动修复",
                    "variants": variants,
                    "description": f"为 {fixer_name} 问题提供 {len(variants)} 种修复方案",
                })

        return suggestions

    def _build_report(
        self,
        l1_issues: List[TraceIssue],
        l2_issues: List[TraceIssue],
        l3_issues: List[TraceIssue],
    ) -> str:
        """生成处理报告"""
        lines = [
            "## AI 痕迹清除报告",
            "",
        ]

        if l1_issues:
            lines.append(f"### L1 自动修复（{len(l1_issues)} 处）")
            lines.append("")
            for issue in l1_issues:
                lines.append(f"- ✅ {issue.trait_type}: {issue.detail}")
            lines.append("")

        if l2_issues:
            lines.append(f"### L2 半自动修复（{len(l2_issues)} 处）")
            lines.append("")
            for issue in l2_issues:
                lines.append(f"- ⚡ {issue.trait_type}: {issue.detail}")
                lines.append(f"  建议: {issue.suggestion}")
            lines.append("")

        if l3_issues:
            lines.append(f"### L3 仅报告（{len(l3_issues)} 处）")
            lines.append("")
            for issue in l3_issues:
                lines.append(f"- ℹ {issue.trait_type}: {issue.detail}")
                lines.append(f"  建议: {issue.suggestion}")
            lines.append("")

        total = len(l1_issues) + len(l2_issues) + len(l3_issues)
        lines.append(f"---")
        lines.append(f"共处理 {total} 处问题: L1={len(l1_issues)} L2={len(l2_issues)} L3={len(l3_issues)}")

        return "\n".join(lines)

    def _fixer_applies(self, fixer_name: str, issue_types: set) -> bool:
        """判断修复器是否适用于当前检测到的问题集合"""
        mapping = {
            "sentence_rhythm": {"sentence_rhythm_uniform"},
            "transition_word": {"transition_word_overuse"},
            "description_template": {"description_templated"},
            "simile_overuse": {"simile_overuse"},
            "emotion_showing": {"emotion_telling", "direct_emotion_telling"},
            "dialogue_naturalizer": {"dialogue_functional"},
        }
        mapped = mapping.get(fixer_name, set())
        return bool(mapped & issue_types)