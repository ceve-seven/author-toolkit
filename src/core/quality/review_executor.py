from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.core.modules.base_module import BaseModule, ModuleResult
from src.core.quality.orchestrator import (
    QualityOrchestrator,
    ReviewContext,
    ReviewLevel,
    ReviewResult,
)
from src.core.purifier.detector import AITraceDetector


class ReviewExecutor(BaseModule):
    """正文审查执行器（环节 17）

    四层审查:
    1. 设定一致性检查
    2. 逻辑合理性检查
    3. 文笔质量检查
    4. 读者体验检查
    """

    module_name = "review_executor"
    depends_on = ["manuscript_writer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = structlog.get_logger("review_executor")
        self.detector = AITraceDetector()

    def run(self, context: Dict[str, Any], content: Any) -> ModuleResult:
        """执行四层审查"""
        self.logger.info("review_start")

        novel_id = context.get("novel_id", "")
        step_name = context.get("step_name", "正文审核")
        text: str = ""
        if isinstance(content, dict):
            text = str(content.get("text") or content.get("content") or "")
        elif hasattr(content, "text"):
            text = str(content.text)
        else:
            text = str(content)

        review_context = ReviewContext(
            novel_id=novel_id,
            step_name=step_name,
            content=text,
            dependencies=context.get("dependencies", {}),
        )

        layers = [
            ("设定一致性", self._check_setting_consistency),
            ("逻辑合理性", self._check_logic_consistency),
            ("文笔质量",   self._check_writing_quality),
            ("读者体验",   self._check_reader_experience),
        ]

        all_details: List[str] = []
        all_suggestions: List[str] = []
        overall_level = ReviewLevel.INFO
        total_score = 0.0

        for layer_name, check_fn in layers:
            layer_result: ReviewResult = check_fn(text, review_context)
            all_details.extend(layer_result.details)
            all_suggestions.extend(layer_result.suggestions)
            if self._compare_level(layer_result.level, overall_level) > 0:
                overall_level = layer_result.level
            total_score += layer_result.score

        avg_score = total_score / len(layers) if layers else 1.0

        ai_trace_issues = self.detector.detect(text)
        if ai_trace_issues:
            all_details.append(f"AI 痕迹检测: 发现 {len(ai_trace_issues)} 处问题")
            for issue in ai_trace_issues[:5]:
                all_details.append(f"  - [{issue.severity}] {issue.detail}")

        review_result = ReviewResult(
            level=overall_level,
            score=avg_score,
            details=all_details,
            suggestions=all_suggestions,
            passed=overall_level not in (ReviewLevel.BLOCKER,),
        )

        report_text = self._format_report(review_result, ai_trace_issues)
        print(report_text)

        self.logger.info(
            "review_complete",
            level=str(overall_level),
            score=avg_score,
            issues=len(all_details),
        )

        return ModuleResult(
            success=True,
            summary=f"审查级别: {overall_level.value}, 评分: {avg_score:.2f}, 问题数: {len(all_details)}",
            data={
                "review_result": {
                    "level": overall_level.value,
                    "score": avg_score,
                    "details": all_details,
                    "suggestions": all_suggestions,
                },
                "ai_trace_issues": [
                    {
                        "type": i.trait_type,
                        "severity": i.severity,
                        "detail": i.detail,
                    }
                    for i in ai_trace_issues
                ],
            },
            word_count=len(text),
        )

    def _check_setting_consistency(self, text: str, ctx: ReviewContext) -> ReviewResult:
        """第一层：设定一致性检查"""
        details: List[str] = []
        suggestions: List[str] = []
        score = 1.0

        deps = ctx.dependencies
        world_data = deps.get("世界观设定") or deps.get("world_building")
        char_data = deps.get("人物设定") or deps.get("characters")

        if world_data:
            world_mentions = self._extract_world_refs(text)
            if world_mentions:
                details.append(f"文本中识别到 {len(world_mentions)} 处世界观引用")
                score = 0.9

        if char_data:
            char_mentions = self._extract_char_refs(text)
            if char_mentions:
                details.append(f"文本中识别到 {len(char_mentions)} 处角色引用")
                score = min(score, 0.9)

        return ReviewResult(
            level=ReviewLevel.INFO,
            score=score,
            details=details,
            suggestions=suggestions,
            passed=score >= 0.7,
        )

    def _check_logic_consistency(self, text: str, ctx: ReviewContext) -> ReviewResult:
        """第二层：逻辑合理性检查——检测常识性矛盾和设定冲突"""
        details: List[str] = []
        suggestions: List[str] = []
        score = 1.0

        sentences = [s.strip() for s in text.replace("！", "。").replace("？", "。").split("。") if s.strip()]
        if len(sentences) < 3:
            details.append("文本段落过短，逻辑链可能不完整")
            suggestions.append("建议扩充内容，确保因果链完整")
            score -= 0.3

        contradiction_patterns = [
            ("但.*却.*同[一]", "前后矛盾：'但...却...' 与 '同一' 句式可能自相矛盾"),
            ("所[以以].*因[为为]", "因果倒置：'所以...因为...' 因果顺序颠倒"),
            ("[虽虽].*但但.*[而而]", "让步转折重叠：'虽然...但是...然而' 过度使用"),
            ("永[远远].*从[未未]", "时序矛盾：'永远' 和 '从未' 在同一语境中冲突"),
            ("全[部部].*[只只]有", "范围矛盾：'全部' 和 '只有' 逻辑冲突"),
            ("同[一].*同[一]", "概念重叠：'同一...同一...' 出现逻辑循环定义"),
        ]
        for pattern, msg in contradiction_patterns:
            import re
            if re.search(pattern, text):
                details.append(msg)
                score -= 0.15

        positive_negative = ["是.*不[是是]", "有.*没[有有]", "能.*不[能能]"]
        for pn in positive_negative:
            import re
            matches = re.findall(pn, text)
            if len(matches) > 3:
                details.append(f"正反对比句式使用频繁（{len(matches)}处），可能造成逻辑混乱")
                score -= 0.1
                break

        text_lower = text.lower()
        if "因为" in text_lower and "所以" not in text_lower:
            pass
        if "所以" in text_lower and "因为" not in text_lower and "由于" not in text_lower:
            pass

        if score < 0.7:
            suggestions.append("检查文本中的逻辑链条，确保因果一致、前后不矛盾")

        return ReviewResult(
            level=ReviewLevel.WARNING if score < 0.7 else ReviewLevel.INFO,
            score=max(score, 0.0),
            details=details,
            suggestions=suggestions,
            passed=score >= 0.7,
        )

    def _check_writing_quality(self, text: str, ctx: ReviewContext) -> ReviewResult:
        """第三层：文笔质量检查（统一使用 AITraceDetector）"""
        details: List[str] = []
        suggestions: List[str] = []
        score = 1.0

        trace_issues = self.detector.detect(text)
        if not trace_issues:
            return ReviewResult(
                level=ReviewLevel.INFO,
                score=1.0,
                details=["未检测到 AI 痕迹问题"],
                suggestions=[],
                passed=True,
            )

        critical_count = sum(1 for i in trace_issues if i.severity == "critical")
        warning_count = sum(1 for i in trace_issues if i.severity == "warning")

        for issue in trace_issues:
            details.append(f"[{issue.severity.upper()}] {issue.trait_type}: {issue.detail}")
            if issue.suggestion:
                suggestions.append(issue.suggestion)

        if critical_count > 0:
            level = ReviewLevel.CRITICAL
            score = max(0.3, 1.0 - critical_count * 0.25)
        elif warning_count > 0:
            level = ReviewLevel.WARNING
            score = max(0.6, 1.0 - warning_count * 0.15)
        else:
            level = ReviewLevel.INFO

        return ReviewResult(
            level=level,
            score=score,
            details=details,
            suggestions=suggestions,
            passed=level != ReviewLevel.CRITICAL,
        )

    def _check_reader_experience(self, text: str, ctx: ReviewContext) -> ReviewResult:
        """第四层：读者体验检查"""
        details: List[str] = []
        suggestions: List[str] = []
        score = 1.0

        total_chars = len(text)
        if total_chars < 500:
            details.append(f"正文字数偏少（{total_chars} 字）")
            suggestions.append("建议增加内容充实度")
            score = 0.6

        dialogue_lines = len(re.findall(r'"([^"]*)"', text)) if 're' in dir() else text.count("\"") // 2
        if total_chars > 0 and dialogue_lines == 0:
            details.append("文本中未检测到对话")
            suggestions.append("建议适当加入对话增强可读性")
            score = min(score, 0.7)

        return ReviewResult(
            level=ReviewLevel.WARNING if score < 0.7 else ReviewLevel.INFO,
            score=score,
            details=details,
            suggestions=suggestions,
            passed=score >= 0.7,
        )

    def _extract_world_refs(self, text: str) -> List[str]:
        """提取文本中的世界观引用"""
        import re
        patterns = [r"(?:在|于|来到|进入|位于)([^，。]{2,8}(?:大陆|世界|王国|帝国|城|镇|村|森林|山脉|河|海|湖|岛))"]
        refs = []
        for p in patterns:
            refs.extend(re.findall(p, text))
        return list(set(refs))

    def _extract_char_refs(self, text: str) -> List[str]:
        """提取文本中的角色引用"""
        import re
        pattern = r"([\u4e00-\u9fff]{2,4})(?:说|道|问|答|想|看|走|站|坐|笑|哭|怒)"
        matches = re.findall(pattern, text)
        return list(set(matches))

    def _compare_level(self, a: ReviewLevel, b: ReviewLevel) -> int:
        """比较两个审查级别的高低"""
        order = [ReviewLevel.INFO, ReviewLevel.WARNING, ReviewLevel.CRITICAL, ReviewLevel.BLOCKER]
        return order.index(a) - order.index(b)

    def _format_report(self, result: ReviewResult, ai_issues: list) -> str:
        """格式化审查报告为可读文本"""
        lines = [
            f"\n{'='*60}",
            f"📋 正文审查报告",
            f"{'='*60}",
            f"  级别: {result.level.value.upper()}",
            f"  评分: {result.score:.2f}",
            f"  状态: {'✓ 通过' if result.passed else '⚠ 需改进'}",
        ]
        if result.details:
            lines.append(f"\n  问题详情:")
            for d in result.details:
                lines.append(f"    - {d}")
        if result.suggestions:
            lines.append(f"\n  改进建议:")
            for s in result.suggestions:
                lines.append(f"    - {s}")
        if ai_issues:
            lines.append(f"\n  AI 痕迹检测（独立扫描）: {len(ai_issues)} 处")
            for issue in ai_issues[:3]:
                lines.append(f"    - [{issue.severity}] {issue.detail}")
        lines.append(f"{'='*60}\n")
        return "\n".join(lines)


import re