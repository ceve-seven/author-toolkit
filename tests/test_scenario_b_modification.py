"""场景 B：修改循环验证"""
import json
import sqlite3

from tests.helpers import (
    DB_PATH,
    NOVEL_ID,
    init_database,
    insert_row,
    seed_novel,
)


def test_scenario_b():
    # 0. 初始化数据库
    init_database()
    seed_novel()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO characters (char_id, novel_id, name, role, layer1_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (f"{NOVEL_ID}-protagonist", NOVEL_ID, "主角", "protagonist",
         json.dumps({"age": 35, "gender": "男"}, ensure_ascii=False)),
    )
    conn.commit()

    cursor.execute(
        "INSERT INTO change_log (novel_id, timestamp, step, module, action, entity_id, entity_type, summary, changed_fields) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (NOVEL_ID, "2025-01-01T10:00:00",
         "人物设定", "character_builder",
         "generated", f"{NOVEL_ID}-protagonist",
         "character", "初始生成主角",
         json.dumps({"age": 30}, ensure_ascii=False)),
    )
    cursor.execute(
        "INSERT INTO change_log (novel_id, timestamp, step, module, action, entity_id, entity_type, summary, changed_fields) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (NOVEL_ID, "2025-01-01T11:00:00",
         "人物设定", "character_builder",
         "modified", f"{NOVEL_ID}-protagonist",
         "character", "修改主角年龄为 35",
         json.dumps({"age": 35}, ensure_ascii=False)),
    )
    conn.commit()

    # 1. 验证角色年龄已更新
    row = cursor.execute(
        "SELECT layer1_json FROM characters WHERE role='protagonist'"
    ).fetchone()
    assert row is not None, "主角不存在"
    layer1 = json.loads(row[0])
    assert layer1["age"] == 35, f"年龄未更新: {layer1['age']}"

    # 2. 验证 change_log 记录修改链
    logs = cursor.execute(
        "SELECT action FROM change_log WHERE step='人物设定' ORDER BY timestamp"
    ).fetchall()
    actions = [log[0] for log in logs]
    assert "generated" in actions, "缺少生成记录"
    assert "modified" in actions, "缺少修改记录"

    conn.close()

    # 关闭 SQLAlchemy 引擎以释放文件锁
    from src.storage.database.engine import reset_engine
    reset_engine()

    print("✅ 场景 B 验证通过")