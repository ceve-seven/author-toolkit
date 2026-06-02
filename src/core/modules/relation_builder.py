import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class RelationBuilder(BaseModule):
    module_name = "relation_builder"
    depends_on = ["world_builder", "character_builder"]

    VALID_TYPES = {
        "family", "romance", "friendship", "rivalry",
        "mentorship", "enmity", "alliance", "master_servant", "neutral",
    }

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        relations = content.get("relations", [])

        for rel in relations:
            relation_id = rel.get("id", generate_id("REL", novel_id, db))
            db.execute(
                text("""
                    INSERT OR REPLACE INTO relations
                    (novel_id, relation_id, char_a_id, char_b_id, type,
                     strength, asymmetry, history, trajectory)
                    VALUES (:novel_id, :relation_id, :char_a_id, :char_b_id, :type,
                            :strength, :asymmetry, :history, :trajectory)
                """),
                {
                    "novel_id": novel_id,
                    "relation_id": relation_id,
                    "char_a_id": rel.get("char_a_id", ""),
                    "char_b_id": rel.get("char_b_id", ""),
                    "type": rel.get("type", ""),
                    "strength": rel.get("strength", 0.0),
                    "asymmetry": rel.get("asymmetry", 0.0),
                    "history": json.dumps(rel.get("history", []), ensure_ascii=False),
                    "trajectory": json.dumps(
                        rel.get("trajectory", []), ensure_ascii=False
                    ),
                },
            )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(relations)} 条人物关系",
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
        characters = dependencies.get("character_builder", {}).get("characters", [])

        char_ids = {c.get("id") for c in characters}
        protagonist_ids = {
            c.get("id") for c in characters if c.get("role") == "主角"
        }

        for rel in relations:
            if rel.get("char_a_id") not in char_ids:
                issues.append(
                    f"char_a_id「{rel.get('char_a_id')}」在 characters 表中不存在"
                )
            if rel.get("char_b_id") not in char_ids:
                issues.append(
                    f"char_b_id「{rel.get('char_b_id')}」在 characters 表中不存在"
                )

            strength = rel.get("strength", -1)
            if not (0.0 <= strength <= 1.0):
                issues.append(
                    f"关系强度 {strength} 超出 0-1 范围（{rel.get('char_a_id')} - {rel.get('char_b_id')}）"
                )

            asymmetry = rel.get("asymmetry", -1)
            if asymmetry != -1 and not (0.0 <= asymmetry <= 1.0):
                issues.append(
                    f"非对称性 {asymmetry} 超出 0-1 范围"
                )

            rel_type = rel.get("type", "")
            if rel_type == "enmity" and strength < 0.6:
                issues.append(
                    f"敌对关系（{rel.get('char_a_id')} - {rel.get('char_b_id')}）强度应 > 0.6，当前 {strength}"
                )

        for pid in protagonist_ids:
            prot_relations = [
                r
                for r in relations
                if r.get("char_a_id") == pid or r.get("char_b_id") == pid
            ]
            if len(prot_relations) < 2:
                issues.append(
                    f"主角 {pid} 至少与 2 个其他角色有关系，当前 {len(prot_relations)} 条"
                )

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues