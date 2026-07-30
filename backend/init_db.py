"""
数据库初始化脚本
独立运行：python init_db.py
"""
import sys
from pathlib import Path

# 确保项目路径在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import init_db, engine
from app.models.models import Base
from app.utils.logger import log


def main():
    log.info("开始初始化数据库...")

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 检查表是否创建成功
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    log.info(f"数据库初始化完成，共创建 {len(tables)} 张表:")
    for table in tables:
        log.info(f"  - {table}")

    # 插入默认配置
    from app.database import SessionLocal
    from app.models.models import SystemConfig

    db = SessionLocal()
    try:
        defaults = [
            ("monitor_interval", "60", "默认监控间隔(秒)"),
            ("browser_timeout", "30000", "浏览器超时(毫秒)"),
            ("headless", "true", "无头模式"),
        ]
        for key, value, desc in defaults:
            existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if not existing:
                db.add(SystemConfig(key=key, value=value, description=desc))

        db.commit()
        log.info("默认配置已插入")
    finally:
        db.close()


if __name__ == "__main__":
    main()
