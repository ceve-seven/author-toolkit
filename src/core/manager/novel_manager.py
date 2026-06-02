from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text

from src.config.settings import Config
from src.utils import validate_table_name
from src.utils.id_generator import generate_id


@dataclass
class NovelInfo:
    """小说信息"""
    id: str
    title: str
    current_step: int
    status: str
    created_at: str
    updated_at: str
    step_name: str = ""
    chapter_count: int = 0
    character_count: int = 0


STEP_NAMES: List[str] = [
    "灵感启动", "小说主题", "世界观设定", "人物设定",
    "势力设定", "物品库", "人物关系", "势力关系", "人物-势力关联", "角色弧线",
    "伏笔追踪", "拟定大纲", "分卷配置", "章节细纲",
    "小说档案", "小说简介", "正文初稿",
    "正文审核", "正文修正", "导出发布",
]


class NovelManager:
    """小说项目管理器

    提供小说项目的 CRUD 操作：创建、列表、查询、删除、统计。
    """

    def __init__(self, db_session: Any):
        self.db = db_session
        self.logger = structlog.get_logger("novel_manager")

    def list_novels(self) -> List[NovelInfo]:
        """列出所有小说"""
        try:
            rows = self.db.execute(
                text("SELECT id, title, current_step, status, created_at, updated_at FROM novels ORDER BY updated_at DESC")
            ).fetchall()
            novels = []
            for row in rows:
                novel = NovelInfo(
                    id=row[0], title=row[1], current_step=row[2] or 1,
                    status=row[3] or "创作中", created_at=row[4] or "",
                    updated_at=row[5] or "",
                )
                novel.step_name = STEP_NAMES[novel.current_step - 1] if 1 <= novel.current_step <= len(STEP_NAMES) else "未知"
                novel.chapter_count = self._count_chapters(novel.id)
                novel.character_count = self._count_characters(novel.id)
                novels.append(novel)
            return novels
        except Exception as e:
            self.logger.warning("list_novels_error", error=str(e))
            return []

    def create_novel(self, title: str, author: str = "") -> Optional[str]:
        """创建新小说，返回 novel_id"""
        novel_id = generate_id("NOV", "GLOBAL", self.db)
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.db.execute(
                text("INSERT INTO novels (id, title, author, current_step, status, created_at, updated_at) "
                     "VALUES (:id, :title, :author, 1, '创作中', :now, :now)"),
                {"id": novel_id, "title": title, "author": author, "now": now},
            )
            self.db.commit()
            self.logger.info("novel_created", novel_id=novel_id, title=title)
            return novel_id
        except Exception as e:
            self.logger.error("create_novel_error", title=title, error=str(e))
            self.db.rollback()
            return None

    def get_novel(self, novel_id: str) -> Optional[NovelInfo]:
        """获取小说信息"""
        try:
            row = self.db.execute(
                text("SELECT id, title, current_step, status, created_at, updated_at FROM novels WHERE id = :novel_id"),
                {"novel_id": novel_id},
            ).fetchone()
            if row is None:
                return None
            novel = NovelInfo(
                id=row[0], title=row[1], current_step=row[2] or 1,
                status=row[3] or "创作中", created_at=row[4] or "",
                updated_at=row[5] or "",
            )
            novel.step_name = STEP_NAMES[novel.current_step - 1] if 1 <= novel.current_step <= len(STEP_NAMES) else "未知"
            novel.chapter_count = self._count_chapters(novel.id)
            novel.character_count = self._count_characters(novel.id)
            return novel
        except Exception as e:
            self.logger.warning("get_novel_error", novel_id=novel_id, error=str(e))
            return None

    def delete_novel(self, novel_id: str) -> bool:
        """删除小说及所有相关数据（级联删除 + 清理输出目录）"""
        novel = self.get_novel(novel_id)
        if novel is None:
            return False

        try:
            self.db.execute(
                text("DELETE FROM novels WHERE id = :novel_id"),
                {"novel_id": novel_id},
            )
            self.db.commit()
            self.logger.info("novel_deleted", novel_id=novel_id, title=novel.title)
        except Exception as e:
            self.logger.error("delete_novel_db_error", novel_id=novel_id, error=str(e))
            self.db.rollback()
            return False

        self._cleanup_output_dirs(novel)
        return True

    def get_novel_stats(self, novel_id: str) -> Dict[str, Any]:
        """获取小说统计数据"""
        stats: Dict[str, Any] = {
            "chapters": 0, "characters": 0, "world_rules": 0,
            "factions": 0, "items": 0, "foreshadows": 0,
            "outlines": 0, "manuscripts": 0,
        }
        try:
            for key, table in [
                ("chapters", "volume_chapters"), ("characters", "characters"),
                ("world_rules", "world_rules"), ("factions", "factions"),
                ("items", "items"), ("foreshadows", "foreshadows"),
                ("outlines", "outlines"), ("manuscripts", "manuscripts"),
            ]:
                row = self.db.execute(
                    text(f"SELECT COUNT(1) FROM {validate_table_name(table)} WHERE novel_id = :novel_id"),
                    {"novel_id": novel_id},
                ).fetchone()
                stats[key] = row[0] if row else 0
        except Exception as e:
            self.logger.warning("get_novel_stats_error", novel_id=novel_id, error=str(e))
        return stats

    def _count_chapters(self, novel_id: str) -> int:
        try:
            row = self.db.execute(
                text("SELECT COUNT(1) FROM manuscripts WHERE novel_id = :novel_id"),
                {"novel_id": novel_id},
            ).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def _count_characters(self, novel_id: str) -> int:
        try:
            row = self.db.execute(
                text("SELECT COUNT(1) FROM characters WHERE novel_id = :novel_id"),
                {"novel_id": novel_id},
            ).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def _cleanup_output_dirs(self, novel: NovelInfo):
        title_tag = novel.title
        id_tag = novel.id

        for base_dir_str in [Config.USER_VIEW_DIR, Config.SYSTEM_DATA_DIR]:
            base_dir = Path(base_dir_str)
            if not base_dir.exists():
                continue
            for candidate in [base_dir / title_tag, base_dir / id_tag]:
                if candidate.exists():
                    try:
                        import shutil
                        shutil.rmtree(candidate)
                        self.logger.info("output_dir_cleaned", path=str(candidate))
                    except Exception as e:
                        self.logger.warning("cleanup_output_error", path=str(candidate), error=str(e))