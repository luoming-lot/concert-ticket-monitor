"""
应用配置管理模块
从 .env 文件和环境变量加载配置
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载 .env 文件（本地开发用，Vercel 上不存在也没关系）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = BASE_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)

# Vercel serverless 环境检测
_IS_VERCEL = bool(os.getenv("VERCEL"))

# Vercel 上数据库用 /tmp（唯一可写目录）
if _IS_VERCEL:
    _DEFAULT_DB = "sqlite:////tmp/concert_monitor.db"
else:
    _DEFAULT_DB = "sqlite:///./data/concert_monitor.db"


class Settings(BaseSettings):
    """应用全局配置"""

    # --- 应用 ---
    APP_NAME: str = "ConcertTicketMonitor"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-random-string-at-least-32-chars"

    # --- 数据库 ---
    DATABASE_URL: str = _DEFAULT_DB

    # --- 监控 ---
    DEFAULT_MONITOR_INTERVAL: int = 60
    MIN_MONITOR_INTERVAL: int = 10

    # --- Playwright ---
    HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30000
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # --- SMTP 邮件 ---
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # --- 企业微信 ---
    WECOM_WEBHOOK_URL: str = ""

    # --- 钉钉 ---
    DINGTALK_WEBHOOK_URL: str = ""
    DINGTALK_SECRET: str = ""

    # --- 服务 ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 5173

    # --- 日志 ---
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    LOG_MAX_DAYS: int = 30

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局单例
settings = Settings()


def get_db_path() -> Path:
    """获取数据库文件绝对路径"""
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        relative_path = db_url.replace("sqlite:///", "", 1)
        if not Path(relative_path).is_absolute():
            return (BASE_DIR / relative_path).resolve()
        return Path(relative_path).resolve()
    return Path(relative_path)


def get_log_dir() -> Path:
    """获取日志目录绝对路径"""
    log_dir = Path(settings.LOG_DIR)
    if not log_dir.is_absolute():
        return (BASE_DIR / log_dir).resolve()
    return log_dir.resolve()
