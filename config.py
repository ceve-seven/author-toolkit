"""
向后兼容桥 — 原 from config import Config 继续可用。

所有配置定义已迁移至 src/config/settings.py。
新代码请直接导入：
    from src.config.settings import Config
"""

from src.config.settings import Config, _load_yaml_configs

__all__ = ["Config", "_load_yaml_configs"]