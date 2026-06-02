# -*- coding: utf-8 -*-
"""初始化数据库并创建小说项目（自动生成唯一 ID，不覆盖已有小说）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from datetime import datetime, timezone

from src.storage.database.engine import get_engine, init_schema
from src.utils.id_generator import generate_id
from sqlalchemy import text

# 初始化 schema（仅建表，不销毁数据）
init_schema()
print("数据库 schema 初始化完成")

# 创建小说项目（自动生成唯一 ID）
engine = get_engine()
novel_id = generate_id("NOV", "GLOBAL", engine=engine)
title = "神豪：从零开始的无限财富"
now = datetime.now(timezone.utc).isoformat()

with engine.connect() as conn:
    conn.execute(
        text("INSERT INTO novels (id, title, current_step, status, created_at, updated_at) "
             "VALUES (:id, :title, 1, '创作中', :now, :now)"),
        {"id": novel_id, "title": title, "now": now},
    )
    conn.commit()
    print(f"小说项目创建成功：{novel_id} - {title}")

    # 验证
    row = conn.execute(
        text("SELECT id, title, current_step FROM novels WHERE id = :id"),
        {"id": novel_id},
    ).fetchone()
    print(f"ID: {row[0]}, 标题: {row[1]}, 当前进度: {row[2]}")
