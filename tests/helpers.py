from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DB_PATH = "data/test_novel.db"
DB_PATH = str(PROJECT_ROOT / TEST_DB_PATH)
NOVEL_ID = "test-novel-001"
STEP_NAMES = [
    "灵感启动", "小说主题", "世界观设定", "人物设定",
    "势力设定", "物品库", "人物关系", "势力关系", "人物-势力关联", "角色弧线",
    "伏笔追踪", "拟定大纲", "分卷配置", "章节细纲",
    "小说档案", "小说简介", "正文初稿",
    "正文审核", "正文修正", "导出发布",
]


def use_test_db():
    from src.config.settings import Config
    Config.SQLITE_PATH = TEST_DB_PATH


def ensure_db_clean():
    db = Path(DB_PATH)
    wal = db.with_suffix(".db-wal")
    shm = db.with_suffix(".db-shm")
    for p in [db, wal, shm]:
        if p.exists():
            p.unlink()


def init_database():
    use_test_db()
    from src.storage.database.engine import reset_engine, init_schema
    reset_engine()
    init_schema()


def seed_novel():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO novels (id, title, author, current_step, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        (NOVEL_ID, "测试小说", "测试作者", 1, "创作中"),
    )
    conn.commit()
    conn.close()


def insert_row(table: str, data: dict[str, Any]):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    cursor.execute(
        f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})",
        tuple(data.values()),
    )
    conn.commit()
    conn.close()


def seed_scenario_a():
    use_test_db()
    from src.storage.database.engine import reset_engine
    reset_engine()
    seed_novel()

    insp_id = f"{NOVEL_ID}-INSP-001"
    insert_row("inspirations", {
        "novel_id": NOVEL_ID, "direction_id": insp_id,
        "title": "测试灵感", "concept": "测试概念",
        "innovation_score": 0.8, "summary": "测试摘要",
        "emotional_potential": 0.7, "created_at": "2025-01-01",
    })
    insert_row("themes", {
        "novel_id": NOVEL_ID, "surface_theme": "表层主题",
        "deep_theme": "深层主题", "emotional_hook": "情感钩子",
        "theme_statement": "主题陈述", "reverse_confirmation": "反转确认",
    })
    insert_row("outlines", {
        "novel_id": NOVEL_ID, "acts": "三幕结构",
        "causal_chain": "因果链", "rhythm_map": "节奏图",
    })
    insert_row("world_building", {
        "novel_id": NOVEL_ID, "dimension_name": "测试维度",
        "rules": "测试规则",
    })
    insert_row("characters", {
        "char_id": f"{NOVEL_ID}-protagonist",
        "novel_id": NOVEL_ID, "name": "主角", "role": "protagonist",
        "layer1_json": json.dumps({"age": 30, "gender": "男"}, ensure_ascii=False),
    })
    insert_row("relations", {
        "relation_id": f"{NOVEL_ID}-REL-001",
        "novel_id": NOVEL_ID, "char_a_id": f"{NOVEL_ID}-protagonist",
        "char_b_id": f"{NOVEL_ID}-antagonist",
        "type": "敌对", "strength": 0.8, "asymmetry": 0.5,
        "history": "暂无", "trajectory": "上升",
    })
    insert_row("character_arcs", {
        "novel_id": NOVEL_ID, "char_id": f"{NOVEL_ID}-protagonist",
        "arc_type": "成长", "start_state": "初始状态",
        "catalyst_event": "催化事件", "change_process": "变化过程",
        "end_state": "最终状态", "chapter_mapping": "1-10",
    })
    insert_row("factions", {
        "faction_id": f"{NOVEL_ID}-FAC-001",
        "novel_id": NOVEL_ID, "name": "测试组织",
        "type": "秘密结社", "hierarchy": "层级结构",
        "goals": "目标", "resources": "资源",
        "doctrines": "教义", "reputation": 0.5,
    })
    insert_row("faction_relations", {
        "relation_id": f"{NOVEL_ID}-FR-001",
        "novel_id": NOVEL_ID, "faction_a_id": f"{NOVEL_ID}-FAC-001",
        "faction_b_id": f"{NOVEL_ID}-FAC-002",
        "type": "同盟", "strength": 0.7,
        "history": "暂无", "treaties": "条约", "hidden_agenda": "隐藏议程",
    })
    insert_row("items", {
        "item_id": f"{NOVEL_ID}-ITEM-001",
        "novel_id": NOVEL_ID, "name": "测试物品",
        "type": "武器", "purpose": "测试目的",
        "background_story": "背景故事", "restrictions": "限制",
        "current_owner": f"{NOVEL_ID}-protagonist",
        "significance_to_plot": "情节意义",
        "first_appearance_chapter": 1,
    })
    insert_row("foreshadows", {
        "foreshadow_id": f"{NOVEL_ID}-FS-001",
        "novel_id": NOVEL_ID, "type": "情节伏笔", "status": "未揭示",
        "plant_chapter": 1, "plant_location": "第一章",
        "plant_form": "对话", "reveal_chapter_planned": 10,
        "reveal_form": "反转", "payload": "有效载荷",
        "surface": "表面信息", "depth": "深层信息",
        "importance": 0.8, "created_at": "2025-01-01",
        "last_modified": "2025-01-01",
    })
    insert_row("archives", {
        "novel_id": NOVEL_ID, "layer1_identity_card": "身份卡",
        "layer2_core_summary": "核心摘要",
        "layer3_module_snapshots": "模块快照",
        "updated_at": "2025-01-01",
    })
    insert_row("synopses", {
        "novel_id": NOVEL_ID,
        "one_liner": "一句话梗概", "short_blurb": "短简介",
        "standard_blurb": "标准简介", "long_blurb": "长简介",
        "core_conflict": "核心冲突", "world_highlight": "世界亮点",
        "selling_points": "卖点", "target_audience": "目标读者",
        "tone_tags": "风格标签", "comparison_titles": "对标作品",
        "hook_question": "钩子问题", "word_count": 100000,
    })
    insert_row("volumes", {
        "volume_id": f"{NOVEL_ID}-VOL-001",
        "novel_id": NOVEL_ID, "name": "第一卷",
        "chapter_range": "1-10", "boundary_gravity": "边界引力",
        "pacing": "节奏", "major_conflict": "主要冲突",
        "character_focus": "角色聚焦", "themes": "主题",
        "cliffhanger": "悬念钩子",
        "volume_rhythm_curve": "节奏曲线",
        "volume_rhythm_evaluation": "节奏评估",
    })
    insert_row("detail_outlines", {
        "novel_id": NOVEL_ID, "chapter_number": 1,
        "chapter_constraint_summary": "约束摘要",
        "scenes": json.dumps([{"scene_number": 1, "location": "测试场景"}], ensure_ascii=False),
    })
    insert_row("manuscripts", {
        "novel_id": NOVEL_ID, "chapter_number": 1, "title": "第一章",
        "compiled_constraint_file": "约束文件",
        "scenes": json.dumps([{"scene_number": 1}], ensure_ascii=False),
        "word_count": 3000, "status": "draft",
    })
    insert_row("review_results", {
        "novel_id": NOVEL_ID, "step_number": 17, "module_name": "正文审核",
        "level": "info", "score": 0.85, "details": "通过",
        "suggestions": "优化建议", "created_at": "2025-01-01",
    })
