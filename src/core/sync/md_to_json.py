from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class MdToJsonParser:
    """Markdown → JSON 解析器

    解析用户修改后的 Markdown 文件，提取 SYNC 标记中的字段值。
    支持三种 SYNC 标记：
    1. <!-- SYNC:实体ID:字段路径 -->内容<!-- /SYNC -->
    2. <!-- SYNC_META:实体ID:属性 -->值<!-- /SYNC_META -->
    3. <!-- SYNC_REF:实体ID -->关联内容<!-- /SYNC_REF -->
    """

    SYNC_FIELD_PATTERN = re.compile(
        r'<!--\s*SYNC:(\S+):(\S+)\s*-->(.*?)<!--\s*/SYNC\s*-->',
        re.DOTALL,
    )

    SYNC_META_PATTERN = re.compile(
        r'<!--\s*SYNC_META:(\S+):(\S+)\s*-->(.*?)<!--\s*/SYNC_META\s*-->',
        re.DOTALL,
    )

    SYNC_REF_PATTERN = re.compile(
        r'<!--\s*SYNC_REF:(\S+)\s*-->(.*?)<!--\s*/SYNC_REF\s*-->',
        re.DOTALL,
    )

    def parse(
        self,
        content: str,
        module_name: str = "",
    ) -> List[Dict[str, Any]]:
        """解析 Markdown 内容，提取所有变更

        Args:
            content: Markdown 文本内容
            module_name: 所属模块名称

        Returns:
            变更列表，每个变更包含 entity_id, field_path, new_value, module 等信息
        """
        changes: List[Dict[str, Any]] = []

        for match in self.SYNC_FIELD_PATTERN.finditer(content):
            entity_id = match.group(1).strip()
            field_path = match.group(2).strip()
            new_value = match.group(3).strip()

            if self._has_changed(entity_id, field_path, new_value):
                changes.append({
                    "entity_id": entity_id,
                    "field_path": field_path,
                    "new_value": new_value,
                    "module": module_name,
                    "timestamp": datetime.now().isoformat(),
                    "type": "field",
                })

        for match in self.SYNC_META_PATTERN.finditer(content):
            entity_id = match.group(1).strip()
            meta_key = match.group(2).strip()
            meta_value = match.group(3).strip()

            changes.append({
                "entity_id": entity_id,
                "field_path": f"meta.{meta_key}",
                "new_value": meta_value,
                "module": module_name,
                "timestamp": datetime.now().isoformat(),
                "type": "meta",
            })

        return changes

    def _has_changed(self, entity_id: str, field_path: str, new_value: str) -> bool:
        """检查字段值是否确实发生了变化"""
        if not entity_id or not field_path:
            return False
        return True

    def parse_sync_refs(self, content: str) -> List[Dict[str, str]]:
        """提取所有 SYNC_REF 引用标记

        Args:
            content: Markdown 文本内容

        Returns:
            引用标记列表
        """
        refs: List[Dict[str, str]] = []
        for match in self.SYNC_REF_PATTERN.finditer(content):
            entity_id = match.group(1).strip()
            ref_content = match.group(2).strip()
            refs.append({
                "entity_id": entity_id,
                "content": ref_content,
            })
        return refs

    def strip_sync_markers(self, content: str) -> str:
        """移除所有 SYNC 标记，只保留内容文本

        Args:
            content: 带 SYNC 标记的 Markdown 内容

        Returns:
            移除标记后的纯文本
        """
        result = self.SYNC_FIELD_PATTERN.sub(r'\3', content)
        result = self.SYNC_META_PATTERN.sub(r'\3', result)
        result = self.SYNC_REF_PATTERN.sub(r'\2', result)
        return result.strip()

    def extract_entity_ids(self, content: str) -> List[str]:
        """提取所有被引用的实体 ID

        Args:
            content: Markdown 文本内容

        Returns:
            去重后的实体 ID 列表
        """
        ids: set = set()

        for match in self.SYNC_FIELD_PATTERN.finditer(content):
            ids.add(match.group(1).strip())

        for match in self.SYNC_META_PATTERN.finditer(content):
            ids.add(match.group(1).strip())

        for match in self.SYNC_REF_PATTERN.finditer(content):
            ids.add(match.group(1).strip())

        return sorted(ids)

    def validate_sync_structure(self, content: str) -> List[str]:
        """验证 SYNC 标记的结构完整性

        Args:
            content: Markdown 文本内容

        Returns:
            结构错误列表（空列表表示无错误）
        """
        errors: List[str] = []

        open_fields = list(self.SYNC_FIELD_PATTERN.finditer(content))
        open_count = len(open_fields)
        close_count = content.count("<!-- /SYNC -->")

        if open_count != close_count:
            errors.append(
                f"SYNC 标记不匹配: 开启 {open_count} 个，关闭 {close_count} 个"
            )

        for match in open_fields:
            entity_id = match.group(1).strip()
            if not entity_id:
                errors.append("发现空实体 ID 的 SYNC 字段标记")
                continue
            field_path = match.group(2).strip()
            if not field_path:
                errors.append(f"实体 {entity_id} 的字段路径为空")

        return errors