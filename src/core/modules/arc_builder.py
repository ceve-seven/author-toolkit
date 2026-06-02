import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult


class ArcBuilder(BaseModule):
    module_name = "arc_builder"
    depends_on = ["character_builder", "relation_builder"]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        arcs = content.get("arcs", [])

        for arc in arcs:
            db.execute(
                text("""
                    INSERT OR REPLACE INTO character_arcs
                    (novel_id, char_id, arc_type, start_state, catalyst_event,
                     change_process, end_state, chapter_mapping)
                    VALUES (:novel_id, :char_id, :arc_type, :start_state,
                            :catalyst_event, :change_process, :end_state, :chapter_mapping)
                """),
                {
                    "novel_id": novel_id,
                    "char_id": arc.get("char_id", ""),
                    "arc_type": arc.get("arc_type", ""),
                    "start_state": json.dumps(
                        arc.get("start_state", {}), ensure_ascii=False
                    ),
                    "catalyst_event": arc.get("catalyst_event", ""),
                    "change_process": json.dumps(
                        arc.get("change_process", []), ensure_ascii=False
                    ),
                    "end_state": json.dumps(
                        arc.get("end_state", {}), ensure_ascii=False
                    ),
                    "chapter_mapping": json.dumps(
                        arc.get("chapter_mapping", []), ensure_ascii=False
                    ),
                },
            )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(arcs)} 条角色弧线",
            data={"arcs": arcs},
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        arcs = data.get("arcs", [])

        dependencies = result.data.get("_dependencies", {})
        characters = dependencies.get("character_builder", {}).get("characters", [])
        protagonist_ids = {
            c.get("id") for c in characters if c.get("role") == "主角"
        }

        for arc in arcs:
            char_id = arc.get("char_id", "")

            if char_id in protagonist_ids:
                start_state = arc.get("start_state", {})
                end_state = arc.get("end_state", {})
                catalyst_event = arc.get("catalyst_event", "")
                change_process = arc.get("change_process", [])
                chapter_mapping = arc.get("chapter_mapping", [])

                if not start_state or not end_state or not catalyst_event:
                    issues.append(
                        f"主角 {char_id} 弧线不完整（缺少 start_state/end_state/catalyst_event）"
                    )

                if start_state == end_state:
                    issues.append(f"主角 {char_id} 的 start_state 与 end_state 不得相同")

                if len(change_process) < 2:
                    issues.append(
                        f"主角 {char_id} 的 change_process 至少 2 个 phase，当前 {len(change_process)} 个"
                    )

            else:
                if arc.get("start_state") and arc.get("end_state"):
                    if arc["start_state"] == arc["end_state"]:
                        issues.append(
                            f"角色 {char_id} 的 start_state 与 end_state 不得相同"
                        )

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues