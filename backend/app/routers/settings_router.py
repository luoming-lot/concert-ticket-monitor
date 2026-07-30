"""
系统配置路由 - 配置的读取/更新 + 通知测试
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import SystemConfig
from ..config import settings as app_settings
from ..services.notifier import NotifierService
from ..utils.logger import log

router = APIRouter()


# ============ 请求模型 ============

class SettingsUpdate(BaseModel):
    monitor_interval: Optional[int] = None
    browser_timeout: Optional[int] = None
    headless: Optional[bool] = None

    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None

    wecom_webhook: Optional[str] = None
    dingtalk_webhook: Optional[str] = None
    dingtalk_secret: Optional[str] = None


class TestEmailRequest(BaseModel):
    to: str
    subject: str = "测试邮件"
    body: str = "这是一封来自演唱会票务监控系统的测试邮件。"


class TestWebhookRequest(BaseModel):
    message: str = "🎫 演唱会票务监控系统 - 测试消息"


# ============ 路由 ============

@router.get("")
async def get_settings(db: Session = Depends(get_db)):
    """获取系统配置"""
    configs = db.query(SystemConfig).all()
    result = {c.key: c.value for c in configs}

    # 合并 .env 中的配置作为默认值
    defaults = {
        "monitor_interval": str(app_settings.DEFAULT_MONITOR_INTERVAL),
        "browser_timeout": str(app_settings.BROWSER_TIMEOUT),
        "headless": str(app_settings.HEADLESS).lower(),
        "smtp_host": app_settings.SMTP_HOST,
        "smtp_port": str(app_settings.SMTP_PORT),
        "smtp_user": app_settings.SMTP_USER,
        "wecom_webhook": app_settings.WECOM_WEBHOOK_URL,
        "dingtalk_webhook": app_settings.DINGTALK_WEBHOOK_URL,
        "dingtalk_secret": app_settings.DINGTALK_SECRET,
    }

    for key, default_value in defaults.items():
        if key not in result:
            result[key] = default_value

    return result


@router.put("")
async def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    """更新系统配置"""
    updates = data.model_dump(exclude_unset=True)

    for key, value in updates.items():
        if value is not None:
            # Upsert 配置
            config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if config:
                config.value = str(value)
            else:
                config = SystemConfig(key=key, value=str(value))
                db.add(config)

    db.commit()
    log.info(f"系统配置已更新: {list(updates.keys())}")
    return {"message": "配置已保存", "updated": list(updates.keys())}


@router.post("/test-email")
async def test_email(req: TestEmailRequest):
    """测试邮件发送"""
    notifier = NotifierService()
    try:
        await notifier.send_email(req.to, req.subject, req.body)
        return {"success": True, "message": f"测试邮件已发送至 {req.to}"}
    except Exception as e:
        log.error(f"测试邮件发送失败: {e}")
        raise HTTPException(status_code=500, detail=f"邮件发送失败: {str(e)}")


@router.post("/test-wecom")
async def test_wecom(req: TestWebhookRequest):
    """测试企业微信通知"""
    notifier = NotifierService()
    try:
        await notifier.send_wecom(req.message)
        return {"success": True, "message": "企业微信通知已发送"}
    except Exception as e:
        log.error(f"企业微信通知失败: {e}")
        raise HTTPException(status_code=500, detail=f"企业微信通知失败: {str(e)}")


@router.post("/test-dingtalk")
async def test_dingtalk(req: TestWebhookRequest):
    """测试钉钉通知"""
    notifier = NotifierService()
    try:
        await notifier.send_dingtalk(req.message)
        return {"success": True, "message": "钉钉通知已发送"}
    except Exception as e:
        log.error(f"钉钉通知失败: {e}")
        raise HTTPException(status_code=500, detail=f"钉钉通知失败: {str(e)}")
