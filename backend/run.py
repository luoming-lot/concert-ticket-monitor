"""
应用启动脚本
用法: python run.py
"""
import sys
from pathlib import Path

# 确保项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from app.config import settings
from app.utils.logger import log


def main():
    log.info(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    log.info(f"📍 后端地址: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    log.info(f"📖 API 文档: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}/docs")

    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
