import json
from datetime import datetime, timezone

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult


class ArchiveBuilder(BaseModule):
    module_name = "archive_builder"
    depends_on = [
        "theme_engine", "outline_builder", "world_builder",
        "character_builder", "relation_builder", "arc_builder",
        "faction_builder", "faction_relation", "item_builder",
        "foreshadow_manager",
    ]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        dependencies = context.get("dependencies", {})
        errors = []

        archive_data = content.get("archive", {})

        layer1 = archive_data.get("layer1_identity_card", {})
        layer2 = archive_data.get("layer2_core_summary", {})
        layer3 = archive_data.get("layer3_module_snapshots", {})

        db.execute(
            text("""
                INSERT OR REPLACE INTO archives
                (novel_id, layer1_identity_card, layer2_core_summary,
                 layer3_module_snapshots, updated_at)
                VALUES (:novel_id, :layer1, :layer2, :layer3, :updated_at)
            """),
            {
                "novel_id": novel_id,
                "layer1": json.dumps(layer1, ensure_ascii=False),
                "layer2": json.dumps(layer2, ensure_ascii=False),
                "layer3": json.dumps(layer3, ensure_ascii=False),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        recent_changes = layer3.get("recent_changes", [])
        for change in recent_changes:
            db.execute(
                text("""
                    INSERT INTO change_log
                    (novel_id, timestamp, step, module, action,
                     entity_id, entity_type, summary, changed_fields)
                    VALUES (:novel_id, :timestamp, :step, :module, :action,
                            :entity_id, :entity_type, :summary, :changed_fields)
                """),
                {
                    "novel_id": novel_id,
                    "timestamp": change.get(
                        "timestamp", datetime.now(timezone.utc).isoformat()
                    ),
                    "step": change.get("step", ""),
                    "module": change.get("module", ""),
                    "action": change.get("action", "update"),
                    "entity_id": change.get("entity_id", ""),
                    "entity_type": change.get("entity_type", ""),
                    "summary": change.get("summary", ""),
                    "changed_fields": json.dumps(
                        change.get("changed_fields", []), ensure_ascii=False
                    ),
                },
            )

        db.flush()

        summary_parts = []
        if layer1:
            summary_parts.append(f"身份卡已更新")
        if layer2:
            summary_parts.append("核心摘要已提取")
        if layer3:
            snapshot_count = len(
                layer3.get("character_list", [])
            )
            summary_parts.append(f"模块快照已聚合（{snapshot_count} 个实体）")

        return ModuleResult(
            success=True,
            summary=f"小说档案已更新：{' / '.join(summary_parts)}",
            data={"archive": archive_data},
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        archive = data.get("archive", {})
        layer3 = archive.get("layer3_module_snapshots", {})

        character_list = layer3.get("character_list", [])
        faction_list = layer3.get("faction_list", [])

        if not character_list:
            issues.append("档案必须引用 characters 表中所有角色")

        if not faction_list:
            issues.append("档案必须引用 factions 表中所有势力")

        recent_changes = layer3.get("recent_changes", [])
        if len(recent_changes) < 5:
            issues.append(
                f"change_log 应包含最近 5 次变更，当前 {len(recent_changes)} 条"
            )

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues