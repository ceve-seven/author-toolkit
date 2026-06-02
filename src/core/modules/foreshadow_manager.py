import json
from datetime import datetime, timezone

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils.id_generator import generate_id


class ForeshadowManager(BaseModule):
    module_name = "foreshadow_manager"
    depends_on = ["outline_builder", "character_builder", "faction_builder"]

    VALID_TYPES = {
        "信息伏笔", "人物伏笔", "物品伏笔", "能力伏笔",
        "关系伏笔", "规则伏笔", "情感伏笔", "结构伏笔",
    }
    VALID_STATUSES = {"待埋设", "已埋设", "待回收", "已回收", "已废弃"}
    VALID_DEPTHS = {"浅层", "中层", "深层"}
    DENSITY_WARN_THRESHOLD = 5.0

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        chroma = context.get("chroma_client")
        errors = []

        foreshadows = content.get("foreshadows", [])
        chroma_ids = []
        density_curve = content.get("density_curve", [])

        for fore in foreshadows:
            fore_id = fore.get("id", generate_id("FORE", novel_id, db))
            chroma_id = fore.get("chroma_id", "")

            now = datetime.now(timezone.utc).isoformat()

            db.execute(
                text("""
                    INSERT OR REPLACE INTO foreshadows
                    (novel_id, foreshadow_id, type, status,
                     plant_chapter, plant_location, plant_form,
                     reveal_chapter_planned, reveal_chapter_actual, reveal_form,
                     payload, surface, depth,
                     related_char, related_item, related_plot,
                     parent_fore, child_fores, tags,
                     importance, chroma_id, created_at, last_modified)
                    VALUES (:novel_id, :foreshadow_id, :type, :status,
                            :plant_chapter, :plant_location, :plant_form,
                            :reveal_chapter_planned, :reveal_chapter_actual, :reveal_form,
                            :payload, :surface, :depth,
                            :related_char, :related_item, :related_plot,
                            :parent_fore, :child_fores, :tags,
                            :importance, :chroma_id, :created_at, :last_modified)
                """),
                {
                    "novel_id": novel_id,
                    "foreshadow_id": fore_id,
                    "type": fore.get("type", ""),
                    "status": fore.get("status", "待埋设"),
                    "plant_chapter": fore.get("plant_chapter", 0),
                    "plant_location": fore.get("plant_location", ""),
                    "plant_form": fore.get("plant_form", ""),
                    "reveal_chapter_planned": fore.get(
                        "reveal_chapter_planned", 0
                    ),
                    "reveal_chapter_actual": fore.get(
                        "reveal_chapter_actual", 0
                    ),
                    "reveal_form": fore.get("reveal_form", ""),
                    "payload": fore.get("payload", ""),
                    "surface": fore.get("surface", ""),
                    "depth": fore.get("depth", "浅层"),
                    "related_char": json.dumps(
                        fore.get("related_char", []), ensure_ascii=False
                    ),
                    "related_item": json.dumps(
                        fore.get("related_item", []), ensure_ascii=False
                    ),
                    "related_plot": json.dumps(
                        fore.get("related_plot", []), ensure_ascii=False
                    ),
                    "parent_fore": fore.get("parent_fore", ""),
                    "child_fores": json.dumps(
                        fore.get("child_fores", []), ensure_ascii=False
                    ),
                    "tags": json.dumps(
                        fore.get("tags", []), ensure_ascii=False
                    ),
                    "importance": fore.get("importance", 0.5),
                    "chroma_id": chroma_id,
                    "created_at": now,
                    "last_modified": now,
                },
            )

            if chroma is not None:
                try:
                    collection = chroma.get_or_create_collection(
                        name="foreshadows"
                    )
                    embed_text = f"{fore.get('payload', '')} {fore.get('surface', '')}"

                    if chroma_id:
                        collection.update(
                            ids=[chroma_id],
                            documents=[embed_text],
                            metadatas=[{
                                "foreshadow_id": fore_id,
                                "novel_id": novel_id,
                                "type": fore.get("type", ""),
                                "status": fore.get("status", ""),
                                "chapter": fore.get("plant_chapter", 0),
                                "importance": fore.get("importance", 0.5),
                            }],
                        )
                    else:
                        new_chroma_id = f"{novel_id}_{fore_id}"
                        collection.add(
                            ids=[new_chroma_id],
                            documents=[embed_text],
                            metadatas=[{
                                "foreshadow_id": fore_id,
                                "novel_id": novel_id,
                                "type": fore.get("type", ""),
                                "status": fore.get("status", ""),
                                "chapter": fore.get("plant_chapter", 0),
                                "importance": fore.get("importance", 0.5),
                            }],
                        )
                        chroma_id = new_chroma_id

                        db.execute(
                            text("""
                                UPDATE foreshadows
                                SET chroma_id = :chroma_id
                                WHERE novel_id = :novel_id
                                  AND foreshadow_id = :foreshadow_id
                            """),
                            {
                                "chroma_id": chroma_id,
                                "novel_id": novel_id,
                                "foreshadow_id": fore_id,
                            },
                        )

                    chroma_ids.append(chroma_id)
                except Exception as e:
                    errors.append(f"ChromaDB 同步失败（{fore_id}）：{str(e)}")

        for snapshot in density_curve:
            db.execute(
                text("""
                    INSERT OR REPLACE INTO foreshadow_density_snapshots
                    (novel_id, chapter, active_count, density_per_kword,
                     new_count, resolved_count)
                    VALUES (:novel_id, :chapter, :active_count, :density_per_kword,
                            :new_count, :resolved_count)
                """),
                {
                    "novel_id": novel_id,
                    "chapter": snapshot.get("chapter", 0),
                    "active_count": snapshot.get("active_count", 0),
                    "density_per_kword": snapshot.get("density", 0.0),
                    "new_count": snapshot.get("new_count", 0),
                    "resolved_count": snapshot.get("resolved_count", 0),
                },
            )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(foreshadows)} 条伏笔，{len(density_curve)} 个密度快照",
            data={
                "foreshadows": foreshadows,
                "density_curve": density_curve,
                "chroma_ids": chroma_ids,
            },
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        prompt_rules = self.load_prompt_rules()
        data = result.data
        foreshadows = data.get("foreshadows", [])

        types_used = set()
        for fore in foreshadows:
            types_used.add(fore.get("type", ""))

            importance = fore.get("importance", 0.0)
            if not (0.0 <= importance <= 1.0):
                issues.append(
                    f"伏笔「{fore.get('foreshadow_id', '')}」importance {importance} 超出 0-1 范围"
                )

            status = fore.get("status", "")
            if status and status not in self.VALID_STATUSES:
                issues.append(
                    f"伏笔「{fore.get('foreshadow_id', '')}」状态「{status}」无效"
                )

            if importance > 0.7:
                reveal_planned = fore.get("reveal_chapter_planned", 0)
                if reveal_planned <= 0:
                    issues.append(
                        f"主伏笔（importance > 0.7）必须有 reveal_chapter_planned"
                    )

            depth = fore.get("depth", "")
            if depth and depth not in self.VALID_DEPTHS:
                issues.append(
                    f"伏笔「{fore.get('foreshadow_id', '')}」depth「{depth}」无效"
                )

            plant_ch = fore.get("plant_chapter", 0)
            reveal_ch = fore.get("reveal_chapter_planned", 0)
            if reveal_ch > 0 and plant_ch > 0 and reveal_ch <= plant_ch:
                issues.append(
                    f"伏笔「{fore.get('foreshadow_id', '')}」回收章节（{reveal_ch}）应在埋设章节（{plant_ch}）之后"
                )

        if len(types_used) < 3:
            issues.append(
                f"至少包含 3 种不同类型的伏笔，当前 {len(types_used)} 种：{types_used}"
            )

        density_curve = data.get("density_curve", [])
        for snap in density_curve:
            density = snap.get("density", 0.0)
            if density > self.DENSITY_WARN_THRESHOLD:
                issues.append(
                    f"第 {snap.get('chapter', '?')} 章伏笔密度 {density:.2f}/千字，超过阈值 {self.DENSITY_WARN_THRESHOLD}"
                )

        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name

        return issues