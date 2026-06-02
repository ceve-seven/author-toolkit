import json
from datetime import datetime, timezone

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class ThemeEngine(BaseModule):
    module_name = "theme_engine"
    depends_on = []

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        dependencies = context.get("dependencies", {})

        errors = []
        data = {}

        directions = content.get("directions", [])
        theme = content.get("theme", {})

        if directions:
            for direction in directions:
                direction_id = direction.get(
                    "id",
                    generate_id("DIR", novel_id, db),
                )
                db.execute(
                    text("""
                        INSERT OR REPLACE INTO inspirations
                        (novel_id, direction_id, title, concept, innovation_score,
                         summary, emotional_potential, created_at)
                        VALUES (:novel_id, :direction_id, :title, :concept,
                                :innovation_score, :summary, :emotional_potential, :created_at)
                    """),
                    {
                        "novel_id": novel_id,
                        "direction_id": direction_id,
                        "title": direction.get("title", ""),
                        "concept": direction.get("concept", ""),
                        "innovation_score": direction.get("innovation_score", 0.0),
                        "summary": direction.get("summary", ""),
                        "emotional_potential": direction.get("emotional_potential", 0.0),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            data["directions"] = directions

        if theme:
            db.execute(
                text("""
                    INSERT OR REPLACE INTO themes
                    (novel_id, surface_theme, deep_theme, emotional_hook,
                     theme_statement, reverse_confirmation)
                    VALUES (:novel_id, :surface_theme, :deep_theme, :emotional_hook,
                            :theme_statement, :reverse_confirmation)
                """),
                {
                    "novel_id": novel_id,
                    "surface_theme": theme.get("surface_theme", ""),
                    "deep_theme": theme.get("deep_theme", ""),
                    "emotional_hook": theme.get("emotional_hook", ""),
                    "theme_statement": theme.get("theme_statement", ""),
                    "reverse_confirmation": theme.get("reverse_confirmation", ""),
                },
            )
            data["theme"] = theme

        db.flush()

        summary_parts = []
        if directions:
            summary_parts.append(f"已生成 {len(directions)} 个灵感方向")
        if theme:
            summary_parts.append(f"主题：{theme.get('surface_theme', '')}")
        summary = " / ".join(summary_parts) if summary_parts else "ThemeEngine 执行完成"

        return ModuleResult(
            success=len(errors) == 0,
            summary=summary,
            data=data,
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data

        directions = data.get("directions", [])
        if directions:
            if len(directions) != 3:
                issues.append(f"灵感方向必须恰好 3 个，当前 {len(directions)} 个")
            for i, d in enumerate(directions):
                score = d.get("innovation_score", -1)
                if not (0.0 <= score <= 1.0):
                    issues.append(f"灵感方向 {i + 1} 的创新性评分 {score} 超出 0-1 范围")
                ep = d.get("emotional_potential", -1)
                if not (0.0 <= ep <= 1.0):
                    issues.append(f"灵感方向 {i + 1} 的情感潜力 {ep} 超出 0-1 范围")

        theme = data.get("theme", {})
        if theme:
            surface = theme.get("surface_theme", "")
            deep = theme.get("deep_theme", "")
            if len(surface) < 10:
                issues.append(f"表层主题字数不足 10 字（当前 {len(surface)} 字）")
            if len(deep) < 10:
                issues.append(f"深层主题字数不足 10 字（当前 {len(deep)} 字）")
            if surface == deep:
                issues.append("表层主题与深层主题不得相同")

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues