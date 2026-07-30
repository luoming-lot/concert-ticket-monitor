"""
数据库管理模块
SQLAlchemy 引擎、会话、基类定义
"""
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

from .config import settings, get_db_path


# 确保数据目录存在
db_path = get_db_path()
db_path.parent.mkdir(parents=True, exist_ok=True)

# 创建引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=settings.DEBUG,
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 声明式基类
class Base(DeclarativeBase):
    pass


def get_db():
    """获取数据库会话（FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库：创建所有表
    在应用启动时调用
    """
    from .models.models import Concert, Show, TicketTier, MonitorLog, StatusHistory  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session():
    """获取独立的数据库会话（用于非请求上下文，如定时任务）"""
    return SessionLocal()
