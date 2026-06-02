"""database engine 模块单元测试"""
import os
import tempfile
from pathlib import Path

from sqlalchemy import text

from src.storage.database.engine import (
    backup_database,
    check_integrity,
    create_session,
    get_engine,
    init_schema,
    reset_engine,
)


class TestDatabaseEngine:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        from src.config.settings import Config
        self._orig_path = Config.SQLITE_PATH
        Config.SQLITE_PATH = os.path.join(self.tmp_dir, "test_unit.db")
        reset_engine()

    def teardown_method(self):
        from src.config.settings import Config
        Config.SQLITE_PATH = self._orig_path
        reset_engine()
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_init_schema_creates_tables(self):
        init_schema()
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
        assert "novels" in tables
        assert "characters" in tables
        assert "themes" in tables
        assert "step_status" in tables

    def test_init_schema_idempotent(self):
        init_schema()
        init_schema()
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
        assert "novels" in tables

    def test_create_session(self):
        init_schema()
        session = create_session()
        try:
            session.execute(text("SELECT 1"))
        finally:
            session.close()

    def test_check_integrity_ok(self):
        init_schema()
        ok, msg = check_integrity()
        assert ok is True
        assert msg == "ok"

    def test_backup_database(self):
        init_schema()
        backup_dir = os.path.join(self.tmp_dir, "backups")
        result = backup_database(backup_dir=backup_dir)
        assert result is not None
        assert os.path.exists(result)

    def test_backup_database_no_db_file(self):
        from src.config.settings import Config
        Config.SQLITE_PATH = os.path.join(self.tmp_dir, "nonexistent.db")
        reset_engine()
        result = backup_database(backup_dir=os.path.join(self.tmp_dir, "bk"))
        assert result is None

    def test_wal_mode_enabled(self):
        init_schema()
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).fetchone()
        assert result[0] in ("wal",)

    def test_foreign_keys_enabled(self):
        init_schema()
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
        assert result[0] in (1, "1")
