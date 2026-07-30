"""
通知服务
多渠道通知：桌面通知、邮件、企业微信、钉钉
"""
import hashlib
import hmac
import base64
import time
import urllib.parse
import asyncio
from typing import Optional

import httpx
from ..config import settings
from ..utils.logger import log


class NotifierService:
    """多渠道通知服务"""

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def send_all(self, message: str, concert_name: str = ""):
        """通过所有已配置的渠道发送通知"""
        tasks = []

        # 桌面通知（总是可用）
        tasks.append(self.send_desktop(message))

        # 邮件通知
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            tasks.append(self.send_email(
                to=settings.SMTP_USER,
                subject=f"🎫 票务监控告警 - {concert_name}" if concert_name else "🎫 票务监控告警",
                body=message,
            ))

        # 企业微信
        if settings.WECOM_WEBHOOK_URL:
            tasks.append(self.send_wecom(message))

        # 钉钉
        if settings.DINGTALK_WEBHOOK_URL:
            tasks.append(self.send_dingtalk(message))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success = sum(1 for r in results if not isinstance(r, Exception))
            log.info(f"通知发送: {success}/{len(tasks)} 成功")
        else:
            log.warning("没有配置任何通知渠道")

    # ============ 桌面通知 ============

    async def send_desktop(self, message: str):
        """
        桌面通知 - 写入系统通知
        Windows: 使用 win10toast 或打印到控制台
        """
        try:
            # 尝试使用系统通知
            import platform
            system = platform.system()

            if system == "Windows":
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(
                        "🎫 演唱会票务监控",
                        message,
                        duration=5,
                        threaded=True,
                    )
                except ImportError:
                    # Fallback: 使用 ctypes 调用 Windows API
                    log.info(f"[桌面通知] {message}")

            elif system == "Darwin":  # macOS
                import subprocess
                subprocess.run([
                    "osascript", "-e",
                    f'display notification "{message[:200]}" with title "🎫 演唱会票务监控"'
                ], capture_output=True)

            else:  # Linux
                try:
                    import subprocess
                    subprocess.run(["notify-send", "🎫 演唱会票务监控", message[:200]], capture_output=True)
                except Exception:
                    pass

            log.info(f"桌面通知已发送: {message[:100]}...")

        except Exception as e:
            log.warning(f"桌面通知发送失败: {e}")

    # ============ 邮件通知 ============

    async def send_email(self, to: str, subject: str, body: str):
        """发送邮件通知"""
        if not settings.SMTP_USER:
            raise ValueError("SMTP 未配置")

        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
            msg["To"] = to
            msg["Subject"] = subject

            # HTML 格式邮件
            html_body = f"""
            <html>
            <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; border-radius: 8px; padding: 20px;">
                    <h2 style="color: #e74c3c;">🎫 演唱会票务监控告警</h2>
                    <div style="background: white; padding: 15px; border-radius: 4px; border-left: 4px solid #e74c3c;">
                        <pre style="white-space: pre-wrap; font-family: inherit; margin: 0;">{body}</pre>
                    </div>
                    <p style="color: #999; font-size: 12px; margin-top: 20px;">
                        此邮件由演唱会票务监控系统自动发送
                    </p>
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_body, "html", "utf-8"))

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=True,
            )

            log.info(f"邮件已发送: {to} - {subject}")

        except ImportError:
            log.warning("aiosmtplib 未安装，邮件通知不可用")
            raise
        except Exception as e:
            log.error(f"邮件发送失败: {e}")
            raise

    # ============ 企业微信通知 ============

    async def send_wecom(self, message: str):
        """发送企业微信机器人消息"""
        if not settings.WECOM_WEBHOOK_URL:
            raise ValueError("企业微信 Webhook 未配置")

        client = await self._get_client()

        payload = {
            "msgtype": "text",
            "text": {
                "content": f"🎫 演唱会票务监控\n\n{message}",
            },
        }

        try:
            resp = await client.post(settings.WECOM_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
            result = resp.json()
            if result.get("errcode") != 0:
                raise Exception(f"企业微信返回错误: {result.get('errmsg', 'unknown')}")
            log.info("企业微信通知已发送")
        except Exception as e:
            log.error(f"企业微信通知失败: {e}")
            raise

    # ============ 钉钉通知 ============

    async def send_dingtalk(self, message: str):
        """发送钉钉机器人消息"""
        if not settings.DINGTALK_WEBHOOK_URL:
            raise ValueError("钉钉 Webhook 未配置")

        webhook_url = settings.DINGTALK_WEBHOOK_URL

        # 如果配置了加签，生成签名参数
        if settings.DINGTALK_SECRET:
            timestamp = str(round(time.time() * 1000))
            secret = settings.DINGTALK_SECRET
            secret_enc = secret.encode("utf-8")
            string_to_sign = f"{timestamp}\n{secret}"
            string_to_sign_enc = string_to_sign.encode("utf-8")
            hmac_code = hmac.new(
                secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
            ).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

        client = await self._get_client()

        payload = {
            "msgtype": "text",
            "text": {
                "content": f"🎫 演唱会票务监控\n\n{message}",
            },
        }

        try:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            if result.get("errcode") != 0:
                raise Exception(f"钉钉返回错误: {result.get('errmsg', 'unknown')}")
            log.info("钉钉通知已发送")
        except Exception as e:
            log.error(f"钉钉通知失败: {e}")
            raise


# 全局单例
notifier_service = NotifierService()
