"""
监控调度服务
基于 APScheduler 的定时监控管理
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..database import get_session
from ..models.models import Concert, MonitorLog, LogLevel, ConcertStatus
from ..services.scraper import ScraperService
from ..services.notifier import NotifierService
from ..utils.logger import log


class MonitorService:
    """监控任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs: Dict[int, str] = {}  # concert_id -> job_id
        self._running = False
        self._start_time: Optional[datetime] = None
        self.scraper = ScraperService()
        self.notifier = NotifierService()

    def _start_scheduler(self):
        """启动调度器（如果未启动）"""
        if not self._running:
            self.scheduler.start()
            self._running = True
            self._start_time = datetime.now()
            log.info("监控调度器已启动")

    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            "running": self._running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "active_jobs": len(self._jobs),
            "job_list": list(self._jobs.keys()),
        }

    def start_monitor(self, concert: Concert) -> Dict[str, Any]:
        """启动单个演出的监控"""
        self._start_scheduler()

        # 如果已有监控任务，先移除
        if concert.id in self._jobs:
            self.stop_monitor(concert.id)

        interval = concert.monitor_interval or 60

        # 添加定时任务
        job = self.scheduler.add_job(
            self._monitor_job,
            trigger=IntervalTrigger(seconds=interval),
            args=[concert.id],
            id=f"concert_{concert.id}",
            name=f"监控: {concert.name}",
            replace_existing=True,
            misfire_grace_time=30,
        )

        self._jobs[concert.id] = job.id

        # 更新演出状态
        db = get_session()
        try:
            concert_obj = db.query(Concert).filter(Concert.id == concert.id).first()
            if concert_obj:
                concert_obj.status = ConcertStatus.MONITORING
                db.commit()
        finally:
            db.close()

        log.info(f"已添加监控任务: {concert.name} (每{interval}秒)")
        return {
            "success": True,
            "concert_id": concert.id,
            "concert_name": concert.name,
            "interval": interval,
            "job_id": job.id,
        }

    def stop_monitor(self, concert_id: int) -> Dict[str, Any]:
        """停止单个演出的监控"""
        job_id = self._jobs.pop(concert_id, None)
        if job_id and self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            log.info(f"已移除监控任务: concert_id={concert_id}")

            db = get_session()
            try:
                concert = db.query(Concert).filter(Concert.id == concert_id).first()
                if concert:
                    concert.status = ConcertStatus.PAUSED
                    db.commit()
            finally:
                db.close()

        return {"success": True, "concert_id": concert_id}

    def stop_all(self) -> Dict[str, Any]:
        """停止所有监控"""
        count = len(self._jobs)
        for concert_id in list(self._jobs.keys()):
            self.stop_monitor(concert_id)

        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False

        log.info(f"已停止所有监控任务 ({count}个)")
        return {"success": True, "stopped": count}

    async def _monitor_job(self, concert_id: int):
        """监控任务执行体 - 由调度器调用"""
        db = get_session()
        try:
            concert = db.query(Concert).filter(Concert.id == concert_id).first()
            if not concert:
                log.warning(f"监控任务: 演出 {concert_id} 不存在，移除任务")
                self.stop_monitor(concert_id)
                return

            log.bind(monitor=True).info(f"执行监控: {concert.name}")

            # 执行数据采集
            try:
                result = await self.scraper.scrape_concert(concert)

                # 记录日志
                log_entry = MonitorLog(
                    concert_id=concert.id,
                    level=LogLevel.INFO,
                    message=f"定时采集完成: 获取 {result.get('show_count', 0)} 个场次",
                )
                db.add(log_entry)

                # 检查是否有票档状态变更
                self._check_changes_and_notify(db, concert, result)

                concert.last_check = datetime.now()
                db.commit()

            except Exception as e:
                log.error(f"定时采集失败 [{concert.name}]: {e}")
                log_entry = MonitorLog(
                    concert_id=concert.id,
                    level=LogLevel.ERROR,
                    message=f"采集失败: {str(e)}",
                )
                db.add(log_entry)
                db.commit()

        finally:
            db.close()

    def _check_changes_and_notify(self, db, concert: Concert, result: Dict):
        """检查变更并发送通知"""
        from ..models.models import StatusHistory

        # 查询最近5分钟的变更记录
        since = datetime.now()
        # 简化：获取最近新增的状态变更
        recent_changes = db.query(StatusHistory).filter(
            StatusHistory.created_at >= concert.last_check or concert.last_check is None
        ).all() if concert.last_check else []

        if recent_changes:
            # 构建通知消息
            change_msgs = []
            for change in recent_changes[:10]:  # 最多10条
                msg = f"🎫 {change.message}"
                change_msgs.append(msg)

            if change_msgs:
                notification = (
                    f"📢 演出「{concert.name}」检测到票务变化:\n\n"
                    + "\n".join(change_msgs)
                )

                # 异步发送通知
                asyncio.ensure_future(self.notifier.send_all(notification))
