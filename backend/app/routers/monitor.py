"""
监控管理路由 - 启动/停止/状态/历史
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Concert, StatusHistory, MonitorLog
from ..services.monitor_service import MonitorService
from ..utils.logger import log

router = APIRouter()

# 全局监控服务实例
monitor_service = MonitorService()


class MonitorStartRequest(BaseModel):
    concert_id: int = Field(..., description="演出ID")


# ============ 路由 ============

@router.get("/status")
async def get_monitor_status():
    """获取全局监控状态"""
    return monitor_service.get_status()


@router.post("/start")
async def start_monitor(req: MonitorStartRequest, db: Session = Depends(get_db)):
    """启动指定演出的监控"""
    concert = db.query(Concert).filter(Concert.id == req.concert_id).first()
    if not concert:
        raise HTTPException(status_code=404, detail="演出不存在")

    result = monitor_service.start_monitor(concert)
    log.info(f"启动监控: {concert.name} (ID: {concert.id})")
    return result


@router.post("/start-all")
async def start_all_monitors(db: Session = Depends(get_db)):
    """启动所有监控中的演出"""
    concerts = db.query(Concert).filter(Concert.status == "monitoring").all()
    started = 0
    for concert in concerts:
        result = monitor_service.start_monitor(concert)
        if result.get("success"):
            started += 1

    log.info(f"批量启动监控: {started}/{len(concerts)}")
    return {"started": started, "total": len(concerts)}


@router.post("/stop/{concert_id}")
async def stop_monitor(concert_id: int, db: Session = Depends(get_db)):
    """停止指定演出的监控"""
    concert = db.query(Concert).filter(Concert.id == concert_id).first()
    if not concert:
        raise HTTPException(status_code=404, detail="演出不存在")

    result = monitor_service.stop_monitor(concert_id)
    log.info(f"停止监控: {concert.name} (ID: {concert.id})")
    return result


@router.post("/stop-all")
async def stop_all_monitors():
    """停止所有监控"""
    result = monitor_service.stop_all()
    log.info("停止所有监控")
    return result


@router.get("/history")
async def get_status_history(
    concert_id: Optional[int] = Query(default=None, description="演出ID筛选"),
    change_type: Optional[str] = Query(default=None, description="变更类型"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取状态变更历史"""
    from ..models.models import Show, TicketTier

    query = db.query(StatusHistory)

    if concert_id:
        # 通过 ticket_tier -> show 关联筛选
        query = query.join(TicketTier, StatusHistory.ticket_tier_id == TicketTier.id) \
                     .join(Show, TicketTier.show_id == Show.id) \
                     .filter(Show.concert_id == concert_id)

    if change_type:
        query = query.filter(StatusHistory.change_type == change_type)

    total = query.count()
    items = query.order_by(StatusHistory.created_at.desc()) \
                 .offset((page - 1) * page_size) \
                 .limit(page_size) \
                 .all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.to_dict() for item in items],
    }


@router.get("/logs")
async def get_all_logs(
    concert_id: Optional[int] = Query(default=None),
    level: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取所有监控日志"""
    query = db.query(MonitorLog)

    if concert_id:
        query = query.filter(MonitorLog.concert_id == concert_id)
    if level:
        query = query.filter(MonitorLog.level == level)

    total = query.count()
    items = query.order_by(MonitorLog.created_at.desc()) \
                 .offset((page - 1) * page_size) \
                 .limit(page_size) \
                 .all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.to_dict() for item in items],
    }
