import json
import os

from sqlalchemy import text

from src.config.settings import Config
from src.core.modules.base_module import BaseModule, ModuleResult


class ExportTool(BaseModule):
    module_name = "export_tool"
    depends_on = ["archive_builder", "synopsis_builder", "manuscript_writer"]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        export_config = content.get("export", {})
        formats = export_config.get("formats", ["markdown", "txt"])
        include_review = export_config.get("include_review_report", False)
        include_foreshadow_map = export_config.get(
            "include_foreshadow_map", False
        )

        novel_row = db.execute(
            text("SELECT title FROM novels WHERE id = :id"), {"id": novel_id}
        ).fetchone()
        novel_title = novel_row[0] if novel_row else f"小说_{novel_id}"

        chapters_data = db.execute(
            text("SELECT chapter_number, title, scenes, word_count FROM manuscripts "
            "WHERE novel_id = :novel_id AND status != 'draft' "
            "ORDER BY chapter_number"),
            {"novel_id": novel_id},
        ).fetchall()

        exported_files = []

        user_view_dir = Config.get_user_view_path(novel_title)
        os.makedirs(user_view_dir, exist_ok=True)

        for fmt in formats:
            if fmt == "markdown":
                file_path = self._export_markdown(
                    user_view_dir, novel_title, novel_id,
                    chapters_data, db, include_review, include_foreshadow_map,
                )
            elif fmt == "txt":
                file_path = self._export_txt(
                    user_view_dir, novel_title, novel_id, chapters_data, db,
                )
            else:
                continue

            if file_path:
                total_wc = sum(
                    ch.get("word_count", 0)
                    for ch in (
                        ch if isinstance(ch, dict)
                        else {"word_count": ch.word_count}
                        for ch in chapters_data
                    )
                    if hasattr(ch, "word_count") or isinstance(ch, dict)
                )
                exported_files.append({
                    "format": fmt,
                    "path": file_path,
                    "word_count": total_wc,
                })

        export_meta = {
            "novel_id": novel_id,
            "novel_title": novel_title,
            "exported_at": __import__(
                "datetime"
            ).datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "formats": formats,
            "files": exported_files,
        }
        meta_path = os.path.join(user_view_dir, "导出配置.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(export_meta, f, ensure_ascii=False, indent=2)

        return ModuleResult(
            success=True,
            summary=f"已导出 {len(exported_files)} 个文件到 {user_view_dir}",
            data={"exported_files": exported_files},
            # pyrefly: ignore [no-matching-overload]
            word_count=sum(f.get("word_count", 0) for f in exported_files),
            errors=errors,
        )

    def _export_markdown(
        self, output_dir: str, novel_title: str, novel_id: str,
        chapters_data: list, db, include_review: bool,
        include_foreshadow_map: bool,
    ) -> str | None:
        file_path = os.path.join(output_dir, "📖 完整小说.md")
        total_wc = 0

        novel_info = db.execute(
            text("SELECT title, author FROM novels WHERE id = :id"),
            {"id": novel_id},
        ).fetchone()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {novel_title}\n\n")
            if novel_info and novel_info[1]:
                f.write(f"**作者**：{novel_info[1]}\n\n")

            synopsis = db.execute(
                text("SELECT standard_blurb, core_conflict, world_highlight, "
                "selling_points, tone_tags "
                "FROM synopses WHERE novel_id = :novel_id ORDER BY last_synced_at DESC LIMIT 1"),
                {"novel_id": novel_id},
            ).fetchone()
            if synopsis and synopsis[0]:
                f.write("## 简介\n\n")
                f.write(f"{synopsis[0]}\n\n")
                f.write("---\n\n")

            f.write("## 目录\n\n")
            for row in chapters_data:
                ch_num, ch_title, _, wc = row
                total_wc += wc or 0
                display_title = ch_title or f"第 {ch_num} 章"
                f.write(f"- [{display_title}](#第{ch_num}章-{display_title})\n")
            f.write("\n---\n\n")

            for row in chapters_data:
                ch_num, ch_title, scenes_json, wc = row
                display_title = ch_title or f"第 {ch_num} 章"
                f.write(f"## 第{ch_num}章 {display_title}\n\n")
                f.write(f"> 字数：{wc or 0}\n\n")

                scenes = []
                if scenes_json:
                    try:
                        scenes = json.loads(scenes_json) if isinstance(scenes_json, str) else scenes_json
                    except (json.JSONDecodeError, TypeError):
                        scenes = []

                for scene in scenes:
                    pov = scene.get("pov_char_id", "")
                    text_content = scene.get("text", "")
                    if pov:
                        f.write(f"*（{pov} 视角）*\n\n")
                    f.write(f"{text_content}\n\n")
                    f.write("---\n\n")

            if include_foreshadow_map:
                foreshadows = db.execute(
                    text("SELECT foreshadow_id, type, status, plant_chapter, "
                    "reveal_chapter_planned, payload, surface "
                    "FROM foreshadows WHERE novel_id = :novel_id "
                    "ORDER BY plant_chapter"),
                    {"novel_id": novel_id},
                ).fetchall()
                if foreshadows:
                    f.write("\n## 伏笔图\n\n")
                    f.write("| ID | 类型 | 状态 | 埋设章 | 计划回收章 | 表层 | 真相 |\n")
                    f.write("|----|------|------|--------|-----------|------|------|\n")
                    for fore in foreshadows:
                        f.write(
                            f"| {fore[0]} | {fore[1]} | {fore[2]} | "
                            f"{fore[3]} | {fore[4]} | {fore[6]} | {fore[5]} |\n"
                        )

        return file_path

    def _export_txt(
        self, output_dir: str, novel_title: str, novel_id: str,
        chapters_data: list, db,
    ) -> str | None:
        file_path = os.path.join(output_dir, "📖 完整小说.txt")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"{novel_title}\n")
            f.write("=" * 40 + "\n\n")

            for row in chapters_data:
                ch_num, ch_title, scenes_json, wc = row
                display_title = ch_title or f"第 {ch_num} 章"
                f.write(f"======== 第{ch_num}章 {display_title} ========\n\n")

                scenes = []
                if scenes_json:
                    try:
                        scenes = json.loads(scenes_json) if isinstance(scenes_json, str) else scenes_json
                    except (json.JSONDecodeError, TypeError):
                        scenes = []

                for scene in scenes:
                    text_content = scene.get("text", "")
                    f.write(f"{text_content}\n\n")

                f.write("\n")

        return file_path

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        exported_files = data.get("exported_files", [])

        if not exported_files:
            issues.append("导出文件列表为空")

        for ef in exported_files:
            file_path = ef.get("path", "")
            if not os.path.exists(file_path):
                issues.append(f"导出文件不存在：{file_path}")

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    f.read()
            except UnicodeDecodeError:
                issues.append(f"文件编码不是 UTF-8：{file_path}")

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues