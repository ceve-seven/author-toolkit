from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.quality.orchestrator import ReviewLevel, ReviewResult


@dataclass
class AggregatedReport:
    """聚合审查报告"""
    title: str
    """报告标题"""
    summary: str
    """报告摘要"""
    overall_level: ReviewLevel
    """总体级别"""
    overall_score: float
    """总体评分"""
    module_reports: List[Dict[str, Any]]
    """各模块审查报告列表"""
    cross_module_issues: List[str]
    """跨模块问题列表"""
    improvement_trend: Optional[List[float]]
    """改进趋势（历史评分序列）"""
    generated_at: str
    """生成时间"""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()


class ReportAggregator:
    """审查报告聚合器——聚合多个审查结果并生成结构化报告"""

    def __init__(self):
        self._history: Dict[str, List[float]] = {}

    def aggregate(
        self,
        results: List[ReviewResult],
        module_names: Optional[List[str]] = None,
        title: str = "综合审查报告",
    ) -> AggregatedReport:
        """聚合多个审查结果

        Args:
            results: 审查结果列表
            module_names: 对应的模块名称列表
            title: 报告标题

        Returns:
            聚合后的审查报告
        """
        if not results:
            return AggregatedReport(
                title=title,
                summary="无审查结果",
                overall_level=ReviewLevel.INFO,
                overall_score=1.0,
                module_reports=[],
                cross_module_issues=[],
                improvement_trend=None,
                generated_at=datetime.now().isoformat(),
            )

        levels = [r.level for r in results]
        if ReviewLevel.BLOCKER in levels:
            overall_level = ReviewLevel.BLOCKER
        elif ReviewLevel.CRITICAL in levels:
            overall_level = ReviewLevel.CRITICAL
        elif ReviewLevel.WARNING in levels:
            overall_level = ReviewLevel.WARNING
        else:
            overall_level = ReviewLevel.INFO

        overall_score = sum(r.score for r in results) / len(results)

        module_reports = []
        all_details: List[str] = []
        all_suggestions: List[str] = []
        cross_module_issues: List[str] = []

        for i, result in enumerate(results):
            module_name = module_names[i] if module_names and i < len(module_names) else f"模块{i+1}"
            module_reports.append({
                "module": module_name,
                "level": result.level.value,
                "score": result.score,
                "details": result.details,
                "suggestions": result.suggestions,
                "passed": result.passed,
            })
            all_details.extend(result.details)
            all_suggestions.extend(result.suggestions)

        cross_module_issues = self._detect_cross_module_issues(results, module_names)

        summary_parts = [
            f"共审查 {len(results)} 个模块",
            f"最高级别: {overall_level.value.upper()}",
            f"综合评分: {overall_score:.2f}",
            f"发现问题: {len(all_details)} 项",
        ]
        summary = " | ".join(summary_parts)

        trend = self._update_trend("_global", overall_score)

        return AggregatedReport(
            title=title,
            summary=summary,
            overall_level=overall_level,
            overall_score=overall_score,
            module_reports=module_reports,
            cross_module_issues=cross_module_issues,
            improvement_trend=trend,
            generated_at=datetime.now().isoformat(),
        )

    def _detect_cross_module_issues(
        self,
        results: List[ReviewResult],
        module_names: Optional[List[str]],
    ) -> List[str]:
        """检测跨模块的一致性问题"""
        issues: List[str] = []
        if not module_names or len(results) < 2:
            return issues

        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                r1, r2 = results[i], results[j]
                if r1.level == ReviewLevel.CRITICAL and r2.level == ReviewLevel.CRITICAL:
                    issues.append(
                        f"模块「{module_names[i]}」和「{module_names[j]}」均出现严重问题"
                    )
        return issues

    def _update_trend(self, key: str, score: float) -> Optional[List[float]]:
        """更新评分趋势历史"""
        if key not in self._history:
            self._history[key] = []
        self._history[key].append(score)
        return self._history[key][-5:]

    def to_markdown(self, report: AggregatedReport) -> str:
        """将聚合报告转换为 Markdown 格式"""
        level_icons = {
            ReviewLevel.BLOCKER: "⛔",
            ReviewLevel.CRITICAL: "⚠",
            ReviewLevel.WARNING: "⚡",
            ReviewLevel.INFO: "✓",
        }
        icon = level_icons.get(report.overall_level, "•")

        lines = [
            f"# {report.title}",
            f"",
            f"**生成时间**: {report.generated_at}",
            f"",
            f"## 总体评估",
            f"",
            f"- {icon} **级别**: {report.overall_level.value.upper()}",
            f"- **综合评分**: {report.overall_score:.2f}",
            f"- **摘要**: {report.summary}",
        ]

        if report.improvement_trend and len(report.improvement_trend) > 1:
            trend_str = " → ".join(f"{s:.2f}" for s in report.improvement_trend)
            lines.extend([
                f"",
                f"## 改进趋势",
                f"",
                f"```",
                f"评分变化: {trend_str}",
                f"```",
            ])

        lines.extend([
            f"",
            f"## 模块审查详情",
            f"",
        ])

        for mr in report.module_reports:
            module_icon = level_icons.get(
                ReviewLevel(mr["level"]), "•"
            )
            lines.extend([
                f"### {module_icon} {mr['module']}",
                f"",
                f"- 级别: {mr['level'].upper()}",
                f"- 评分: {mr['score']:.2f}",
                f"- 状态: {'通过' if mr['passed'] else '需改进'}",
            ])
            if mr["details"]:
                lines.append(f"")
                lines.append(f"**问题详情:**")
                for d in mr["details"]:
                    lines.append(f"- {d}")
            if mr["suggestions"]:
                lines.append(f"")
                lines.append(f"**改进建议:**")
                for s in mr["suggestions"]:
                    lines.append(f"- {s}")
            lines.append(f"")

        if report.cross_module_issues:
            lines.extend([
                f"## 跨模块问题",
                f"",
            ])
            for issue in report.cross_module_issues:
                lines.append(f"- {issue}")
            lines.append(f"")

        return "\n".join(lines)

    def get_history(self) -> Dict[str, List[float]]:
        """获取历史评分数据"""
        return dict(self._history)

    def clear_history(self):
        """清除历史数据"""
        self._history.clear()