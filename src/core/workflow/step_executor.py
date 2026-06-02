"""AI Agent 单步执行器 — 每步强制执行：约束验证 → 模块执行 → 质量审查 → 同步输出

AI Agent 不允许自行编写 Python 脚本执行模块，必须通过此执行器完成每一步。
"""
from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from src.core.modules.registry import get_registry
from src.core.modules.base_module import BaseModule, ModuleResult


# ============================================================
# 步骤定义 — 20 步完整管线
# ============================================================

STEP_DEFINITIONS = [
    # (步骤号, 环节名, 模块名, 需要质检, 依赖步骤号列表)
    (1,  "灵感启动",     "theme_engine",       False, []),
    (2,  "小说主题",     "theme_engine",       False, [1]),
    (3,  "世界观设定",   "world_builder",       False, [2]),
    (4,  "人物设定",     "character_builder",   False, [3]),
    (5,  "势力设定",     "faction_builder",     False, [3]),
    (6,  "物品库",       "item_builder",        False, [3]),
    (7,  "人物关系",     "relation_builder",    False, [4]),
    (8,  "势力关系",     "faction_relation",    False, [5]),
    (9,  "人物-势力关联", "char_faction_bridge", False, [4, 5, 7, 8]),
    (10, "角色弧线",     "arc_builder",         False, [4, 7, 9]),
    (11, "伏笔追踪",     "foreshadow_manager",  False, [4, 5, 6]),
    (12, "拟定大纲",     "outline_builder",     False, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]),
    (13, "分卷配置",     "volume_config",       True,  [12]),
    (14, "章节细纲",     "detail_outline",      True,  [13]),
    (15, "小说档案",     "archive_builder",     False, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]),
    (16, "小说简介",     "synopsis_builder",    False, [15]),
    (17, "正文初稿",     "manuscript_writer",   True,  [14]),
    (18, "正文审核",     "review_executor",     True,  [17]),
    (19, "正文修正",     "manuscript_fixer",    True,  [18]),
    (20, "导出发布",     "export_tool",         False, [19]),
]


# ============================================================
# 约束定义 — 对应 章节细纲.md 的规则
# ============================================================

@dataclass
class ConstraintViolation:
    rule: str
    severity: str  # "error" / "warning"
    message: str
    suggestion: str


class ConstraintsEngine:
    """约束验证引擎 — 强制执行 章节细纲.md 的规则"""

    @staticmethod
    def validate_volume_config(content: dict) -> List[ConstraintViolation]:
        """验证分卷配置：禁止整数章强迫症"""
        violations = []
        volumes = content.get("volumes", [])
        if not volumes:
            return violations

        for i, vol in enumerate(volumes):
            ch_range = vol.get("chapter_range", [])
            if len(ch_range) == 2:
                start, end = ch_range
                length = end - start + 1

                # 规则：分卷不以整数为边界，以叙事重力为边界
                if length % 10 == 0 and length > 0:
                    boundary = vol.get("boundary_gravity", [])
                    if not boundary or all(
                        b.get("type") != "narrative_gravity"
                        for b in (boundary if isinstance(boundary, list) else [])
                    ):
                        gravity_sources = vol.get("boundary_gravity", vol.get("gravity_sources", []))
                        has_gravity = bool(gravity_sources)
                        violations.append(ConstraintViolation(
                            rule="no_integer_chapter_obsession",
                            severity="warning" if has_gravity else "error",
                            message=f"第{i+1}卷「{vol.get('name', '')}」章节数正好是{length}章（整数），"
                                    f"{'但已提供重力来源' if has_gravity else '且未提供分卷重力来源'}",
                            suggestion="根据 章节细纲.md 1.1 节：分卷应以人物状态不可逆变化为边界，"
                                      "而非整数章节。请检查分卷边界是否对应弧线节点或冲突收束点。"
                        ))

        return violations

    @staticmethod
    def validate_chapter_distribution(content: dict) -> List[ConstraintViolation]:
        """验证章节分布合理性"""
        violations = []
        volumes = content.get("volumes", [])
        if not volumes:
            return violations

        total = sum(
            v.get("chapter_range", [0, 0])[1] - v.get("chapter_range", [0, 0])[0] + 1
            for v in volumes if len(v.get("chapter_range", [])) == 2
        )

        # 规则：20万字，600章 = 约333字/章 — 过短
        if total >= 500:
            avg_words = 200000 / total
            if avg_words < 500:
                violations.append(ConstraintViolation(
                    rule="chapter_word_count_too_low",
                    severity="warning",
                    message=f"共{total}章，每章平均约{avg_words:.0f}字，低于500字/章的建议下限",
                    suggestion="每章至少需要1500-3000字才能展开有效的叙事。建议减少章节数至100-200章，"
                              "或改为短篇集格式。长篇小说的每章字数通常在2000-5000字之间。"
                ))

        return violations

    @staticmethod
    def validate_chapter_content_duplicates(
        chapters: List[Dict[str, Any]]
    ) -> List[ConstraintViolation]:
        """检测章节内容重复"""
        violations = []
        seen_summaries = {}
        for i, ch in enumerate(chapters):
            # pyrefly: ignore [unsupported-operation]
            summary = ch.get("summary", ch.get("content", ""))[:100]
            if summary and len(summary) > 20:
                for prev_i, prev_summary in seen_summaries.items():
                    if summary == prev_summary:
                        violations.append(ConstraintViolation(
                            rule="no_duplicate_chapters",
                            severity="error",
                            message=f"第{ch.get('chapter_number', i+1)}章与第{prev_i+1}章内容完全相同",
                            suggestion="请重新生成差异化内容，确保每章推进情节或深化人物。"
                        ))
                seen_summaries[i] = summary
        return violations


# ============================================================
# 质量门禁
# ============================================================

class QualityGate:
    """质量门禁 — 强制质量审查流程"""

    @staticmethod
    def must_review(step_num: int) -> bool:
        """检查该步骤是否需要质量审查"""
        for s in STEP_DEFINITIONS:
            if s[0] == step_num:
                return s[3]
        return False

    @staticmethod
    def run_review(novel_id: str, step_num: int, db_session: Any) -> dict:
        """执行质量审查并返回结果"""
        from src.core.quality.orchestrator import QualityOrchestrator, ReviewContext

        # 构建审查上下文
        context = ReviewContext(
            novel_id=novel_id,
            step_name=f"step_{step_num:02d}",
        )

        # 执行审查
        orchestrator = QualityOrchestrator(db_session)
        result = orchestrator.review(context)

        return {
            "success": result.passed,
            "summary": f"质量评分: {result.score:.2f}, 通过: {result.passed}",
            "data": {"level": result.level.value if hasattr(result.level, "value") else str(result.level),
                    "score": result.score,
                    "details": result.details,
                    "suggestions": result.suggestions},
            "errors": result.details if not result.passed else [],
        }


# ============================================================
# 同步输出
# ============================================================

class SyncOutput:
    """同步引擎 — 生成 user_view/ 结构化 Markdown"""

    @staticmethod
    def sync(novel_id: str, step_name: str, db_session: Any) -> str:
        """同步当前步骤数据到 user_view/ 目录"""
        try:
            from src.config.settings import Config
            from src.core.sync.engine import SyncEngine
            engine = SyncEngine(db_session, Config.USER_VIEW_DIR, Config.SYSTEM_DATA_DIR)
            report = engine.sync_json_to_md(novel_id)
            return f"已同步 {report.files_updated} 个文件到 user_view/"
        except Exception as e:
            return f"同步警告: {e}"


# ============================================================
# 步骤执行结果
# ============================================================

@dataclass
class StepExecutionResult:
    step_num: int
    step_name: str
    module_name: str
    success: bool
    summary: str = ""
    module_data: Optional[Dict[str, Any]] = None
    review_result: Optional[Dict[str, Any]] = None
    constraint_violations: List[ConstraintViolation] = field(default_factory=list)
    sync_status: str = ""
    errors: List[str] = field(default_factory=list)


# ============================================================
# 单步执行器 — AI Agent 唯一允许的模块调用入口
# ============================================================

class StepExecutor:
    """单步执行器

    AI Agent 必须使用此执行器来执行每一步，不能自行编写脚本调用模块。
    每步执行流程：
        1. 依赖验证 — 检查前置步骤是否完成
        2. 约束验证 — 对特殊步骤执行约束检查
        3. 模块执行 — 调用对应模块的 run()
        4. 质量审查 — 对需要质检的步骤执行审查
        5. 同步输出 — 将结果同步到 user_view/
    """

    def __init__(self, novel_id: str, db_session: Any, chroma_client: Any):
        self.novel_id = novel_id
        self.db = db_session
        self.chroma = chroma_client

    def execute(
        self,
        step_num: int,
        content: dict,
        user_modifications: Optional[List[str]] = None,
    ) -> StepExecutionResult:
        """执行单个步骤并返回完整结果

        Args:
            step_num: 步骤编号 (1-20)
            content: AI Agent 根据用户需求生成的结构化内容
            user_modifications: 用户提供的修改建议（可选）

        Returns:
            StepExecutionResult: 包含所有执行信息的完整结果
        """
        # 查找步骤定义
        step_def = None
        for s in STEP_DEFINITIONS:
            if s[0] == step_num:
                step_def = s
                break
        if not step_def:
            return StepExecutionResult(
                step_num=step_num, step_name="未知", module_name="",
                success=False, errors=[f"步骤 {step_num} 不存在"],
            )

        _, step_name, module_name, needs_review, dep_steps = step_def
        result = StepExecutionResult(
            step_num=step_num, step_name=step_name,
            module_name=module_name, success=False,
        )

        # 1. 验证依赖
        dep_errors = self._validate_dependencies(step_num, dep_steps)
        if dep_errors:
            result.errors = dep_errors
            return result

        # 2. 约束验证
        violations = self._check_constraints(step_num, content)
        result.constraint_violations = violations
        errors = [v for v in violations if v.severity == "error"]
        if errors:
            result.errors = [f"[约束违规] {e.message} (建议: {e.suggestion})" for e in errors]
            return result

        # 3. 执行模块
        module_result = self._run_module(step_name, module_name, content, user_modifications)
        result.success = module_result.success
        result.summary = module_result.summary
        result.module_data = module_result.data
        if module_result.errors:
            result.errors.extend(module_result.errors)

        # 写 system_data JSON（确保同步引擎能正确读取）
        if module_result.success:
            self._save_system_data(module_name, module_result)

        # 4. 同步到 user_view/（无论模块执行成功与否，只要写了数据库就同步）
        result.sync_status = SyncOutput.sync(self.novel_id, step_name, self.db)

        if not module_result.success:
            return result

        # 5. 质量审查（如果需要）
        if needs_review:
            review = QualityGate.run_review(self.novel_id, step_num, self.db)
            result.review_result = review
            if not review["success"]:
                result.errors.append(f"[质量审查未通过] {review['summary']}")
            self._save_review_result(step_num, module_name, review)

        # 6. 更新小说进度
        self._update_progress(step_num)

        return result

    def _validate_dependencies(self, step_num: int, dep_steps: List[int]) -> List[str]:
        """验证依赖步骤是否已完成（以 step_status 为准）"""
        errors = []
        completed = set()
        try:
            rows = self.db.execute(
                text("SELECT step_number FROM step_status WHERE novel_id = :nid AND status = 'completed'"),
                {"nid": self.novel_id},
            ).fetchall()
            completed = {r[0] for r in rows}
            # 同步 novels.current_step（确保后续流程一致）
            if completed:
                max_step = max(completed)
                self.db.execute(
                    text("UPDATE novels SET current_step = :step, updated_at = :now WHERE id = :id AND current_step < :step"),
                    {"step": max_step, "now": datetime.now().isoformat(), "id": self.novel_id},
                )
        except Exception as e:
            pass

        for dep in dep_steps:
            if dep not in completed:
                dep_name = ""
                for s in STEP_DEFINITIONS:
                    if s[0] == dep:
                        dep_name = s[1]
                        break
                errors.append(
                    f"依赖步骤 {dep}「{dep_name}」尚未完成。"
                    f"请先完成前置步骤再继续。"
                )
        return errors

    def _check_constraints(self, step_num: int, content: dict) -> List[ConstraintViolation]:
        """检查步骤相关的约束"""
        violations = []

        if step_num == 13:  # 分卷配置
            violations.extend(ConstraintsEngine.validate_volume_config(content))
            violations.extend(ConstraintsEngine.validate_chapter_distribution(content))

        if step_num == 17:  # 正文初稿
            chapters = content.get("chapters", [])
            violations.extend(ConstraintsEngine.validate_chapter_content_duplicates(chapters))

        return violations

    def _run_module(
        self,
        step_name: str,
        module_name: str,
        content: dict,
        user_modifications: Optional[List[str]] = None,
    ) -> ModuleResult:
        """执行模块"""
        registry = get_registry()
        registry.initialize()
        cls = registry.get(module_name)
        if not cls:
            return ModuleResult(
                success=False,
                summary=f"模块 '{module_name}' 未注册",
                errors=[f"模块 '{module_name}' 未注册"],
            )

        module = cls()
        ctx = {
            "novel_id": self.novel_id,
            "db_session": self.db,
            "chroma_client": self.chroma,
            "dependencies": {},
            "user_modifications": user_modifications,
        }
        return module.run(ctx, content)

    MODULE_TO_SYSTEM_DATA = {
        "theme_engine": "01_主题",
        "world_builder": "02_世界观",
        "faction_builder": "03_势力",
        "faction_relation": "04_势力关系",
        "character_builder": "05_人物",
        "relation_builder": "06_人物关系",
        "arc_builder": "07_角色弧线",
        "item_builder": "08_物品仓库",
        "foreshadow_manager": "09_伏笔管理",
        "outline_builder": "10_大纲",
        "volume_config": "11_分卷",
        "detail_outline": "12_细纲",
        "manuscript_writer": "13_正文",
        "char_faction_bridge": "14_人物势力",
        "archive_builder": "15_档案",
        "synopsis_builder": "16_简介",
        "export_tool": "17_导出",
        "review_executor": "18_审核",
        "author_tool": "19_作者工具",
    }

    def _save_system_data(self, module_name: str, module_result: ModuleResult):
        """模块执行成功后，将数据写入 system_data JSON

        确保 sync 引擎的 `_load_module_data` 能从 JSON 读到最新数据，
        而不是回退到 DB 的原始列格式。
        """
        import json
        from pathlib import Path
        from src.config.settings import Config

        sys_module = self.MODULE_TO_SYSTEM_DATA.get(module_name)
        if not sys_module:
            return

        data = module_result.data
        records = None
        for key in ("characters", "factions", "items", "world_rules",
                     "foreshadows", "relations", "faction_relations",
                     "arcs", "chapters", "volumes", "records",
                     "acts", "causal_chain", "rhythm_map",
                     "scenes", "directions", "theme",
                     "synopsis", "dimensions"):
            records = data.get(key)
            if records is not None:
                break

        if records is None and isinstance(data, dict):
            records = [data]
        elif records is None:
            records = []

        json_path = Path(Config.SYSTEM_DATA_DIR) / self.novel_id / "modules" / f"{sys_module}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps({"records": records, "count": len(records)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _update_progress(self, step_num: int):
        """更新小说进度并记录步骤状态"""
        try:
            self.db.execute(
                text("UPDATE novels SET current_step = :step, updated_at = :now WHERE id = :id"),
                {"step": step_num, "now": datetime.now().isoformat(), "id": self.novel_id},
            )
            step_name = ""
            for s in STEP_DEFINITIONS:
                if s[0] == step_num:
                    step_name = s[1]
                    break
            self.db.execute(
                text("INSERT OR REPLACE INTO step_status (novel_id, step_number, step_name, status) VALUES (:nid, :step_no, :sname, 'completed')"),
                {"nid": self.novel_id, "step_no": step_num, "sname": step_name},
            )
            self.db.commit()
        except Exception:
            pass

    def _save_review_result(self, step_num: int, module_name: str, review: dict):
        """将质量审查结果持久化到 review_results 表"""
        try:
            data = review.get("data", {})
            details = data.get("details", [])
            suggestions = data.get("suggestions", [])
            self.db.execute(
                text("""
                    INSERT INTO review_results
                        (novel_id, step_number, module_name, level, score, details, suggestions, created_at)
                    VALUES
                        (:novel_id, :step_number, :module_name, :level, :score, :details, :suggestions, :created_at)
                """),
                {
                    "novel_id": self.novel_id,
                    "step_number": step_num,
                    "module_name": module_name,
                    "level": data.get("level", "info"),
                    "score": data.get("score", 1.0),
                    "details": json.dumps(details, ensure_ascii=False),
                    "suggestions": json.dumps(suggestions, ensure_ascii=False),
                    "created_at": datetime.now().isoformat(),
                },
            )
            self.db.commit()
        except Exception as e:
            pass


# ============================================================
# 辅助函数 — AI Agent 直接调用
# ============================================================

def get_step_info(step_num: int) -> dict:
    """获取步骤信息（名称、依赖、需要质检等）"""
    for s in STEP_DEFINITIONS:
        if s[0] == step_num:
            dep_names = []
            for d in s[4]:
                for ds in STEP_DEFINITIONS:
                    if ds[0] == d:
                        dep_names.append(ds[1])
                        break
            return {
                "step_num": step_num,
                "step_name": s[1],
                "module_name": s[2],
                "needs_review": s[3],
                "dependencies": dep_names,
                "total_steps": len(STEP_DEFINITIONS),
            }
    return {"step_num": step_num, "step_name": "未知", "error": "步骤不存在"}


def list_steps() -> List[dict]:
    """列出所有步骤"""
    return [
        {
            "step_num": s[0],
            "step_name": s[1],
            "module_name": s[2],
            "needs_review": s[3],
            "dependencies": [ds[1] for d in s[4] for ds in STEP_DEFINITIONS if ds[0] == d],
        }
        for s in STEP_DEFINITIONS
    ]


def get_expected_format(step_num: int) -> str:
    """获取指定步骤期望的 content 格式说明"""
    formats = {
        1:  "灵感启动: directions[] + theme{surface_theme, deep_theme, emotional_hook, theme_statement, reverse_confirmation}",
        2:  "小说主题: theme{} + sub_themes[]（每个含 name + core_question）",
        3:  "世界观设定: dimensions[]（name, rules[] 含 description, scope, constraints）",
        4:  "人物设定: characters[]（name, role, layer1-4, weight）",
        5:  "势力设定: factions[]（name, type, hierarchy, goals, resources, doctrines, reputation, members[]）",
        6:  "物品库: items[]（name, type, purpose, background_story, restrictions[], current_owner, significance_to_plot）",
        7:  "人物关系: relations[]（char_a_id, char_b_id, type, strength, asymmetry, history, trajectory）",
        8:  "势力关系: relations[]（faction_a_id, faction_b_id, type, strength, history[], treaties[], hidden_agenda）",
        9:  "人物-势力关联: links[]（char_id, faction_id, membership_type, join_chapter, role_in_faction, loyalty）",
        10: "角色弧线: arcs[]（char_id, arc_type, start_state, catalyst_event, change_process[], end_state, chapter_mapping[]）",
        11: "伏笔追踪: foreshadows[]（type, status, plant_chapter, payload, depth, importance）+ density_curve[]",
        12: "拟定大纲: acts[]（title, chapters, key_events, description）+ causal_chain[] + rhythm_map[]",
        13: "分卷配置: volumes[]（name, chapter_range[2], boundary_gravity[], pacing, major_conflict, character_focus[], themes, cliffhanger）",
        14: "章节细纲: chapters[]（chapter_number, pov_character, summary, scenes[]）",
        15: "小说档案: AI自动聚合所有前置模块数据",
        16: "小说简介: synopsis（one_liner, short_blurb, standard_blurb, long_blurb, selling_points, target_audience）",
        17: "正文初稿: chapters[]（chapter_number, title, scenes, word_count）",
        18: "正文审核: 自动执行（无需 content）",
        19: "正文修正: chapters[]（含修正标记）",
        20: "导出发布: 自动执行（无需 content）",
    }
    return formats.get(step_num, "自由格式 JSON")
