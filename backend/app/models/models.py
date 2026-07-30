"""
数据库模型定义
Concert → Show → TicketTier 三级关联
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from ..database import Base


# ============ 枚举类型 ============

class ConcertStatus(str, enum.Enum):
    MONITORING = "monitoring"
    PAUSED = "paused"
    ENDED = "ended"


class TicketStatus(str, enum.Enum):
    AVAILABLE = "available"       # 有票
    SOLD_OUT = "sold_out"        # 售罄
    PENDING = "pending"          # 未开售
    UNKNOWN = "unknown"          # 未知


class MonitorStatus(str, enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class ChangeType(str, enum.Enum):
    STOCK = "stock"       # 库存变化
    PRICE = "price"       # 价格变化
    OPEN = "open"         # 开售
    SOLD_OUT = "sold_out" # 售罄


# ============ 数据模型 ============

class Concert(Base):
    """演出信息"""
    __tablename__ = "concerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="演出名称")
    url = Column(String(1024), nullable=False, comment="票务平台链接")
    venue = Column(String(255), default="", comment="演出场馆")
    cover_image = Column(String(1024), default="", comment="封面图URL")
    description = Column(Text, default="", comment="演出描述")

    status = Column(
        SAEnum(ConcertStatus),
        default=ConcertStatus.MONITORING,
        comment="监控状态"
    )
    monitor_interval = Column(Integer, default=60, comment="监控间隔(秒)")

    # 元数据
    platform = Column(String(50), default="", comment="平台标识")
    raw_data = Column(Text, default="", comment="原始JSON数据")

    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    last_check = Column(DateTime, nullable=True, comment="最后检测时间")

    # 关联
    shows = relationship("Show", back_populates="concert", cascade="all, delete-orphan")
    monitor_logs = relationship("MonitorLog", back_populates="concert", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "venue": self.venue,
            "cover_image": self.cover_image,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "monitor_interval": self.monitor_interval,
            "platform": self.platform,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_check": self.last_check.isoformat() if self.last_check else None,
        }


class Show(Base):
    """场次信息"""
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concert_id = Column(Integer, ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False, comment="场次名称")
    show_time = Column(DateTime, nullable=True, comment="演出时间")
    sale_start_time = Column(DateTime, nullable=True, comment="开售时间")
    venue = Column(String(255), default="", comment="场馆")

    # 原始标识
    show_id_platform = Column(String(100), default="", comment="平台场次ID")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    concert = relationship("Concert", back_populates="shows")
    ticket_tiers = relationship("TicketTier", back_populates="show", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "concert_id": self.concert_id,
            "name": self.name,
            "show_time": self.show_time.isoformat() if self.show_time else None,
            "sale_start_time": self.sale_start_time.isoformat() if self.sale_start_time else None,
            "venue": self.venue,
            "show_id_platform": self.show_id_platform,
        }


class TicketTier(Base):
    """票档信息"""
    __tablename__ = "ticket_tiers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False, comment="票档名称")
    price = Column(Float, default=0.0, comment="票价")
    face_value = Column(Float, default=0.0, comment="面值")

    status = Column(
        SAEnum(TicketStatus),
        default=TicketStatus.UNKNOWN,
        comment="票档状态"
    )
    stock_count = Column(Integer, default=-1, comment="库存数量(-1未知)")

    # 平台原始ID
    tier_id_platform = Column(String(100), default="", comment="平台票档ID")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    show = relationship("Show", back_populates="ticket_tiers")
    status_histories = relationship("StatusHistory", back_populates="ticket_tier", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "show_id": self.show_id,
            "name": self.name,
            "price": self.price,
            "face_value": self.face_value,
            "status": self.status.value if self.status else None,
            "stock_count": self.stock_count,
            "tier_id_platform": self.tier_id_platform,
        }


class StatusHistory(Base):
    """票档状态变更历史"""
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_tier_id = Column(Integer, ForeignKey("ticket_tiers.id", ondelete="CASCADE"), nullable=False)

    old_status = Column(String(50), default="", comment="旧状态")
    new_status = Column(String(50), default="", comment="新状态")
    old_stock = Column(Integer, default=-1, comment="旧库存")
    new_stock = Column(Integer, default=-1, comment="新库存")
    old_price = Column(Float, default=0.0, comment="旧价格")
    new_price = Column(Float, default=0.0, comment="新价格")

    change_type = Column(SAEnum(ChangeType), default=ChangeType.STOCK, comment="变更类型")
    message = Column(String(500), default="", comment="变更描述")

    created_at = Column(DateTime, default=datetime.now, comment="记录时间")

    # 关联
    ticket_tier = relationship("TicketTier", back_populates="status_histories")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_tier_id": self.ticket_tier_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "old_stock": self.old_stock,
            "new_stock": self.new_stock,
            "old_price": self.old_price,
            "new_price": self.new_price,
            "change_type": self.change_type.value if self.change_type else None,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MonitorLog(Base):
    """监控执行日志"""
    __tablename__ = "monitor_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concert_id = Column(Integer, ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False)

    level = Column(SAEnum(LogLevel), default=LogLevel.INFO, comment="日志级别")
    message = Column(Text, default="", comment="日志内容")
    detail = Column(Text, default="", comment="详细信息(JSON)")

    created_at = Column(DateTime, default=datetime.now, comment="记录时间")

    # 关联
    concert = relationship("Concert", back_populates="monitor_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "concert_id": self.concert_id,
            "level": self.level.value if self.level else None,
            "message": self.message,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemConfig(Base):
    """系统配置键值存储"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, comment="配置键")
    value = Column(Text, default="", comment="配置值")
    description = Column(String(255), default="", comment="配置说明")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
