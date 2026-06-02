from __future__ import annotations

# 数据库中所有合法表名的白名单
VALID_TABLES: set[str] = {
    "novels", "id_counters", "inspirations", "themes", "outlines",
    "world_building", "world_rules", "characters", "relations",
    "character_arcs", "factions", "faction_members", "faction_relations",
    "char_faction_links", "items", "foreshadows",
    "foreshadow_density_snapshots", "volumes", "volume_chapters",
    "detail_outlines", "archives", "change_log", "synopses", "manuscripts",
    "fix_logs", "review_results", "step_data", "step_status",
    "purification_logs",
}


def validate_table_name(name: str) -> str:
    """校验表名是否在白名单内，防止 SQL 注入。

    所有使用 f-string 拼接表名的 SQL 查询，必须通过此函数校验后再执行。
    参数值来自硬编码映射，而不是用户输入。

    Raises:
        ValueError: 表名不在白名单中，附带有效表名列表

    Returns:
        原表名（校验通过后原样返回）
    """
    if name not in VALID_TABLES:
        similar = [t for t in VALID_TABLES if name.lower() in t.lower() or t.lower() in name.lower()]
        hint = ""
        if similar:
            hint = f"，您是不是想查: {similar}"
        raise ValueError(
            f"非法表名: '{name}'，不在白名单中{hint}\n"
            f"有效表名: {sorted(VALID_TABLES)}"
        )
    return name
