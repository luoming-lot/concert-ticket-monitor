"""
演出管理路由 - CRUD + 数据采集
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Concert, Show, TicketTier, ConcertStatus, MonitorLog
from ..services.scraper import ScraperService
from ..utils.logger import log

router = APIRouter()


# ============ 请求/响应模型 ============

class ConcertCreate(BaseModel):
    name: str = Field(..., description="演出名称")
    url: str = Field(..., description="票务平台链接")
    venue: str = Field(default="", description="演出场馆")
    monitor_interval: int = Field(default=60, ge=10, le=3600, description="监控间隔(秒)")
    platform: str = Field(default="", description="平台标识")


class ConcertUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    venue: Optional[str] = None
    monitor_interval: Optional[int] = None
    status: Optional[str] = None


class ConcertListResponse(BaseModel):
    total: int
    items: List[dict]
    page: int
    page_size: int


# ============ 路由 ============

@router.get("")
async def list_concerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str = Query(default="", description="搜索关键词"),
    status: str = Query(default="", description="状态筛选"),
    db: Session = Depends(get_db),
):
    """获取演出列表"""
    query = db.query(Concert)

    if keyword:
        query = query.filter(Concert.name.contains(keyword))
    if status:
        query = query.filter(Concert.status == status)

    total = query.count()
    items = query.order_by(Concert.created_at.desc()) \
                 .offset((page - 1) * page_size) \
                 .limit(page_size) \
                 .all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.to_dict() for item in items],
    }


@router.get("/{concert_id}")
async def get_concert(concert_id: int, db: Session = Depends(get_db)):
    """获取演出详情（含场次和票档）"""
    concert = db.query(Concert).filter(Concert.id == concert_id).first()
    if not concert:
        raise HTTPException(status_code=404, detail="演出不存在")

    result = concert.to_dict()
    result["shows"] = []
    for show in concert.shows:
        show_dict = show.to_dict()
        show_dict["ticket_tiers"] = [t.to_dict() for t in show.ticket_tiers]
        result["shows"].append(show_dict)

    return result


@router.post("")
async def create_concert(data: ConcertCreate, db: Session = Depends(get_db)):
    """添加演出"""
    # 检查重复URL
    existing = db.query(Concert).filter(Concert.url == data.url).first()
    if existing:
        raise HTTPException(status_code=400, detail="该演出链接已存在")

    concert = Concert(
        name=data.name,
        url=data.url,
        venue=data.venue,
        monitor_interval=data.monitor_interval,
        platform=data.platform,
        status=ConcertStatus.MONITORING,
    )
    db.add(concert)
    db.commit()
    db.refresh(concert)

    log.info(f"添加演出: {concert.name} (ID: {concert.id})")
    return concert.to_dict()


@router.put("/{concert_id}")
async def update_concert(concert_id: int, data: ConcertUpdate, db: Session = Depends(get_db)):
    """更新演出信息"""
    concert = db.query(Concert).filter(Concert.id == concert_id).first()
    if not concert:
        raise HTTPException(status_code=404, detail="演出不存在")

    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = ConcertStatus(update_data["status"])

    for key, value in update_data.items():
        setattr(concert, key, value)

    db.commit()
    db.refresh(concert)
    log.info(f"更新演出: {concert.name} (ID: {concert.id})")
    return concert.to_dict()


@router.delete("/{concert_id}")
async def delete_concert(concert_id: int, db: Session = Depends(get_db)):
    """删除演出（级联删除场次和票档）"""
    concert = db.query(Concert).filter(Concert.id == concert_id).first()
    if not concert:
        raise HTTPException(status_code=404, detail="演出不存在")

    name = concert.name
    db.delete(concert)
    db.commit()
    log.info(f"删除演出: {name} (ID: {concert_id})")
    return {"message": f"已删除: {name}"}


@router.post("/{concert_id}/scrape")
async def scrape_concert(concert_id: int, db: Session = Depends(get_db)):
    """手动触发数据采集"""
    concert = db.query(Concert).filter(Concert.id == concert_id).first()
    if not concert:
        raise HTTPException(status_code=404, detail="演出不存在")

    try:
        scraper = ScraperService()
        result = await scraper.scrape_concert(concert)

        # 记录日志
        show_count = result.get('show_count', 0)
        log_entry = MonitorLog(
            concert_id=concert.id,
            level="success",
            message=f"采集完成: 获取 {show_count} 个场次",
        )
        db.add(log_entry)

        concert.last_check = datetime.now()
        db.commit()

        if show_count == 0:
            return {
                "success": True,
                "data": result,
                "warning": "未检测到场次信息，可能是页面结构特殊，请检查演出链接是否正确"
            }

        return {"success": True, "data": result}

    except Exception as e:
        error_msg = str(e)
        # 翻译常见错误为中文
        if "net::ERR_NAME_NOT_RESOLVED" in error_msg or "net::ERR_CONNECTION" in error_msg:
            detail = "无法访问目标网站，请检查网络连接或URL是否正确"
        elif "timeout" in error_msg.lower():
            detail = "页面加载超时，目标网站响应太慢或被防火墙拦截"
        elif "net::ERR_SSL" in error_msg or "certificate" in error_msg.lower():
            detail = "SSL证书验证失败，链接格式可能有误"
        elif "TargetClosedError" in error_msg or "Page crashed" in error_msg:
            detail = "浏览器页面崩溃，可能是目标网站内存占用过大"
        elif "net::ERR_BLOCKED_BY_CLIENT" in error_msg:
            detail = "请求被浏览器拦截，可能需要关闭广告拦截插件"
        elif "net::ERR_ABORTED" in error_msg:
            detail = "页面加载被中断，目标网站可能有反爬检测"
        elif "403" in error_msg or "Forbidden" in error_msg:
            detail = "目标网站拒绝访问(403)，可能需要添加Cookie或更换User-Agent"
        elif "Chrome" in error_msg or "chromium" in error_msg.lower() or "executable" in error_msg.lower():
            detail = "未找到Chrome浏览器。请安装 Google Chrome 或运行: playwright install chromium"
        else:
            detail = f"采集失败: {error_msg[:200]}"

        log.error(f"采集失败 (concert_id={concert_id}): {error_msg}")
        log_entry = MonitorLog(
            concert_id=concert.id,
            level="error",
            message=f"采集失败: {detail}",
        )
        db.add(log_entry)
        db.commit()
        raise HTTPException(status_code=500, detail=detail)


@router.get("/{concert_id}/logs")
async def get_concert_logs(
    concert_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取演出监控日志"""
    query = db.query(MonitorLog).filter(MonitorLog.concert_id == concert_id)
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
