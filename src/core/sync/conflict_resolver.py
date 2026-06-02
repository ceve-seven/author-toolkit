from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class ConflictResolver:
    """冲突解决器

    检测双向同步中的冲突，提供自动合并策略。

    冲突场景：
    - 用户修改了 Markdown，但系统也修改了同一字段（MD 时间 > DB 时间）
    - 系统和用户同时修改（DB 时间 > MD 时间）
    - 时间戳相同或无法判断
    - 用户删除了 SYNC 标记
    """

    def __init__(self, default_strategy: str = "last_write_wins"):
        self.default_strategy = default_strategy

    def resolve(
        self,
        old_value: Any,
        new_value: Any,
        entity_id: str = "",
        field_path: str = "",
        db_timestamp: Optional[str] = None,
        md_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """解决单个字段的冲突

        Args:
            old_value: 数据库中的旧值
            new_value: Markdown 中的新值
            entity_id: 实体 ID
            field_path: 字段路径
            db_timestamp: 数据库最后修改时间
            md_timestamp: Markdown 最后修改时间

        Returns:
            冲突解决结果，包含 strategy（策略）和 resolved_value（解决后的值）
        """
        if old_value == new_value:
            return {
                "strategy": "no_conflict",
                "resolved_value": new_value,
                "entity_id": entity_id,
                "field_path": field_path,
                "description": "无冲突，值相同",
            }

        dt_db = self._parse_timestamp(db_timestamp)
        dt_md = self._parse_timestamp(md_timestamp)

        if dt_db is not None and dt_md is not None:
            if dt_md > dt_db:
                return {
                    "strategy": "use_new",
                    "resolved_value": new_value,
                    "entity_id": entity_id,
                    "field_path": field_path,
                    "description": "用户手动修改优先（Markdown 时间更新）",
                }
            elif dt_db > dt_md:
                return {
                    "strategy": "use_old",
                    "resolved_value": old_value,
                    "entity_id": entity_id,
                    "field_path": field_path,
                    "description": "系统修改优先（数据库时间更新）",
                }

        return {
            "strategy": self.default_strategy,
            "resolved_value": new_value if self.default_strategy == "last_write_wins" else old_value,
            "entity_id": entity_id,
            "field_path": field_path,
            "description": f"按默认策略「{self.default_strategy}」解决",
        }

    def batch_resolve(
        self,
        conflicts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """批量解决冲突

        Args:
            conflicts: 冲突列表，每个元素包含 old_value, new_value, entity_id, field_path 等

        Returns:
            解决后的结果列表
        """
        resolved: List[Dict[str, Any]] = []
        for conflict in conflicts:
            result = self.resolve(
                old_value=conflict.get("old_value"),
                new_value=conflict.get("new_value"),
                entity_id=conflict.get("entity_id", ""),
                field_path=conflict.get("field_path", ""),
                db_timestamp=conflict.get("db_timestamp"),
                md_timestamp=conflict.get("md_timestamp"),
            )
            resolved.append(result)
        return resolved

    def detect_conflicts(
        self,
        db_data: Dict[str, Any],
        md_changes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """检测数据库数据和 Markdown 变更之间的冲突

        Args:
            db_data: 数据库中的当前数据
            md_changes: Markdown 解析出的变更列表

        Returns:
            检测到的冲突列表
        """
        conflicts: List[Dict[str, Any]] = []

        for change in md_changes:
            entity_id = change.get("entity_id", "")
            field_path = change.get("field_path", "")
            new_value = change.get("new_value")

            db_value = self._get_nested_value(db_data, entity_id, field_path)

            if db_value is not None and str(db_value) != str(new_value):
                conflicts.append({
                    "old_value": db_value,
                    "new_value": new_value,
                    "entity_id": entity_id,
                    "field_path": field_path,
                    "db_timestamp": change.get("timestamp"),
                    "md_timestamp": datetime.now().isoformat(),
                })

        return conflicts

    def _get_nested_value(
        self,
        data: Dict[str, Any],
        entity_id: str,
        field_path: str,
    ) -> Optional[Any]:
        """从嵌套字典中获取值

        Args:
            data: 数据集
            entity_id: 实体 ID
            field_path: 字段路径（支持点号分隔）

        Returns:
            字段值，未找到时返回 None
        """
        if entity_id in data and isinstance(data[entity_id], dict):
            current = data[entity_id]
            parts = field_path.split(".")
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current

        for key, value in data.items():
            if isinstance(value, dict) and value.get("id") == entity_id:
                current = value
                parts = field_path.split(".")
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None
                return current

        return None

    def _parse_timestamp(self, timestamp: Optional[str]) -> Optional[datetime]:
        """解析时间戳字符串"""
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp)
        except (ValueError, TypeError):
            return None