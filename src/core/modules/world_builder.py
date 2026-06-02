import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class WorldBuilder(BaseModule):
    module_name = "world_builder"
    depends_on = ["theme_engine", "outline_builder"]

    VALID_DIMENSIONS = {
        "物理规则", "地理空间", "时间历史", "社会结构",
        "文化习俗", "科技水平", "魔法/超自然体系", "经济体系",
    }

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        dimensions = content.get("dimensions", [])

        for dim in dimensions:
            dim_name = dim.get("name", "")
            rules = dim.get("rules", [])

            db.execute(
                text("""
                    INSERT OR REPLACE INTO world_building
                    (novel_id, dimension_name, rules)
                    VALUES (:novel_id, :dimension_name, :rules)
                """),
                {
                    "novel_id": novel_id,
                    "dimension_name": dim_name,
                    "rules": json.dumps(rules, ensure_ascii=False),
                },
            )

            for rule in rules:
                rule_id = rule.get(
                    "id",
                    generate_id("RULE", novel_id, db),
                )
                db.execute(
                    text("""
                        INSERT OR REPLACE INTO world_rules
                        (rule_id, novel_id, dimension, description, scope, constraints)
                        VALUES (:rule_id, :novel_id, :dimension, :description,
                                :scope, :constraints)
                    """),
                    {
                        "rule_id": rule_id,
                        "novel_id": novel_id,
                        "dimension": dim_name,
                        "description": rule.get("description", ""),
                        "scope": rule.get("scope", ""),
                        "constraints": json.dumps(
                            rule.get("constraints", ""), ensure_ascii=False
                        ),
                    },
                )

        db.flush()

        dim_names = [d.get("name", "") for d in dimensions]
        total_rules = sum(len(d.get("rules", [])) for d in dimensions)

        return ModuleResult(
            success=True,
            summary=f"世界观已保存：{len(dimensions)} 个维度，{total_rules} 条规则",
            data={"dimensions": dimensions},
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        dimensions = data.get("dimensions", [])

        dim_names = {d.get("name", "") for d in dimensions}
        missing = self.VALID_DIMENSIONS - dim_names
        if missing:
            issues.append(f"缺少维度：{', '.join(sorted(missing))}")

        for dim in dimensions:
            dim_name = dim.get("name", "")
            rules = dim.get("rules", [])
            if len(rules) < 2:
                issues.append(f"维度「{dim_name}」规则数不足 2 条（当前 {len(rules)} 条）")

        total_rules = sum(len(d.get("rules", [])) for d in dimensions)
        if total_rules < 16:
            issues.append(f"总规则数不足 16 条（当前 {total_rules} 条）")

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues