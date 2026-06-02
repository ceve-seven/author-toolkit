"""
全局配置 — Agent-Native 模式
Agent 本身是 LLM，不需要外部 API Key，不需要启动任何外部服务。
所有数据存储在本地文件系统。

配置加载优先级：
  1. 默认值（本类中的硬编码）
  2. YAML 配置文件覆盖（src/config/ 目录下的 *.yaml）
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# pyrefly: ignore [missing-source-for-stubs]
import yaml


def _load_yaml_configs(config_dir: str = "src/config") -> Dict[str, Any]:
    """从 src/config/ 目录加载所有 YAML 配置文件，合并为一个字典。"""
    merged: Dict[str, Any] = {}
    config_path = Path(config_dir)
    if not config_path.exists() or not config_path.is_dir():
        return merged

    for yaml_file in sorted(config_path.glob("*.yaml")):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                merged.update(data)
        except Exception as e:
            print(f"  [config] 警告：加载配置文件 {yaml_file} 失败：{e}")

    return merged


class ConfigMeta(type):
    """元类：自动从 YAML 加载配置覆盖默认值。"""

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        cls = super().__new__(mcs, name, bases, namespace)

        overrides = _load_yaml_configs(getattr(cls, "CONFIG_DIR", "src/config"))

        for key, value in list(namespace.items()):
            if key.startswith("_") or callable(value):
                continue
            if key in overrides:
                setattr(cls, key, overrides[key])

        return cls


class Config(metaclass=ConfigMeta):
    """全局配置类。

    所有路径均为相对于项目根目录的相对路径。
    YAML 配置位于 src/config/ 目录，键名与类属性名一致即可覆盖。
    """

    CONFIG_DIR: str = "src/config"

    # ==================== 数据文件路径（全部本地） ====================

    DATA_DIR: str = "data"
    """数据根目录"""

    SQLITE_PATH: str = "data/novel.db"
    """SQLite 数据库文件路径"""

    CHROMADB_PATH: str = "data/chromadb"
    """ChromaDB 向量数据库持久化目录"""

    USER_VIEW_DIR: str = "output"
    """用户可视层 Markdown 文件根目录（生成的小说文件）"""

    SYSTEM_DATA_DIR: str = "system_data"
    """系统引擎层 JSON 数据根目录"""

    LOG_PATH: str = "logs/novel_creation.log"
    """结构化日志完整文件路径"""

    # ==================== 日志配置 ====================

    LOG_LEVEL: str = "INFO"
    """文件日志级别：DEBUG / INFO / WARNING / ERROR"""

    LOG_CONSOLE_LEVEL: str = "INFO"
    """终端日志级别（可独立于文件日志）"""

    # ==================== 质量保障配置 ====================

    QUALITY_AUTO_FIX_ENABLED: bool = True
    """是否启用质量自动修正"""

    AI_PURIFIER_ENABLED: bool = True
    """是否启用 AI 痕迹清除"""

    AI_PURIFIER_AUTO_FIX_LEVELS: List[int] | None = None
    """AI 痕迹自动清除等级：1=轻度, 2=中度, 3=深度"""

    MAX_USER_INPUT_LENGTH: int = 10 * 1024 * 1024
    """用户输入最大长度限制（字节），默认 10MB"""

    # ==================== 向量搜索配置 ====================

    FORESHADOW_DUPLICATE_THRESHOLD: float = 0.85
    """伏笔相似度检测阈值（0~1），高于此值判定为重复"""

    # ==================== 派生路径 ====================

    @classmethod
    def get_data_path(cls, *subpaths: str) -> str:
        """拼接 DATA_DIR 下的子路径，确保目录存在。"""
        path = os.path.join(cls.DATA_DIR, *subpaths)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    @classmethod
    def get_user_view_path(cls, novel_title: str, *subpaths: str) -> str:
        """拼接用户可视层路径（output/ 目录）。"""
        return os.path.join(cls.USER_VIEW_DIR, novel_title, *subpaths)

    @classmethod
    def get_system_data_path(cls, novel_title: str, *subpaths: str) -> str:
        """拼接系统数据层路径。"""
        return os.path.join(cls.SYSTEM_DATA_DIR, novel_title, *subpaths)

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """将配置导出为字典（用于日志记录等）。"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and not callable(getattr(cls, key))
        }


Config.AI_PURIFIER_AUTO_FIX_LEVELS = Config.AI_PURIFIER_AUTO_FIX_LEVELS or [1, 2]