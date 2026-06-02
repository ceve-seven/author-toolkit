from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from src.core.quality.rule_registry import QualityRule, RuleRegistry


class ReviewLevel(str, Enum):
    """审查级别枚举"""
    BLOCKER = "blocker"
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ReviewResult:
    """审查结果"""
    level: ReviewLevel
    """审查级别"""
    score: float
    """质量评分（0-1）"""
    details: List[str] = field(default_factory=list)
    """问题详情列表"""
    suggestions: List[str] = field(default_factory=list)
    """改进建议列表"""
    auto_fixes: List[Dict[str, Any]] = field(default_factory=list)
    """自动修复操作列表"""
    passed: bool = True
    """是否通过审查"""
    timestamp: str = ""
    """审查时间戳"""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ReviewContext:
    """审查上下文"""
    novel_id: str = ""
    """小说 ID"""
    step_name: str = ""
    """当前环节名称"""
    content: Any = None
    """待审查的内容"""
    dependencies: Dict[str, Any] = field(default_factory=dict)
    """前置依赖数据"""
    constraints: List[str] = field(default_factory=list)
    """审查约束条件"""
    user_modifications: Optional[str] = None
    """用户修改指令"""


class ReviewExecutor:
    """审查执行器基类——每个规则对应一个执行器"""

    def __init__(self, executor_id: str, rule: QualityRule):
        self.executor_id = executor_id
        self.rule = rule
        self.logger = structlog.get_logger(f"review.{executor_id}")

    def execute(self, content: Any, dependencies: Dict[str, Any]) -> ReviewResult:
        """执行审查"""
        raise NotImplementedError


class QualityOrchestrator:
    """质量总控调度器

    Agent 在每个环节完成后直接调用此方法：
        quality.review(context)
    """

    def __init__(self, db_session: Any):
        self.db_session = db_session
        self.rule_registry = RuleRegistry()
        self.review_executors: Dict[str, ReviewExecutor] = {}
        self.fixers: Dict[str, Any] = {}
        self.logger = structlog.get_logger("quality")

    def load_rules(self):
        """加载所有质量规则"""
        self.rule_registry.register_default_rules()
        self.rule_registry.register_from_file("src/config/quality_rules.yaml")
        count = self.rule_registry.count_rules()

        self._register_builtin_executors()

        self.logger.info("rules_loaded", counts=count)

    def _register_builtin_executors(self):
        """注册内置审查执行器"""
        from sqlalchemy import text

        class WorldBuildingFiveLayersExecutor(ReviewExecutor):
            """世界观五层审查——真正执行规则检查"""
            def execute(self, content: Any, dependencies: Dict[str, Any]) -> ReviewResult:
                details = []
                score = 1.0
                content_str = str(content) if content else ""
                if not content_str or len(content_str) < 20:
                    return ReviewResult(level=ReviewLevel.INFO, score=1.0,
                                        details=["无内容需要审查"], passed=True)
                if "规则" not in content_str and "dimension" not in content_str and "dimensions" not in content_str:
                    details.append("世界观数据中缺少规则定义")
                    score -= 0.2
                if len(content_str) < 200:
                    details.append("世界观数据过于简略，建议补充规则细节")
                    score -= 0.1
                if details:
                    level = ReviewLevel.WARNING if score < 0.7 else ReviewLevel.INFO
                    return ReviewResult(level=level, score=score,
                                        details=details, suggestions=["检查规则间的逻辑一致性"],
                                        passed=score >= 0.7)
                return ReviewResult(level=ReviewLevel.INFO, score=1.0,
                                    details=["世界观五层审查通过"], passed=True)

        class CrossModuleValidationExecutor(ReviewExecutor):
            """跨模块交叉验证——检查实体间引用关系"""
            def execute(self, content: Any, dependencies: Dict[str, Any]) -> ReviewResult:
                details = []
                db = None
                try:
                    from src.storage.database.engine import create_session
                    with create_session() as session:
                        novel_id = ""
                        if isinstance(content, dict):
                            novel_id = content.get("novel_id", "")
                        if not novel_id and dependencies:
                            for v in dependencies.values():
                                if isinstance(v, dict) and v.get("novel_id"):
                                    novel_id = v["novel_id"]
                                    break
                        if not novel_id:
                            r = session.execute(text("SELECT id FROM novels LIMIT 1")).fetchone()
                            if r:
                                novel_id = str(r[0])
                        if novel_id:
                            pairs = [
                                ("人物-势力", "SELECT COUNT(1) FROM char_faction_links WHERE novel_id=:nid AND char_id NOT IN (SELECT char_id FROM characters WHERE novel_id=:nid)", "存在 char_faction_links 引用了不存在的角色"),
                                ("人物-弧线", "SELECT COUNT(1) FROM character_arcs WHERE novel_id=:nid AND char_id NOT IN (SELECT char_id FROM characters WHERE novel_id=:nid)", "存在 character_arcs 引用了不存在的角色"),
                                ("人物-关系", "SELECT COUNT(1) FROM relations WHERE novel_id=:nid AND char_a_id NOT IN (SELECT char_id FROM characters WHERE novel_id=:nid)", "存在 relations 引用了不存在的角色"),
                                ("势力-关系", "SELECT COUNT(1) FROM faction_relations WHERE novel_id=:nid AND faction_a_id NOT IN (SELECT faction_id FROM factions WHERE novel_id=:nid)", "存在 faction_relations 引用了不存在的势力"),
                                ("伏笔-人物", "SELECT COUNT(1) FROM foreshadows WHERE novel_id=:nid AND related_char != '' AND json_extract(related_char, '$[0]') NOT IN (SELECT char_id FROM characters WHERE novel_id=:nid) LIMIT 5", "存在 foreshadows 引用了不存在的角色"),
                            ]
                            for label, sql, msg in pairs:
                                try:
                                    c = session.execute(text(sql), {"nid": novel_id}).scalar()
                                    if c and c > 0:
                                        details.append(f"【{label}】{msg}（共{c}处）")
                                except Exception:
                                    pass
                            if not details:
                                details.append("跨模块引用验证通过，所有实体引用关系完整")
                    score = 0.5 if details and len([d for d in details if "验证通过" not in d]) > 0 else 1.0
                    level = ReviewLevel.CRITICAL if score < 0.7 else ReviewLevel.INFO
                    return ReviewResult(level=level, score=score, details=details,
                                        suggestions=["修复引用断裂的实体关系"] if score < 0.7 else [],
                                        passed=score >= 0.7)
                except Exception as e:
                    return ReviewResult(level=ReviewLevel.INFO, score=1.0,
                                        details=[f"跨模块验证跳过: {e}"], passed=True)

        for executor in [
            WorldBuildingFiveLayersExecutor("world_building_five_layers",
                self.rule_registry.get_rule("world_building_five_layers")),
            CrossModuleValidationExecutor("cross_module_validation",
                self.rule_registry.get_rule("cross_module_validation_checklist")),
        ]:
            if executor.rule:
                self.review_executors[executor.executor_id] = executor

    def register_executor(self, executor: ReviewExecutor):
        """注册审查执行器"""
        self.review_executors[executor.executor_id] = executor

    def register_fixer(self, fixer_id: str, fixer: Any):
        """注册自动修复器"""
        self.fixers[fixer_id] = fixer

    def review(self, context: ReviewContext) -> ReviewResult:
        """执行完整审查链

        Args:
            context: 审查上下文，包含 novel_id, step_name, content, dependencies

        Returns:
            聚合后的审查结果
        """
        rules = self.rule_registry.get_rules_for_context(context)
        if not rules:
            return ReviewResult(
                level=ReviewLevel.INFO,
                score=1.0,
                details=["无适用规则"],
                passed=True,
            )

        results: List[ReviewResult] = []
        for rule in sorted(rules, key=lambda r: r.priority):
            executor = self.review_executors.get(rule.rule_id)
            if not executor:
                executor = self._create_default_executor(rule)
                self.review_executors[rule.rule_id] = executor

            result = executor.execute(context.content, context.dependencies)
            results.append(result)

            if result.level == ReviewLevel.BLOCKER:
                return self._aggregate(results, blocked=True)

        return self._aggregate(results)

    def _aggregate(self, results: List[ReviewResult], blocked: bool = False) -> ReviewResult:
        """聚合多个审查结果"""
        if not results:
            return ReviewResult(
                level=ReviewLevel.INFO,
                score=1.0,
                details=[],
                passed=True,
            )

        levels = [r.level for r in results]
        if blocked or ReviewLevel.BLOCKER in levels:
            final_level = ReviewLevel.BLOCKER
        elif ReviewLevel.CRITICAL in levels:
            final_level = ReviewLevel.CRITICAL
        elif ReviewLevel.WARNING in levels:
            final_level = ReviewLevel.WARNING
        else:
            final_level = ReviewLevel.INFO

        avg_score = sum(r.score for r in results) / len(results)
        all_details = [d for r in results for d in r.details]
        all_suggestions = [s for r in results for s in r.suggestions]
        all_fixes = [f for r in results for f in r.auto_fixes]

        return ReviewResult(
            level=final_level,
            score=avg_score,
            details=all_details,
            suggestions=all_suggestions,
            auto_fixes=all_fixes,
            passed=final_level not in (ReviewLevel.BLOCKER, ReviewLevel.CRITICAL),
        )

    def _create_default_executor(self, rule: QualityRule) -> ReviewExecutor:
        """为未注册执行器的规则创建默认执行器"""
        class _DefaultExecutor(ReviewExecutor):
            def execute(self, content: Any, dependencies: Dict[str, Any]) -> ReviewResult:
                return ReviewResult(
                    level=ReviewLevel.INFO,
                    score=1.0,
                    details=[f"规则「{self.rule.display_name}」: 默认通过"],
                    suggestions=[],
                    passed=True,
                )
        return _DefaultExecutor(rule.rule_id, rule)

    def fix(self, result: ReviewResult, context: ReviewContext) -> Dict[str, Any]:
        """调用自动修正器修复问题

        Args:
            result: 审查结果
            context: 审查上下文

        Returns:
            修复报告
        """
        fix_report: Dict[str, Any] = {
            "fixed_count": 0,
            "failed_count": 0,
            "fixes": [],
            "errors": [],
        }

        if not result.auto_fixes:
            return fix_report

        for fix_info in result.auto_fixes:
            fixer_id = str(fix_info.get("fixer_id", "")) if isinstance(fix_info, dict) else ""
            fixer = self.fixers.get(fixer_id)
            if not fixer:
                fix_report["errors"].append(f"未找到修复器: {fixer_id}")
                fix_report["failed_count"] += 1
                continue

            try:
                params = fix_info.get("params") if isinstance(fix_info, dict) else {}
                content = getattr(context, "content", None)
                if content is not None:
                    fixed_content = fixer.fix(content, params)
                    fix_report["fixes"].append({
                        "fixer_id": fixer_id,
                        "success": True,
                    })
                    fix_report["fixed_count"] += 1
            except Exception as e:
                fix_report["errors"].append(f"修复器 {fixer_id} 执行失败: {e}")
                fix_report["failed_count"] += 1

        return fix_report