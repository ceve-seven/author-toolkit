import json
from datetime import datetime, timezone

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult


class SynopsisBuilder(BaseModule):
    module_name = "synopsis_builder"
    depends_on = ["archive_builder"]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        synopsis = content.get("synopsis", {})

        one_liner_text = synopsis.get("one_liner", {}).get("text", "")
        short_blurb_text = synopsis.get("short_blurb", {}).get("text", "")
        standard_blurb_text = synopsis.get("standard_blurb", {}).get("text", "")
        long_blurb_text = synopsis.get("long_blurb", {}).get("text", "")

        total_word_count = len(one_liner_text + short_blurb_text + standard_blurb_text + long_blurb_text)

        db.execute(
            text("""
                INSERT OR REPLACE INTO synopses
                (novel_id, one_liner, short_blurb, standard_blurb, long_blurb,
                 core_conflict, world_highlight, selling_points,
                 target_audience, tone_tags, comparison_titles,
                 hook_question, word_count, last_synced_at, stale_status)
                VALUES (:novel_id, :one_liner, :short_blurb, :standard_blurb, :long_blurb,
                        :core_conflict, :world_highlight, :selling_points,
                        :target_audience, :tone_tags, :comparison_titles,
                        :hook_question, :word_count, :last_synced_at, :stale_status)
            """),
            {
                "novel_id": novel_id,
                "one_liner": one_liner_text,
                "short_blurb": short_blurb_text,
                "standard_blurb": standard_blurb_text,
                "long_blurb": long_blurb_text,
                "core_conflict": synopsis.get("core_conflict", ""),
                "world_highlight": synopsis.get("world_highlight", ""),
                "selling_points": json.dumps(
                    synopsis.get("selling_points", []), ensure_ascii=False
                ),
                "target_audience": synopsis.get("target_audience", ""),
                "tone_tags": json.dumps(
                    synopsis.get("tone_tags", []), ensure_ascii=False
                ),
                "comparison_titles": json.dumps(
                    synopsis.get("comparison_titles", []), ensure_ascii=False
                ),
                "hook_question": synopsis.get("hook_question", ""),
                "word_count": total_word_count,
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
                "stale_status": "up_to_date",
            },
        )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"四版本简介已生成（共 {total_word_count} 字）",
            data={"synopsis": synopsis, "word_count": total_word_count},
            word_count=total_word_count,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        synopsis = data.get("synopsis", {})

        one_liner = synopsis.get("one_liner", {}).get("text", "")
        short_blurb = synopsis.get("short_blurb", {}).get("text", "")
        standard_blurb = synopsis.get("standard_blurb", {}).get("text", "")
        long_blurb = synopsis.get("long_blurb", {}).get("text", "")

        one_liner_len = len(one_liner)
        if one_liner_len < 30 or one_liner_len > 50:
            issues.append(
                f"one_liner 长度应在 30-50 字之间，当前 {one_liner_len} 字"
            )

        short_len = len(short_blurb)
        if short_len < 150 or short_len > 250:
            issues.append(
                f"short_blurb 长度应在 150-250 字之间，当前 {short_len} 字"
            )

        standard_len = len(standard_blurb)
        if standard_len < 300 or standard_len > 500:
            issues.append(
                f"standard_blurb 长度应在 300-500 字之间，当前 {standard_len} 字"
            )

        long_len = len(long_blurb)
        if long_len < 800 or long_len > 1500:
            issues.append(
                f"long_blurb 长度应在 800-1500 字之间，当前 {long_len} 字"
            )

        selling_points = synopsis.get("selling_points", [])
        if len(selling_points) < 3:
            issues.append(
                f"selling_points 至少 3 个，当前 {len(selling_points)} 个"
            )
        else:
            dimensions_covered = {sp.get("dimension", "") for sp in selling_points}
            for dim in ["plot", "character", "world"]:
                if dim not in dimensions_covered:
                    issues.append(f"selling_points 缺少 {dim} 维度")

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues