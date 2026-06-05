"""
日志管理模块
基于 loguru 的日志配置
"""
import sys
from pathlib import Path
from loguru import logger

from ..config import settings, get_log_dir


def setup_logger():
    """配置日志系统"""
    # 移除默认 handler
    logger.remove()

    # 日志目录
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # 文件输出 - 普通日志
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level=settings.LOG_LEVEL,
        rotation="00:00",
        retention=f"{settings.LOG_MAX_DAYS} days",
        encoding="utf-8",
        enqueue=True,
    )

    # 文件输出 - 错误日志
    logger.add(
        log_dir / "error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",
        rotation="00:00",
        retention=f"{settings.LOG_MAX_DAYS} days",
        encoding="utf-8",
        enqueue=True,
    )

    # 文件输出 - 监控日志
    logger.add(
        log_dir / "monitor_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
        level="INFO",
        rotation="00:00",
        retention=f"{settings.LOG_MAX_DAYS} days",
        encoding="utf-8",
        enqueue=True,
        filter=lambda record: record["extra"].get("monitor", False),
    )

    return logger


# 创建 logger 实例
log = setup_logger()
