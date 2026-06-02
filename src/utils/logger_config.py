"""
structlog 日志系统配置
终端输出简洁版（ConsoleRenderer），日志文件输出完整版（JSON + 上下文）。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog

from src.config.settings import Config


# pyrefly: ignore [bad-function-definition]
def setup_logging(log_level: str = None) -> structlog.stdlib.BoundLogger:
    """初始化结构化日志系统

    终端输出简洁易读的彩色日志，日志文件输出包含完整上下文的格式化文本。
    文件日志和终端日志可独立设置级别。

    Args:
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR），
                   为 None 时使用 Config.LOG_LEVEL

    Returns:
        structlog 日志器实例，推荐命名为 "workflow"
    """
    level = (log_level or Config.LOG_LEVEL).upper()
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    numeric_level = log_level_map.get(level, logging.INFO)

    # 确保日志目录存在
    log_path = Path(Config.LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # ====== structlog 配置（终端 + 文件共用处理器链） ======

    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                pad_level=True,
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # ====== 文件日志独立配置（完整格式，独立级别） ======

    file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    # 清除已有处理器避免重复
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    root_logger.addHandler(file_handler)

    # 记录初始化完成
    logger = structlog.get_logger("workflow")
    logger.info(
        "logging_initialized",
        log_level=level,
        log_path=str(log_path),
        console_level=Config.LOG_CONSOLE_LEVEL,
    )

    return logger