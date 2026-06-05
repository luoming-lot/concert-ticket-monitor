"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .utils.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    log.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    init_db()
    log.info("✅ 数据库初始化完成")
    yield
    # 关闭时
    log.info(f"🛑 {settings.APP_NAME} 正在关闭...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="演唱会票务监控系统 API",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.FRONTEND_PORT}",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "version": settings.APP_VERSION}


# 注册路由
from .routers.auth import router as auth_router
from .routers.concerts import router as concerts_router
from .routers.monitor import router as monitor_router
from .routers.settings_router import router as settings_api_router
from .routers.bot import router as bot_router

app.include_router(auth_router, prefix="/api/auth", tags=["认证"])
app.include_router(concerts_router, prefix="/api/concerts", tags=["演出管理"])
app.include_router(monitor_router, prefix="/api/monitor", tags=["监控管理"])
app.include_router(settings_api_router, prefix="/api/settings", tags=["系统配置"])
app.include_router(bot_router, prefix="/api/bot", tags=["抢票控制"])
