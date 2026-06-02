"""场景 A：正常流程验证"""
import json
import sqlite3
from pathlib import Path

from tests.helpers import (
    DB_PATH,
    init_database,
    seed_scenario_a,
)


def test_scenario_a():
    # 0. 初始化数据库（init_schema 内部已 DROP + CREATE，无需提前删文件）
    init_database()
    seed_scenario_a()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. SQLite 数据完整性
    tables_to_check = [
        "inspirations", "themes", "outlines", "world_building",
        "characters", "relations", "character_arcs", "factions",
        "faction_relations", "items", "foreshadows", "archives",
        "synopses", "volumes", "detail_outlines", "manuscripts",
        "review_results",
    ]
    for table in tables_to_check:
        count = cursor.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        assert count > 0, f"{table} 表无数据"

    # 验证 manuscripts 状态链
    statuses = cursor.execute(
        "SELECT DISTINCT status FROM manuscripts"
    ).fetchall()
    status_list = [s[0] for s in statuses]
    assert "draft" in status_list

    # 2. 日志完整性（仅验证日志文件存在）
    log_path = Path("logs/novel_creation.log")
    assert log_path.exists(), "日志文件不存在"

    conn.close()

    # 关闭 SQLAlchemy 引擎以释放文件锁
    from src.storage.database.engine import reset_engine
    reset_engine()

    print("✅ 场景 A 验证通过")