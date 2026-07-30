"""
抢票控制 API
配置管理 + 一键启动/停止 + 实时状态
"""
import asyncio
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from ..services.damai_bot import (
    DamaiConfig, DamaiBot, get_bot, create_bot,
    load_config_from_file, save_config_to_file,
)
from ..utils.logger import log

router = APIRouter()


# ============ 请求模型 ============

class BotConfigRequest(BaseModel):
    target_url: str = Field(..., description="目标演出详情页 URL")
    users: List[str] = Field(default_factory=list, description="观演人姓名列表")
    index_url: str = Field(default="https://www.damai.cn/")
    login_url: str = Field(default="https://passport.damai.cn/login")
    city: str = Field(default="")
    dates: List[str] = Field(default_factory=list)
    prices: List[str] = Field(default_factory=list)
    fast_mode: bool = True
    if_listen: bool = True
    if_commit_order: bool = False
    max_retries: int = Field(default=1000, ge=1, le=100000)
    page_load_delay: float = Field(default=2.0, ge=0.5, le=30)


class BotStartRequest(BaseModel):
    headless: bool = True


# ============ API 路由 ============

@router.get("/config")
async def get_bot_config():
    """获取抢票配置"""
    config = load_config_from_file()
    return {"config": config.to_dict()}


@router.put("/config")
async def update_bot_config(data: BotConfigRequest):
    """保存抢票配置"""
    config = DamaiConfig.from_dict(data.model_dump())
    save_config_to_file(config)
    log.info("抢票配置已保存")
    return {"message": "配置已保存", "config": config.to_dict()}


@router.get("/status")
async def get_bot_status():
    """获取抢票引擎状态"""
    bot = get_bot()
    if bot is None:
        return {"running": False, "stage": "idle", "logs": []}
    return bot.get_status()


@router.post("/start")
async def start_bot(req: BotStartRequest = BotStartRequest()):
    """启动抢票引擎"""
    bot = get_bot()
    if bot and bot.running:
        raise HTTPException(status_code=400, detail="抢票引擎已在运行中")

    config = load_config_from_file()
    if not config.target_url:
        raise HTTPException(status_code=400, detail="请先配置目标演出URL")

    if not config.users:
        raise HTTPException(status_code=400, detail="请先配置观演人")

    bot = create_bot(config, headless=req.headless)

    # 在后台线程中运行（独立事件循环，避免和 uvicorn 冲突）
    import threading
    def _run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(bot.run())
        finally:
            loop.close()

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()

    log.info("抢票引擎已启动")
    return {
        "message": "抢票引擎已启动",
        "target_url": config.target_url,
        "users": config.users,
    }


@router.post("/stop")
async def stop_bot():
    """停止抢票引擎"""
    bot = get_bot()
    if bot is None or not bot.running:
        raise HTTPException(status_code=400, detail="抢票引擎未运行")

    bot.stop()
    log.info("抢票引擎已停止")
    return {"message": "抢票引擎已停止"}


@router.post("/stop-immediately")
async def stop_bot_immediately():
    """紧急停止抢票引擎"""
    bot = get_bot()
    if bot:
        bot.running = False
        bot._add_log("error", "紧急停止！")
    return {"message": "已发送停止信号"}
