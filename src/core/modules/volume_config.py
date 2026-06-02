import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class VolumeConfig(BaseModule):
    module_name = "volume_config"
    depends_on = ["outline_builder", "character_builder", "arc_builder"]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        volumes = content.get("volumes", [])

        for vol in volumes:
            volume_id = vol.get("id", generate_id("VOL", novel_id, db))

            db.execute(
                text("""
                    INSERT OR REPLACE INTO volumes
                    (novel_id, volume_id, name, chapter_range,
                     boundary_gravity, pacing, major_conflict,
                     character_focus, themes, cliffhanger,
                     volume_rhythm_curve, volume_rhythm_evaluation)
                    VALUES (:novel_id, :volume_id, :name, :chapter_range,
                            :boundary_gravity, :pacing, :major_conflict,
                            :character_focus, :themes, :cliffhanger,
                            :volume_rhythm_curve, :volume_rhythm_evaluation)
                """),
                {
                    "novel_id": novel_id,
                    "volume_id": volume_id,
                    "name": vol.get("name", ""),
                    "chapter_range": json.dumps(
                        vol.get("chapter_range", []), ensure_ascii=False
                    ),
                    "boundary_gravity": json.dumps(
                        vol.get("boundary_gravity", []), ensure_ascii=False
                    ),
                    "pacing": vol.get("pacing", "medium"),
                    "major_conflict": vol.get("major_conflict", ""),
                    "character_focus": json.dumps(
                        vol.get("character_focus", []), ensure_ascii=False
                    ),
                    "themes": json.dumps(
                        vol.get("themes", []), ensure_ascii=False
                    ),
                    "cliffhanger": vol.get("cliffhanger", ""),
                    "volume_rhythm_curve": json.dumps(
                        vol.get("volume_rhythm_curve", []), ensure_ascii=False
                    ),
                    "volume_rhythm_evaluation": vol.get(
                        "volume_rhythm_evaluation", ""
                    ),
                },
            )

            chapters = vol.get("chapters", [])
            for ch in chapters:
                db.execute(
                    text("""
                        INSERT OR REPLACE INTO volume_chapters
                        (novel_id, volume_id, chapter_number, pov_character,
                         summary, word_count_budget)
                        VALUES (:novel_id, :volume_id, :chapter_number, :pov_character,
                                :summary, :word_count_budget)
                    """),
                    {
                        "novel_id": novel_id,
                        "volume_id": volume_id,
                        "chapter_number": ch.get("chapter_number", 0),
                        "pov_character": ch.get("pov_character", ""),
                        "summary": ch.get("summary", ""),
                        "word_count_budget": ch.get("word_count_budget", 0),
                    },
                )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(volumes)} 卷配置",
            data={
                "volumes": volumes,
                "boundary_candidates": content.get("boundary_candidates", []),
                "rhythm_reports": content.get("rhythm_reports", []),
            },
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        volumes = data.get("volumes", [])

        dependencies = result.data.get("_dependencies", {})
        outline = dependencies.get("outline_builder", {})
        acts = outline.get("acts", [])
        total_chapters_planned = sum(a.get("chapters", 0) for a in acts)

        total_volume_chapters = 0
        for vol in volumes:
            chapters = vol.get("chapters", [])
            total_volume_chapters += len(chapters)

            if len(chapters) < 3:
                issues.append(
                    f"卷「{vol.get('name', '')}」至少 3 章，当前 {len(chapters)} 章"
                )

            for ch in chapters:
                if not ch.get("pov_character"):
                    issues.append(
                        f"卷「{vol.get('name', '')}」第 {ch.get('chapter_number', '?')} 章未指定 POV 角色"
                    )

            if not vol.get("cliffhanger"):
                issues.append(f"卷「{vol.get('name', '')}」缺少卷末悬念（cliffhanger）")

        if total_chapters_planned > 0 and total_volume_chapters != total_chapters_planned:
            issues.append(
                f"各卷章节数合计（{total_volume_chapters}）与大纲总章节数（{total_chapters_planned}）不一致"
            )

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues