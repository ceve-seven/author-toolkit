import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class FactionRelationBuilder(BaseModule):
    module_name = "faction_relation"
    depends_on = ["world_builder", "faction_builder"]

    VALID_TYPES = {"alliance", "hostile", "neutral", "subordinate", "puppet"}

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        relations = content.get("relations", [])

        for rel in relations:
            relation_id = rel.get("id", generate_id("FREL", novel_id, db))
            db.execute(
                text("""
                    INSERT OR REPLACE INTO faction_relations
                    (novel_id, relation_id, faction_a_id, faction_b_id, type,
                     strength, history, treaties, hidden_agenda)
                    VALUES (:novel_id, :relation_id, :faction_a_id, :faction_b_id, :type,
                            :strength, :history, :treaties, :hidden_agenda)
                """),
                {
                    "novel_id": novel_id,
                    "relation_id": relation_id,
                    "faction_a_id": rel.get("faction_a_id", ""),
                    "faction_b_id": rel.get("faction_b_id", ""),
                    "type": rel.get("type", ""),
                    "strength": rel.get("strength", 0.0),
                    "history": json.dumps(rel.get("history", []), ensure_ascii=False),
                    "treaties": json.dumps(
                        rel.get("treaties", []), ensure_ascii=False
                    ),
                    "hidden_agenda": rel.get("hidden_agenda", ""),
                },
            )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(relations)} 条势力关系",
            data={"relations": relations},
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        relations = data.get("relations", [])

        dependencies = result.data.get("_dependencies", {})
        factions = dependencies.get("faction_builder", {}).get("factions", [])
        faction_ids = {f.get("id") for f in factions}

        faction_relation_count: dict[str, int] = {}

        for rel in relations:
            fa = rel.get("faction_a_id", "")
            fb = rel.get("faction_b_id", "")

            if fa not in faction_ids:
                issues.append(f"faction_a_id「{fa}」在 factions 表中不存在")
            if fb not in faction_ids:
                issues.append(f"faction_b_id「{fb}」在 factions 表中不存在")

            faction_relation_count[fa] = faction_relation_count.get(fa, 0) + 1
            faction_relation_count[fb] = faction_relation_count.get(fb, 0) + 1

            strength = rel.get("strength", -1)
            if not (0.0 <= strength <= 1.0):
                issues.append(f"关系强度 {strength} 超出 0-1 范围")

            rel_type = rel.get("type", "")
            if rel_type == "alliance" and strength < 0.5:
                issues.append(
                    f"联盟关系（{fa} - {fb}）强度应 > 0.5，当前 {strength}"
                )
            if rel_type == "hostile" and strength < 0.5:
                issues.append(
                    f"敌对关系（{fa} - {fb}）强度应 > 0.5，当前 {strength}"
                )

        for fid in faction_ids:
            if faction_relation_count.get(fid, 0) < 1:
                issues.append(f"势力 {fid} 至少与 1 个其他势力有关系")

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues