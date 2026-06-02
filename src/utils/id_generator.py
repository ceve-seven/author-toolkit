"""
ID 生成器
按 novel_id + prefix 维护自增计数器，生成 CHAR-001、NOV-001 等格式的 ID。
计数器持久化到 SQLite 数据库的 id_counters 表。
"""

from __future__ import annotations

from typing import Dict, Tuple

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# 内存计数器缓存，避免重复查询
_counter_cache: Dict[Tuple[str, str], int] = {}

# 延迟初始化的 Session
_Base = declarative_base()


class IDCounter(_Base):
    """ID 计数器持久化表"""

    __tablename__ = "id_counters"

    novel_id = Column(String(32), primary_key=True)
    prefix = Column(String(16), primary_key=True)
    current_value = Column(Integer, nullable=False, default=0)


def _ensure_table(engine):
    """确保 ID 计数器表存在"""
    _Base.metadata.create_all(engine)


def generate_id(
    prefix: str,
    novel_id: str = "GLOBAL",
    db_session=None,
    engine=None,
) -> str:
    """生成格式化的自增 ID

    Args:
        prefix: ID 前缀，如 CHAR、NOV、FORE、LOC、RULE、FAC、REL、ARC、ITEM
        novel_id: 小说 ID，用于区分不同小说的计数器（默认 GLOBAL）
        db_session: SQLAlchemy 会话对象（提供 session 时优先使用）
        engine: SQLAlchemy 引擎（仅当 db_session 为 None 时使用）

    Returns:
        格式化的 ID 字符串，如 "CHAR-001"、"NOV-002"

    Examples:
        >>> generate_id("CHAR", "NOV-001", session)
        "CHAR-001"
        >>> generate_id("CHAR", "NOV-001", session)
        "CHAR-002"
    """
    cache_key = (novel_id, prefix)

    if db_session is not None:
        return _generate_with_session(prefix, novel_id, cache_key, db_session)
    elif engine is not None:
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            return _generate_with_session(prefix, novel_id, cache_key, session)
        finally:
            session.close()
    else:
        return _generate_with_cache(prefix, cache_key)


def _generate_with_session(
    prefix: str,
    novel_id: str,
    cache_key: Tuple[str, str],
    session,
) -> str:
    """通过数据库会话生成 ID"""
    _ensure_table(session.bind)

    counter = (
        session.query(IDCounter)
        .filter_by(novel_id=novel_id, prefix=prefix)
        .with_for_update()
        .first()
    )

    if counter is None:
        counter = IDCounter(
            novel_id=novel_id,
            prefix=prefix,
            current_value=1,
        )
        session.add(counter)
        next_value = 1
    else:
        counter.current_value += 1
        next_value = counter.current_value

    session.flush()

    _counter_cache[cache_key] = next_value

    return f"{prefix}-{next_value:03d}"


def _generate_with_cache(
    prefix: str,
    cache_key: Tuple[str, str],
) -> str:
    """通过内存缓存生成 ID（无数据库时使用）"""
    if cache_key in _counter_cache:
        _counter_cache[cache_key] += 1
    else:
        _counter_cache[cache_key] = 1

    next_value = _counter_cache[cache_key]
    return f"{prefix}-{next_value:03d}"


def peek_next_id(
    prefix: str,
    novel_id: str = "GLOBAL",
    db_session=None,
) -> str:
    """查看下一个 ID 而不自增

    Args:
        prefix: ID 前缀
        novel_id: 小说 ID
        db_session: SQLAlchemy 会话对象

    Returns:
        下一个 ID 的格式字符串
    """
    cache_key = (novel_id, prefix)

    if cache_key in _counter_cache:
        next_value = _counter_cache[cache_key] + 1
    elif db_session is not None:
        counter = (
            db_session.query(IDCounter)
            .filter_by(novel_id=novel_id, prefix=prefix)
            .first()
        )
        next_value = (counter.current_value + 1) if counter else 1
        _counter_cache[cache_key] = next_value - 1
    else:
        next_value = 1

    return f"{prefix}-{next_value:03d}"


def reset_counter(
    prefix: str,
    novel_id: str = "GLOBAL",
    db_session=None,
):
    """重置指定小说的计数器

    Args:
        prefix: ID 前缀
        novel_id: 小说 ID
        db_session: SQLAlchemy 会话对象
    """
    cache_key = (novel_id, prefix)
    _counter_cache.pop(cache_key, None)

    if db_session is not None:
        db_session.query(IDCounter).filter_by(
            novel_id=novel_id, prefix=prefix
        ).delete()
        db_session.flush()