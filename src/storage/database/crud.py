from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.storage.database.models import Base

ModelT = TypeVar("ModelT", bound=Base)


def create_entity(db: Session, model: Type[ModelT], data_dict: Dict[str, Any]) -> ModelT:
    entity = model(**data_dict)
    db.add(entity)
    db.flush()
    return entity


def get_entity(db: Session, model: Type[ModelT], entity_id: Any) -> Optional[ModelT]:
    return db.get(model, entity_id)


def get_all(db: Session, model: Type[ModelT], novel_id: str) -> Sequence[ModelT]:
    # pyrefly: ignore [missing-attribute]
    stmt = select(model).where(model.novel_id == novel_id)
    return db.execute(stmt).scalars().all()


def update_entity(db: Session, model: Type[ModelT], entity_id: Any, data_dict: Dict[str, Any]) -> Optional[ModelT]:
    entity = db.get(model, entity_id)
    if entity is None:
        return None
    for key, value in data_dict.items():
        setattr(entity, key, value)
    db.flush()
    return entity


def delete_entity(db: Session, model: Type[ModelT], entity_id: Any) -> bool:
    entity = db.get(model, entity_id)
    if entity is None:
        return False
    db.delete(entity)
    db.flush()
    return True


def delete_by_novel(db: Session, model: Type[ModelT], novel_id: str) -> int:
    # pyrefly: ignore [missing-attribute]
    stmt = select(model).where(model.novel_id == novel_id)
    entities = db.execute(stmt).scalars().all()
    count = len(entities)
    for entity in entities:
        db.delete(entity)
    db.flush()
    return count


def bulk_create(db: Session, model: Type[ModelT], data_list: List[Dict[str, Any]]) -> List[ModelT]:
    entities = [model(**data) for data in data_list]
    db.add_all(entities)
    db.flush()
    return entities


def query(
    db: Session,
    model: Type[ModelT],
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Sequence[ModelT]:
    stmt = select(model)
    if filters:
        for key, value in filters.items():
            column = getattr(model, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
    if order_by:
        column = getattr(model, order_by, None)
        if column is not None:
            stmt = stmt.order_by(column)
    if offset is not None:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return db.execute(stmt).scalars().all()