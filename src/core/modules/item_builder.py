import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class ItemBuilder(BaseModule):
    module_name = "item_builder"
    depends_on = ["world_builder"]

    VALID_TYPES = {
        "weapon", "artifact", "magic_item", "technology",
        "key_item", "daily_item",
    }

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        items = content.get("items", [])

        for item in items:
            item_id = item.get("id", generate_id("ITEM", novel_id, db))
            db.execute(
                text("""
                    INSERT OR REPLACE INTO items
                    (novel_id, item_id, name, type, purpose, background_story,
                     restrictions, current_owner, significance_to_plot,
                     first_appearance_chapter)
                    VALUES (:novel_id, :item_id, :name, :type, :purpose,
                            :background_story, :restrictions, :current_owner,
                            :significance_to_plot, :first_appearance_chapter)
                """),
                {
                    "novel_id": novel_id,
                    "item_id": item_id,
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "purpose": item.get("purpose", ""),
                    "background_story": item.get("background_story", ""),
                    "restrictions": json.dumps(
                        item.get("restrictions", []), ensure_ascii=False
                    ),
                    "current_owner": item.get("current_owner", ""),
                    "significance_to_plot": item.get("significance_to_plot", ""),
                    "first_appearance_chapter": item.get(
                        "first_appearance_chapter", 0
                    ),
                },
            )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(items)} 件物品",
            data={"items": items},
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        items = data.get("items", [])

        if len(items) < 3:
            issues.append(f"至少需要 3 件物品，当前 {len(items)} 件")

        for item in items:
            restrictions = item.get("restrictions", [])
            if not restrictions:
                issues.append(f"物品「{item.get('name', '')}」必须有限制条件")

            first_appearance = item.get("first_appearance_chapter", 0)
            if first_appearance < 1:
                issues.append(
                    f"物品「{item.get('name', '')}」首次出现章节无效：{first_appearance}"
                )

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues