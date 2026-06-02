import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class CharacterBuilder(BaseModule):
    module_name = "character_builder"
    depends_on = ["world_builder"]

    MIN_REQUIRED_EMOTIONS = {"高兴", "愤怒", "悲伤", "恐惧", "惊讶"}

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        characters = content.get("characters", [])

        for char in characters:
            char_id = char.get("id", generate_id("CHAR", novel_id, db))
            weight = char.get("weight", {})

            weighted_score = (
                weight.get("arc_contribution", 0) * 0.35
                + weight.get("plot_driving", 0) * 0.30
                + weight.get("theme_carrying", 0) * 0.20
                + weight.get("network_centrality", 0) * 0.15
            )

            db.execute(
                text("""
                    INSERT OR REPLACE INTO characters
                    (novel_id, char_id, name, role,
                     layer1_json, layer2_json, layer3_json, layer4_json,
                     weight_tier, weight_score, weight_json)
                    VALUES (:novel_id, :char_id, :name, :role,
                            :layer1_json, :layer2_json, :layer3_json, :layer4_json,
                            :weight_tier, :weight_score, :weight_json)
                """),
                {
                    "novel_id": novel_id,
                    "char_id": char_id,
                    "name": char.get("name", ""),
                    "role": char.get("role", ""),
                    "layer1_json": json.dumps(
                        char.get("layer1_identity", {}), ensure_ascii=False
                    ),
                    "layer2_json": json.dumps(
                        char.get("layer2_psychology", {}), ensure_ascii=False
                    ),
                    "layer3_json": json.dumps(
                        char.get("layer3_ability", {}), ensure_ascii=False
                    ),
                    "layer4_json": json.dumps(
                        char.get("layer4_special", {}), ensure_ascii=False
                    ),
                    "weight_tier": weight.get("tier", ""),
                    "weight_score": weighted_score,
                    "weight_json": json.dumps(weight, ensure_ascii=False),
                },
            )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(characters)} 个角色",
            data={"characters": characters},
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        characters = data.get("characters", [])

        if len(characters) < 3:
            issues.append(f"至少需要 3 个角色（1 主角 + 2 配角），当前 {len(characters)} 个")

        protagonists = [c for c in characters if c.get("role") == "主角"]

        for char in characters:
            required_layers = [
                "layer1_identity",
                "layer2_psychology",
                "layer3_ability",
                "layer4_special",
            ]
            for layer in required_layers:
                if layer not in char:
                    issues.append(
                        f"角色「{char.get('name', char.get('id', ''))}」缺少 {layer}"
                    )

            layer3 = char.get("layer3_ability", {})
            knowledge_boundaries = layer3.get("knowledge_boundaries", {})
            not_knows = knowledge_boundaries.get("not_knows", [])
            if len(not_knows) < 2:
                issues.append(
                    f"角色「{char.get('name', '')}」的 not_knows 至少 2 项，当前 {len(not_knows)} 项"
                )

            layer2 = char.get("layer2_psychology", {})
            body_dict = layer2.get("body_language_dictionary", {})
            covered_emotions = set(body_dict.keys())
            missing_emotions = self.MIN_REQUIRED_EMOTIONS - covered_emotions
            if missing_emotions:
                issues.append(
                    f"角色「{char.get('name', '')}」情感身体词典缺少：{', '.join(missing_emotions)}"
                )
            for emotion, reactions in body_dict.items():
                if isinstance(reactions, list) and len(reactions) < 2:
                    issues.append(
                        f"角色「{char.get('name', '')}」情感「{emotion}」至少 2 个身体反应"
                    )

            if char in protagonists:
                layer4 = char.get("layer4_special", {})
                secrets = layer4.get("secrets", [])
                if not secrets:
                    issues.append(
                        f"主角「{char.get('name', '')}」必须有秘密（secrets）"
                    )
                cracks = layer4.get("cracks", [])
                if len(cracks) < 2:
                    issues.append(
                        f"主角「{char.get('name', '')}」至少 2 个破绽（cracks），当前 {len(cracks)} 个"
                    )

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues