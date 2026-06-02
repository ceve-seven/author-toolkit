from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseFixer(ABC):
    """修复器抽象基类——所有自动修复器必须继承此类"""

    @abstractmethod
    def fix(self, content: str, params: Optional[Dict[str, Any]] = None) -> str:
        """执行修复操作

        Args:
            content: 待修复的内容
            params: 修复参数

        Returns:
            修复后的内容
        """
        ...

    def get_fixer_id(self) -> str:
        """获取修复器标识"""
        return self.__class__.__name__

    def validate(self, content: str) -> bool:
        """验证内容是否需要修复

        Args:
            content: 待验证的内容

        Returns:
            是否需要修复
        """
        return True