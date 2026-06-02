from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text

from src.core.sync.json_to_md import JsonToMdRenderer
from src.core.sync.md_to_json import MdToJsonParser
from src.core.sync.conflict_resolver import ConflictResolver
from src.utils import validate_table_name


@dataclass
class SyncReport:
    """同步报告"""
    direction: str
    """同步方向: json_to_md / md_to_json"""
    files_updated: int = 0
    """更新的文件数"""
    changes: List[Dict[str, Any]] = field(default_factory=list)
    """变更列表"""
    errors: List[str] = field(default_factory=list)
    """错误列表"""
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    """冲突列表"""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class SyncEngine:
    """双向同步引擎

    Agent 直接调用两个函数：
    - sync_json_to_md(novel_id): 将系统 JSON 数据渲染为用户可读的 Markdown
    - sync_md_to_json(novel_id): 将用户修改的 Markdown 解析回系统 JSON
    """

    MODULE_ORDER = [
        "01_主题",
        "02_世界观",
        "03_势力",
        "04_势力关系",
        "05_人物",
        "06_人物关系",
        "07_角色弧线",
        "08_物品仓库",
        "09_伏笔管理",
        "10_大纲",
        "11_分卷",
        "12_细纲",
        "13_正文",
    ]

    def __init__(self, db_session: Any, user_view_dir: str, system_data_dir: str):
        self.db = db_session
        self.user_view_dir = Path(user_view_dir)
        self.system_data_dir = Path(system_data_dir)
        self.renderer = JsonToMdRenderer()
        self.parser = MdToJsonParser()
        self.conflict_resolver = ConflictResolver()
        self.logger = structlog.get_logger("sync")

    def sync_json_to_md(self, novel_id: str) -> SyncReport:
        """方向: 系统 JSON → 用户 Markdown

        场景: Agent 修改数据后，更新用户可视层

        Args:
            novel_id: 小说 ID

        Returns:
            同步报告
        """
        self.logger.info("sync_json_to_md_start", novel_id=novel_id)

        novel = self._load_novel(novel_id)
        novel_dir = self.user_view_dir / novel.title
        novel_dir.mkdir(parents=True, exist_ok=True)

        files_updated = 0
        errors: List[str] = []

        for module_name in self.MODULE_ORDER:
            try:
                module_dir = novel_dir / module_name.replace("_", " ")
                module_dir.mkdir(parents=True, exist_ok=True)

                data = self._load_module_data(novel_id, module_name)

                if module_name == "13_正文":
                    files_updated += self._sync_manuscript(module_dir, data, novel, novel_id)
                else:
                    md_content = self.renderer.render(module_name, data, novel)
                    md_path = module_dir / f"{module_name}.md"

                    if self._has_changed(md_path, md_content):
                        md_path.write_text(md_content, encoding="utf-8")
                        files_updated += 1

            except Exception as e:
                error_msg = f"模块 {module_name} 同步失败: {e}"
                self.logger.warning("module_sync_error", module=module_name, error=str(e))
                errors.append(error_msg)

        self._render_review_report(novel_id, novel_dir)
        self._render_overview(novel_id, novel_dir)

        report = SyncReport(
            direction="json_to_md",
            files_updated=files_updated,
            errors=errors,
            timestamp=datetime.now().isoformat(),
        )

        self.logger.info(
            "sync_json_to_md_end",
            novel_id=novel_id,
            files_updated=files_updated,
            errors=len(errors),
        )
        return report

    def _sync_manuscript(self, module_dir: Path, data: Dict[str, Any], novel: Any, novel_id: str) -> int:
        """同步正文模块：按分卷组织，每个章节输出为独立 .md 文件"""
        files_updated = 0
        records = data.get("records", [])
        if not records:
            return 0

        volume_map = self._build_volume_map(novel_id)

        for rec in records:
            try:
                chapter_num = rec.get("chapter_number", "?")
                chapter_title = rec.get("title", f"第{chapter_num}章")
                scenes_raw = rec.get("text", rec.get("content", rec.get("scenes", "")))
                scenes = self.renderer.parse_scenes(scenes_raw)

                vol_info = volume_map.get(chapter_num)
                if vol_info:
                    vol_dir_name = f"卷{vol_info['vol_seq']}-{vol_info['vol_name']}"
                else:
                    vol_dir_name = "未归类"

                vol_dir = module_dir / vol_dir_name
                vol_dir.mkdir(parents=True, exist_ok=True)

                md_lines = [f"# 第 {chapter_num} 章  {chapter_title}", ""]
                if scenes:
                    for i, scene in enumerate(scenes):
                        content = scene.get("content", "") if isinstance(scene, dict) else str(scene)
                        if content:
                            md_lines.append(content)
                            if i < len(scenes) - 1:
                                md_lines.extend(["", "* * *", ""])

                chapter_number_str = f"{chapter_num:03d}" if isinstance(chapter_num, int) else str(chapter_num)
                filename = f"第{chapter_number_str}章_{chapter_title}.md"
                md_path = vol_dir / filename

                if self._has_changed(md_path, "\n".join(md_lines)):
                    md_path.write_text("\n".join(md_lines), encoding="utf-8")
                    files_updated += 1
            except Exception as e:
                self.logger.warning("chapter_sync_error", chapter=rec.get("chapter_number"), error=str(e))
        return files_updated

    def _build_volume_map(self, novel_id: str) -> Dict[int, Dict[str, Any]]:
        """构建章节号 → 分卷信息的映射"""
        volume_map = {}
        try:
            from sqlalchemy import text
            import json
            rows = self.db.execute(
                text("SELECT volume_id, name, chapter_range FROM volumes WHERE novel_id = :novel_id ORDER BY volume_id"),
                {"novel_id": novel_id},
            ).fetchall()
            for seq, (vol_id, vol_name, chapter_range_raw) in enumerate(rows, 1):
                try:
                    cr = json.loads(chapter_range_raw)
                    start, end = cr[0], cr[1]
                    for ch in range(start, end + 1):
                        volume_map[ch] = {"vol_seq": seq, "vol_name": vol_name, "vol_id": vol_id}
                except (json.JSONDecodeError, IndexError, TypeError):
                    pass
        except Exception as e:
            self.logger.warning("build_volume_map_error", error=str(e))
        return volume_map

    def sync_md_to_json(self, novel_id: str) -> SyncReport:
        """方向: 用户 Markdown → 系统 JSON

        场景: 用户手动编辑了 Markdown 文件后，同步回系统

        Args:
            novel_id: 小说 ID

        Returns:
            同步报告
        """
        self.logger.info("sync_md_to_json_start", novel_id=novel_id)

        novel = self._load_novel(novel_id)
        novel_dir = self.user_view_dir / novel.title

        if not novel_dir.exists():
            return SyncReport(
                direction="md_to_json",
                files_updated=0,
                errors=["目录不存在"],
                timestamp=datetime.now().isoformat(),
            )

        changes: List[Dict[str, Any]] = []
        errors: List[str] = []

        for module_dir in sorted(novel_dir.iterdir()):
            if not module_dir.is_dir():
                continue
            for md_file in module_dir.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    parsed = self.parser.parse(content, module_dir.name)
                    if parsed:
                        changes.extend(parsed)
                except Exception as e:
                    error_msg = f"解析 {md_file} 失败: {e}"
                    self.logger.warning("parse_md_error", file=str(md_file), error=str(e))
                    errors.append(error_msg)

        applied = self._apply_changes(novel_id, changes)

        self.logger.info(
            "sync_md_to_json_end",
            novel_id=novel_id,
            changes_found=len(changes),
            changes_applied=len(applied),
        )

        return SyncReport(
            direction="md_to_json",
            files_updated=len(applied),
            changes=applied,
            errors=errors,
            timestamp=datetime.now().isoformat(),
        )

    def _load_novel(self, novel_id: str) -> Any:
        """从数据库加载小说信息"""
        class NovelInfo:
            def __init__(self, row):
                self.id = row[0] if row else novel_id
                self.title = row[1] if row else novel_id

        try:
            row = self.db.execute(
                text("SELECT id, title FROM novels WHERE id = :novel_id"),
                {"novel_id": novel_id},
            ).fetchone()
            return NovelInfo(row)
        except Exception:
            return NovelInfo(None)

    def _load_module_data(self, novel_id: str, module_name: str) -> Dict[str, Any]:
        """从系统数据层加载模块数据"""
        try:
            data_path = self.system_data_dir / novel_id / "modules" / f"{module_name}.json"
            if data_path.exists():
                import json
                with open(data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

        try:
            table = self._module_to_table(module_name)
            if table:
                if module_name == "05_人物":
                    result = self.db.execute(
                        text("""
                            SELECT c.*, f.name AS faction_name
                            FROM characters c
                            LEFT JOIN char_faction_links cfl ON c.novel_id = cfl.novel_id AND c.char_id = cfl.char_id
                            LEFT JOIN factions f ON cfl.novel_id = f.novel_id AND cfl.faction_id = f.faction_id
                            WHERE c.novel_id = :novel_id
                        """),
                        {"novel_id": novel_id},
                    )
                elif module_name == "07_角色弧线":
                    result = self.db.execute(
                        text("""
                            SELECT ca.*, c.name AS character_name
                            FROM character_arcs ca
                            LEFT JOIN characters c ON ca.novel_id = c.novel_id AND ca.char_id = c.char_id
                            WHERE ca.novel_id = :novel_id
                        """),
                        {"novel_id": novel_id},
                    )
                else:
                    id_column = "id" if table == "novels" else "novel_id"
                    result = self.db.execute(
                        text(f"SELECT * FROM {validate_table_name(table)} WHERE {id_column} = :novel_id"),
                        {"novel_id": novel_id},
                    )
                rows = result.fetchall()
                if rows:
                    columns = result.keys()
                    records = [dict(zip(columns, row)) for row in rows]
                    return {"records": records, "count": len(records)}
        except Exception as e:
            self.logger.warning("load_module_data_error", module=module_name, error=str(e))

        return {}

    def _module_to_table(self, module_name: str) -> Optional[str]:
        """模块名到数据库表名的映射"""
        mapping = {
            "01_主题": "themes",
            "02_世界观": "world_rules",
            "03_势力": "factions",
            "04_势力关系": "faction_relations",
            "05_人物": "characters",
            "06_人物关系": "relations",
            "07_角色弧线": "character_arcs",
            "08_物品仓库": "items",
            "09_伏笔管理": "foreshadows",
            "10_大纲": "outlines",
            "11_分卷": "volumes",
            "12_细纲": "detail_outlines",
            "13_正文": "manuscripts",
        }
        return mapping.get(module_name)

    def _has_changed(self, path: Path, new_content: str) -> bool:
        """检查文件内容是否发生了变化"""
        if not path.exists():
            return True
        try:
            old_content = path.read_text(encoding="utf-8")
            return old_content != new_content
        except Exception:
            return True

    def _render_review_report(self, novel_id: str, novel_dir: Path):
        """渲染审查报告到 Markdown"""
        try:
            review_dir = novel_dir / "审查报告"
            review_dir.mkdir(parents=True, exist_ok=True)

            report_path = review_dir / "质量审查报告.md"
            content = self._build_review_report_content(novel_id)
            report_path.write_text(content, encoding="utf-8")

            ai_report_path = review_dir / "AI痕迹清除报告.md"
            ai_content = self._build_ai_clean_report(novel_id)
            ai_report_path.write_text(ai_content, encoding="utf-8")

        except Exception as e:
            self.logger.warning("render_review_report_error", error=str(e))

    def _render_overview(self, novel_id: str, novel_dir: Path):
        """渲染小说概览"""
        try:
            overview_path = novel_dir / "小说概览.md"
            content = self._build_overview_content(novel_id)
            overview_path.write_text(content, encoding="utf-8")
        except Exception as e:
            self.logger.warning("render_overview_error", error=str(e))

    def _build_review_report_content(self, novel_id: str) -> str:
        """构建审查报告内容"""
        lines = [
            "# 质量审查报告",
            "",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 审查摘要",
            "",
            "| 审查项 | 状态 | 评分 |",
            "|--------|------|------|",
        ]
        try:
            rows = self.db.execute(
                text("SELECT module, level, score, checked_at FROM review_results WHERE novel_id = :novel_id ORDER BY checked_at DESC LIMIT 10"),
                {"novel_id": novel_id},
            ).fetchall()
            for row in rows:
                module, level, score, checked_at = row
                level_icon = {"blocker": "⛔", "critical": "⚠", "warning": "⚡", "info": "✓"}
                icon = level_icon.get(level, "•")
                lines.append(f"| {module} | {icon} {level.upper()} | {score:.2f} | {checked_at} |")
        except Exception:
            lines.append("| - | - | - |")

        lines.append("")
        return "\n".join(lines)

    def _build_ai_clean_report(self, novel_id: str) -> str:
        """构建 AI 痕迹清除报告"""
        lines = [
            "# AI 痕迹清除报告",
            "",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 清除记录",
            "",
            "| 时间 | 处理文本 | 发现问题 | 自动修复 |",
            "|------|----------|----------|----------|",
        ]
        try:
            rows = self.db.execute(
                text("SELECT processed_at, text_length, issues_found, auto_fixed FROM purification_logs WHERE novel_id = :novel_id ORDER BY processed_at DESC LIMIT 10"),
                {"novel_id": novel_id},
            ).fetchall()
            for row in rows:
                lines.append(f"| {row[0]} | {row[1]} 字 | {row[2]} 处 | {row[3]} 处 |")
        except Exception:
            lines.append("| - | - | - | - |")

        lines.append("")
        return "\n".join(lines)

    def _build_overview_content(self, novel_id: str) -> str:
        """构建小说概览"""
        lines = [
            "# 小说概览",
            "",
            f"> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        try:
            row = self.db.execute(
                text("SELECT id, title, current_step, created_at FROM novels WHERE id = :novel_id"),
                {"novel_id": novel_id},
            ).fetchone()
            if row:
                lines.extend([
                    f"- **小说 ID**: {row[0]}",
                    f"- **标题**: {row[1]}",
                    f"- **当前进度**: 环节 {row[2]}/20",
                    f"- **创建时间**: {row[3]}",
                    "",
                ])
        except Exception:
            pass

        try:
            chapter_count = self.db.execute(
                text("SELECT COUNT(1) FROM manuscripts WHERE novel_id = :novel_id"),
                {"novel_id": novel_id},
            ).fetchone()
            char_count = self.db.execute(
                text("SELECT COUNT(1) FROM characters WHERE novel_id = :novel_id"),
                {"novel_id": novel_id},
            ).fetchone()
            lines.extend([
                "## 数据统计",
                "",
                f"- **章节数**: {chapter_count[0] if chapter_count else 0}",
                f"- **角色数**: {char_count[0] if char_count else 0}",
                "",
            ])
        except Exception:
            pass

        return "\n".join(lines)

    def _apply_changes(
        self,
        novel_id: str,
        changes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """应用 Markdown 解析后的变更到数据库"""
        applied: List[Dict[str, Any]] = []

        for change in changes:
            try:
                entity_id = change.get("entity_id")
                field_path = change.get("field_path", "")
                new_value = change.get("new_value")
                module = change.get("module", "")

                table = self._module_to_table(module)
                if not table or not entity_id or not field_path:
                    continue

                table_ok = validate_table_name(table)
                existing = self.db.execute(
                    text(f"SELECT * FROM {table_ok} WHERE id = :id AND novel_id = :novel_id"),
                    {"id": entity_id, "novel_id": novel_id},
                ).fetchone()
                if existing:
                    conflict = self.conflict_resolver.resolve(
                        old_value=existing,
                        new_value={field_path: new_value},
                        entity_id=entity_id,
                        md_timestamp=change.get("timestamp", ""),
                    )
                    if conflict.get("strategy") == "use_new":
                        self.db.execute(
                            text(f"UPDATE {table_ok} SET {field_path} = :new_value WHERE id = :id AND novel_id = :novel_id"),
                            {"new_value": new_value, "id": entity_id, "novel_id": novel_id},
                        )
                        applied.append(change)
                else:
                    applied.append(change)

            except Exception as e:
                self.logger.warning("apply_change_error", change=change, error=str(e))

        if applied:
            try:
                self.db.commit()
            except Exception:
                pass

        return applied