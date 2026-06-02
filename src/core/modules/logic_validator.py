from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceLink:
    evidence: str
    source_chapter: int
    source_text: str
    category: str


@dataclass
class ValidationResult:
    passed: bool
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class LogicChainValidator:
    def extract_evidence_chain(self, text: str) -> List[EvidenceLink]:
        chains: List[EvidenceLink] = []
        patterns = [
            (r"因为(.{3,50})，?所以", "direct"),
            (r"[第]?(\d+)[章节][的]?(.{5,50})[提示暗示说明]", "hint"),
            (r"等等[，,](.{5,50})[这那]", "inference"),
            (r"难道(.{5,40})[？?]", "question"),
            (r"原来(.{5,50})[。.！!]", "reveal"),
        ]
        for pattern, category in patterns:
            for match in re.finditer(pattern, text):
                chains.append(EvidenceLink(
                    evidence=match.group(1).strip(),
                    source_chapter=0,
                    source_text=match.group(0),
                    category=category,
                ))
        return chains

    def validate_knowledge_boundary(
        self, character_id: str, deduced_info: str, character_knowledge: Dict[str, Any]
    ) -> ValidationResult:
        issues = []
        suggestions = []
        known_topics = character_knowledge.get(character_id, [])
        info_keywords = self._extract_keywords(deduced_info)

        unknown_topics = [kw for kw in info_keywords if kw not in known_topics]
        if unknown_topics:
            issues.append(
                f"角色 {character_id} 推导出'{', '.join(unknown_topics[:3])}'等信息，"
                f"但TA的知识边界中不包含这些信息"
            )
            suggestions.append(
                f"前置铺垫：在前文增加角色获取'{unknown_topics[0]}'信息的场景"
            )

        return ValidationResult(passed=len(issues) == 0, issues=issues, suggestions=suggestions)

    def design_misdirection(self, target_chapter: int, plot_events: List[Dict]) -> List[str]:
        suggestions = []
        event_descriptions = [e.get("description", "") for e in plot_events if e.get("chapter", 0) < target_chapter]

        planted = [e for e in event_descriptions if "暗示" in e or "线索" in e or "发现" in e]
        if len(planted) < 3:
            suggestions.append(
                f"在第 {max(1, target_chapter - 8)} 章到第 {target_chapter - 1} 章之间，"
                f"埋设至少 3 条指向错误方向的误导线索"
            )

        surface_readings = [e for e in event_descriptions if "表面" in e or "以为" in e or "猜测" in e]
        if not surface_readings:
            suggestions.append(
                f"在误导链中至少包含 1 个'表面看似合理但实际错误'的角色推测"
            )

        return suggestions

    def verify_reversal_quality(self, reversal_text: str, context_text: str) -> ValidationResult:
        issues = []
        foreshadow_count = 0

        for match in re.finditer(r"(线索|暗示|提示|痕迹|迹象|预兆|征兆)", context_text):
            foreshadow_count += 1

        if foreshadow_count < 3:
            issues.append(
                f"反转前仅检测到 {foreshadow_count} 处线索/暗示，建议至少 3 处"
            )

        keywords = ["竟然", "原来", "没想到", "出乎意料", "反转", "其实"]
        has_surprise = any(kw in reversal_text for kw in keywords)
        if not has_surprise:
            issues.append("反转段落缺乏意外性表达")

        retroactive_count = 0
        for match in re.finditer(r"(难怪|怪不得|原来如此|所以)|才|早就|难怪)", reversal_text):
            retroactive_count += 1
        if retroactive_count == 0 and foreshadow_count > 0:
            issues.append("反转后缺少'原来如此'感的回顾确认")

        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues,
            suggestions=[
                "在反转前 3-8 章埋设至少 3 条回看才明显的线索",
                "反转段落应包含角色'恍然大悟'的时刻",
                "反转后让至少 2 个已有信息获得新含义",
            ],
        )

    def _extract_keywords(self, text: str) -> List[str]:
        stop_words = {"的", "了", "是", "在", "有", "和", "就", "不", "都", "而",
                      "及", "与", "着", "或", "一个", "没有", "我们", "他们", "你们",
                      "这", "那", "哪", "什么", "怎么", "为什么", "如何"}
        words = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        return [w for w in words if w not in stop_words][:10]


def validate(module_result: Any) -> List[str]:
    issues = []
    data = getattr(module_result, "data", {})
    text = data.get("text", "") or data.get("content", "")

    if not text or len(text) < 500:
        return issues

    validator = LogicChainValidator()
    chains = validator.extract_evidence_chain(text)

    if chains:
        deduction_len = sum(len(c.evidence) for c in chains)
        total_len = len(text)
        ratio = deduction_len / total_len if total_len > 0 else 0
        if ratio < 0.05:
            issues.append(f"推理内容占比 {ratio:.1%}，建议增加推理段落密度")

    return issues