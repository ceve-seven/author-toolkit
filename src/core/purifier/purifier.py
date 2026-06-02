from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.core.purifier.detector import AITraceDetector, TraceIssue
from src.core.purifier.pipeline import PurificationPipeline


@dataclass
class PurificationResult:
    """清除结果"""
    passed: bool
    """是否全部自动通过"""
    text: str
    """清除后的文本"""
    issues: List[TraceIssue] = field(default_factory=list)
    """检测到的问题列表"""
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    """L2 半自动修复建议"""
    report: str = ""
    """清除报告"""
    auto_fixed_count: int = 0
    """自动修复数量"""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class AITracePurifier:
    """AI 痕迹清除执行器

    整合检测 + 修复两个阶段：
    - 检测：调用 AITraceDetector 识别 6 大特征
    - 修复：根据配置的修复级别执行自动或半自动清除
    """

    def __init__(self, auto_fix_levels: Optional[List[int]] = None):
        self.detector = AITraceDetector()
        self.pipeline = PurificationPipeline()
        self.auto_fix_levels = auto_fix_levels or [1, 2]
        self.logger = structlog.get_logger("ai_purifier")

    def purify(
        self,
        text: str,
        auto_fix_levels: Optional[List[int]] = None,
    ) -> PurificationResult:
        """执行 AI 痕迹检测和清除

        Args:
            text: 待处理的文本
            auto_fix_levels: 自动修复级别列表，不传则使用默认配置

        Returns:
            清除结果
        """
        levels = auto_fix_levels or self.auto_fix_levels
        self.logger.info("purify_start", text_length=len(text), auto_fix_levels=levels)

        pipeline_result = self.pipeline.purify(text)

        issues = pipeline_result.issues if hasattr(pipeline_result, "issues") else []
        final_text = pipeline_result.text if hasattr(pipeline_result, "text") else text
        suggestions = pipeline_result.suggestions if hasattr(pipeline_result, "suggestions") else []
        report = pipeline_result.report if hasattr(pipeline_result, "report") else ""

        l1_count = sum(1 for i in issues if i.fix_level == 1) if issues else 0
        l2_count = sum(1 for i in issues if i.fix_level == 2) if issues else 0
        l3_count = sum(1 for i in issues if i.fix_level == 3) if issues else 0

        self.logger.info(
            "purify_complete",
            total_issues=len(issues),
            l1_auto=l1_count,
            l2_semi=l2_count,
            l3_report=l3_count,
        )

        return PurificationResult(
            passed=(l2_count == 0 and l3_count == 0),
            text=final_text,
            issues=issues,
            suggestions=suggestions,
            report=report or self._build_report(issues, l1_count),
            auto_fixed_count=l1_count,
        )

    def _build_report(self, issues: List[TraceIssue], auto_fixed: int) -> str:
        """生成清除报告"""
        if not issues:
            return "✅ 未检测到 AI 痕迹问题"

        lines = [
            "## AI 痕迹清除报告",
            "",
            f"检测到 {len(issues)} 处问题，自动修复 {auto_fixed} 处",
            "",
        ]

        severity_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        for issue in issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            type_counts[issue.trait_type] = type_counts.get(issue.trait_type, 0) + 1

        lines.append("### 问题统计")
        lines.append("")
        for sev, count in severity_counts.items():
            lines.append(f"- {sev.upper()}: {count} 处")
        lines.append("")

        for ttype, count in type_counts.items():
            level_label = {1: "L1自动", 2: "L2半自动", 3: "L3仅报告"}
            fl = next((i.fix_level for i in issues if i.trait_type == ttype), 1)
            lines.append(f"- {ttype}: {count} 处 ({level_label.get(fl, '未知')})")
            suggestion = next((i.suggestion for i in issues if i.trait_type == ttype), "")
            if suggestion:
                lines.append(f"  建议: {suggestion}")

        return "\n".join(lines)

    def detect_only(self, text: str) -> List[TraceIssue]:
        """仅检测 AI 痕迹，不执行修复"""
        return self.detector.detect(text)