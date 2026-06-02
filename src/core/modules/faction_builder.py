import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class FactionBuilder(BaseModule):
    module_name = "faction_builder"
    depends_on = ["world_builder"]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        factions = content.get("factions", [])

        for faction in factions:
            faction_id = faction.get("id", generate_id("FAC", novel_id, db))

            db.execute(
                text("""
                    INSERT OR REPLACE INTO factions
                    (novel_id, faction_id, name, type,
                     hierarchy, goals, resources, doctrines, reputation)
                    VALUES (:novel_id, :faction_id, :name, :type,
                            :hierarchy, :goals, :resources, :doctrines, :reputation)
                """),
                {
                    "novel_id": novel_id,
                    "faction_id": faction_id,
                    "name": faction.get("name", ""),
                    "type": faction.get("type", ""),
                    "hierarchy": json.dumps(
                        faction.get("hierarchy", []), ensure_ascii=False
                    ),
                    "goals": json.dumps(
                        faction.get("goals", []), ensure_ascii=False
                    ),
                    "resources": json.dumps(
                        faction.get("resources", []), ensure_ascii=False
                    ),
                    "doctrines": json.dumps(
                        faction.get("doctrines", []), ensure_ascii=False
                    ),
                    "reputation": faction.get("reputation", 0.5),
                },
            )

            members = faction.get("members", [])
            for member in members:
                db.execute(
                    text("""
                        INSERT OR REPLACE INTO faction_members
                        (novel_id, faction_id, char_id, role, rank)
                        VALUES (:novel_id, :faction_id, :char_id, :role, :rank)
                    """),
                    {
                        "novel_id": novel_id,
                        "faction_id": faction_id,
                        "char_id": member.get("char_id", ""),
                        "role": member.get("role", ""),
                        "rank": member.get("rank", ""),
                    },
                )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(factions)} 个势力",
            data={"factions": factions},
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        factions = data.get("factions", [])

        if len(factions) < 2:
            issues.append(f"至少需要 2 个势力，当前 {len(factions)} 个")

        for faction in factions:
            hierarchy = faction.get("hierarchy", [])
            if len(hierarchy) < 2:
                issues.append(
                    f"势力「{faction.get('name', '')}」至少 2 个层级，当前 {len(hierarchy)} 个"
                )

            goals = faction.get("goals", [])
            if len(goals) < 1:
                issues.append(
                    f"势力「{faction.get('name', '')}」至少 1 个目标"
                )

            reputation = faction.get("reputation", -1)
            if reputation != -1 and not (0.0 <= reputation <= 1.0):
                issues.append(
                    f"势力「{faction.get('name', '')}」声誉值 {reputation} 超出 0-1 范围"
                )

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues