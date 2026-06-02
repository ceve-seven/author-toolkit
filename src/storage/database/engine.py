from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import Config
from src.storage.database.models import Base


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def reset_engine() -> None:
    """重置数据库引擎（测试隔离用：切换到测试数据库路径后调用此函数）"""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        db_path = Config.SQLITE_PATH
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _enable_wal(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def init_db() -> None:
    """仅创建 ORM 模型表（适用于旧版兼容）"""
    engine = get_engine()
    Base.metadata.create_all(engine)


def init_schema() -> None:
    """创建所有模块所需表（列名与模块 SQL 查询兼容）

    使用 CREATE TABLE IF NOT EXISTS，仅在表不存在时创建，已有数据不会被销毁。
    可安全重复调用。
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS novels (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT,
                current_step INTEGER DEFAULT 1, status TEXT DEFAULT '创作中',
                created_at TEXT, updated_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS id_counters (
                novel_id TEXT, prefix TEXT, current_value INTEGER DEFAULT 0,
                PRIMARY KEY (novel_id, prefix)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inspirations (
                novel_id TEXT, direction_id TEXT,
                title TEXT, concept TEXT, innovation_score REAL,
                summary TEXT, emotional_potential REAL, created_at TEXT,
                PRIMARY KEY (novel_id, direction_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS themes (
                novel_id TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT,
                surface_theme TEXT, deep_theme TEXT, emotional_hook TEXT,
                theme_statement TEXT, reverse_confirmation TEXT,
                UNIQUE(novel_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS outlines (
                novel_id TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT,
                acts TEXT, causal_chain TEXT, rhythm_map TEXT,
                UNIQUE(novel_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS world_building (
                novel_id TEXT, dimension_name TEXT, rules TEXT,
                UNIQUE(novel_id, dimension_name)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS world_rules (
                novel_id TEXT, rule_id TEXT, dimension TEXT,
                description TEXT, scope TEXT, constraints TEXT,
                PRIMARY KEY (novel_id, rule_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS characters (
                novel_id TEXT, char_id TEXT, name TEXT, role TEXT,
                layer1_json TEXT, layer2_json TEXT, layer3_json TEXT, layer4_json TEXT,
                weight_tier TEXT, weight_score REAL, weight_json TEXT,
                PRIMARY KEY (novel_id, char_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS relations (
                novel_id TEXT, relation_id TEXT,
                char_a_id TEXT, char_b_id TEXT,
                type TEXT, strength REAL, asymmetry REAL,
                history TEXT, trajectory TEXT,
                PRIMARY KEY (novel_id, relation_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS character_arcs (
                novel_id TEXT, char_id TEXT, arc_type TEXT,
                start_state TEXT, catalyst_event TEXT,
                change_process TEXT, end_state TEXT, chapter_mapping TEXT,
                PRIMARY KEY (novel_id, char_id, arc_type)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS factions (
                novel_id TEXT, faction_id TEXT, name TEXT, type TEXT,
                hierarchy TEXT, goals TEXT, resources TEXT,
                doctrines TEXT, reputation REAL,
                PRIMARY KEY (novel_id, faction_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS faction_members (
                novel_id TEXT, faction_id TEXT, char_id TEXT, role TEXT, rank TEXT,
                PRIMARY KEY (novel_id, faction_id, char_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS faction_relations (
                novel_id TEXT, relation_id TEXT,
                faction_a_id TEXT, faction_b_id TEXT,
                type TEXT, strength REAL,
                history TEXT, treaties TEXT, hidden_agenda TEXT,
                PRIMARY KEY (novel_id, relation_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS char_faction_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, char_id TEXT, faction_id TEXT,
                membership_type TEXT, join_chapter INTEGER,
                leave_chapter INTEGER, role_in_faction TEXT,
                loyalty REAL, notes TEXT,
                UNIQUE(novel_id, char_id, faction_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS items (
                novel_id TEXT, item_id TEXT, name TEXT, type TEXT,
                purpose TEXT, background_story TEXT, restrictions TEXT,
                current_owner TEXT, significance_to_plot TEXT,
                first_appearance_chapter INTEGER,
                PRIMARY KEY (novel_id, item_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS foreshadows (
                novel_id TEXT, foreshadow_id TEXT,
                type TEXT, status TEXT,
                plant_chapter INTEGER, plant_location TEXT, plant_form TEXT,
                reveal_chapter_planned INTEGER, reveal_chapter_actual INTEGER,
                reveal_form TEXT, payload TEXT, surface TEXT, depth TEXT,
                related_char TEXT, related_item TEXT, related_plot TEXT,
                parent_fore TEXT, child_fores TEXT, tags TEXT,
                importance REAL, chroma_id TEXT,
                created_at TEXT, last_modified TEXT,
                PRIMARY KEY (novel_id, foreshadow_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS foreshadow_density_snapshots (
                novel_id TEXT, chapter INTEGER, active_count INTEGER,
                density_per_kword REAL, new_count INTEGER, resolved_count INTEGER,
                UNIQUE(novel_id, chapter)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS volumes (
                novel_id TEXT, volume_id TEXT, name TEXT,
                chapter_range TEXT, boundary_gravity TEXT, pacing TEXT,
                major_conflict TEXT, character_focus TEXT, themes TEXT,
                cliffhanger TEXT, volume_rhythm_curve TEXT,
                volume_rhythm_evaluation TEXT,
                PRIMARY KEY (novel_id, volume_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS volume_chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, volume_id TEXT, chapter_number INTEGER,
                pov_character TEXT, summary TEXT, word_count_budget INTEGER,
                UNIQUE(novel_id, volume_id, chapter_number)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS detail_outlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, chapter_number INTEGER,
                chapter_constraint_summary TEXT, scenes TEXT,
                UNIQUE(novel_id, chapter_number)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS archives (
                novel_id TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer1_identity_card TEXT, layer2_core_summary TEXT,
                layer3_module_snapshots TEXT, updated_at TEXT,
                UNIQUE(novel_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, timestamp TEXT, step TEXT, module TEXT,
                action TEXT, entity_id TEXT, entity_type TEXT,
                summary TEXT, changed_fields TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS synopses (
                novel_id TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT,
                one_liner TEXT, short_blurb TEXT, standard_blurb TEXT,
                long_blurb TEXT, core_conflict TEXT, world_highlight TEXT,
                selling_points TEXT, target_audience TEXT, tone_tags TEXT,
                comparison_titles TEXT, hook_question TEXT,
                word_count INTEGER, last_synced_at TEXT, stale_status TEXT,
                UNIQUE(novel_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS manuscripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, chapter_number INTEGER, title TEXT,
                compiled_constraint_file TEXT, scenes TEXT,
                word_count INTEGER, transition_fixes TEXT, status TEXT,
                UNIQUE(novel_id, chapter_number)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fix_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, chapter_number INTEGER, fix_type TEXT,
                issue_ref TEXT, original_summary TEXT,
                fixed_summary TEXT, timestamp TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, step_number INTEGER, module_name TEXT,
                level TEXT, score REAL, details TEXT,
                suggestions TEXT, created_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS step_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, step_number INTEGER, module_name TEXT,
                status TEXT, data TEXT, created_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS step_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, step_number INTEGER, step_name TEXT,
                status TEXT, UNIQUE(novel_id, step_number)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS purification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, processed_at TEXT,
                text_length INTEGER, issues_found INTEGER,
                auto_fixed INTEGER, report TEXT
            )
        """))
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()


def check_integrity() -> tuple[bool, str]:
    """对数据库执行完整性检查（PRAGMA integrity_check）。

    Returns:
        (is_ok, message): 检查通过返回 (True, "ok")，否则返回 (False, 错误详情)
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA integrity_check")).fetchone()
            if result and result[0] == "ok":
                return True, "ok"
            return False, str(result[0]) if result else "unknown"
    except Exception as e:
        return False, str(e)


def backup_database(backup_dir: str = "data/backups", max_daily: int = 7, max_weekly: int = 4) -> str | None:
    """使用 SQLite backup API 创建数据库备份。

    备份策略：
      - 每日备份：文件名格式 novel_YYYY-MM-DD.db
      - 每周一同时保留周备份：文件名格式 novel_weekly_YYYY-MM-DD.db
      - 自动清理超过保留数量的旧备份

    Args:
        backup_dir: 备份文件存储目录
        max_daily: 保留的最大每日备份数
        max_weekly: 保留的最大每周备份数

    Returns:
        成功返回备份文件路径，失败返回 None
    """
    import sqlite3
    import shutil
    from datetime import date

    db_path = Config.SQLITE_PATH
    if not os.path.exists(db_path):
        return None

    os.makedirs(backup_dir, exist_ok=True)

    today = date.today()
    daily_name = f"novel_{today.isoformat()}.db"
    daily_path = os.path.join(backup_dir, daily_name)

    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(daily_path)
        src.backup(dst)
        dst.close()
        src.close()
    except Exception:
        return None

    if today.weekday() == 0:
        weekly_name = f"novel_weekly_{today.isoformat()}.db"
        weekly_path = os.path.join(backup_dir, weekly_name)
        try:
            shutil.copy2(daily_path, weekly_path)
        except Exception:
            pass

    _cleanup_old_backups(backup_dir, "novel_", max_daily)
    _cleanup_old_backups(backup_dir, "novel_weekly_", max_weekly)

    return daily_path


def _cleanup_old_backups(backup_dir: str, prefix: str, max_keep: int) -> None:
    """清理旧备份文件，保留最近 max_keep 个。"""
    import glob as glob_mod
    pattern = os.path.join(backup_dir, f"{prefix}*.db")
    files = sorted(glob_mod.glob(pattern), reverse=True)
    for f in files[max_keep:]:
        try:
            os.remove(f)
        except Exception:
            pass


def create_session() -> Session:
    """创建并返回一个新的 Session（需手动关闭）"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()