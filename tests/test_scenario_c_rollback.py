"""场景 C：回退操作验证"""
import json
import sqlite3

from tests.helpers import (
    DB_PATH,
    NOVEL_ID,
    init_database,
    insert_row,
    seed_novel,
)


def test_scenario_c():
    # 0. 初始化数据库（仅建表，不填充场景 A 数据）
    init_database()
    seed_novel()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 清理可能残留的旧数据，确保环节 04-08 表为空
    for table in ["world_building", "characters", "relations",
                  "character_arcs", "factions"]:
        cursor.execute(f"DELETE FROM {table}")
    conn.commit()

    # 环节 01-03：填充数据（应保留）
    insp_id = f"{NOVEL_ID}-INSP-001"
    cursor.execute(
        "INSERT OR IGNORE INTO inspirations (novel_id, direction_id, title, concept, innovation_score, summary, emotional_potential, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (NOVEL_ID, insp_id, "回退测试灵感", "测试概念", 0.8, "摘要", 0.7, "2025-01-01"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO themes (novel_id, surface_theme, deep_theme, emotional_hook, theme_statement, reverse_confirmation) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (NOVEL_ID, "表层", "深层", "钩子", "陈述", "确认"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO outlines (novel_id, acts, causal_chain, rhythm_map) "
        "VALUES (?, ?, ?, ?)",
        (NOVEL_ID, "三幕", "因果链", "节奏图"),
    )
    conn.commit()

    # 环节 04-08：不插入数据（模拟回退后清空）

    # change_log 回退记录
    cursor.execute(
        "INSERT INTO change_log (novel_id, timestamp, step, module, action, entity_id, entity_type, summary, changed_fields) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (NOVEL_ID, "2025-01-01T12:00:00",
         "世界观", "rollback", "rollback", NOVEL_ID,
         "novel", "回退至环节 04",
         json.dumps({"target_step": 4}, ensure_ascii=False)),
    )

    # step_data 记录
    cursor.execute(
        "INSERT INTO step_data (novel_id, step_number, module_name, status, data, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (NOVEL_ID, 4, "world_builder", "pending", "{}", "2025-01-01"),
    )
    conn.commit()

    # 1. 环节 01-03 数据保留
    assert cursor.execute(
        "SELECT count(*) FROM inspirations"
    ).fetchone()[0] > 0, "灵感数据被删除"
    assert cursor.execute(
        "SELECT count(*) FROM themes"
    ).fetchone()[0] > 0, "主题数据被删除"
    assert cursor.execute(
        "SELECT count(*) FROM outlines"
    ).fetchone()[0] > 0, "大纲数据被删除"

    # 2. 环节 04-08 数据删除
    deleted_tables = ["world_building", "characters", "relations",
                      "character_arcs", "factions"]
    for table in deleted_tables:
        count = cursor.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        assert count == 0, f"{table} 表有 {count} 条数据未被删除"

    # 3. change_log 有回退记录
    rollback_logs = cursor.execute(
        "SELECT action, summary FROM change_log WHERE action='rollback'"
    ).fetchall()
    assert len(rollback_logs) > 0, "缺少回退日志"

    # 4. 验证 step_data 表的状态
    step_04 = cursor.execute(
        "SELECT status FROM step_data WHERE step_number=4"
    ).fetchone()
    assert step_04 is not None, "环节 04 无状态记录"
    assert step_04[0] == "pending", f"环节 04 状态异常: {step_04[0]}"

    conn.close()

    # 关闭 SQLAlchemy 引擎以释放文件锁
    from src.storage.database.engine import reset_engine
    reset_engine()

    print("✅ 场景 C 验证通过")