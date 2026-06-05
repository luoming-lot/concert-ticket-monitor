"""
大麦网自动抢票引擎
基于 Playwright 实现的大麦网全流程自动化
参考: ticket-purchase 项目的 Selenium 方案，改用 Playwright + 本机 Chrome
"""
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

from ..utils.logger import log
from ..config import settings as app_settings


# ============================================================
# 配置数据结构
# ============================================================

@dataclass
class DamaiConfig:
    """大麦网抢票配置"""
    # 必填
    target_url: str = ""                           # 目标演出详情页 URL
    users: List[str] = field(default_factory=list) # 观演人姓名列表

    # 可选
    index_url: str = "https://www.damai.cn/"       # 大麦首页
    login_url: str = "https://passport.damai.cn/login"
    city: str = ""                                  # 演出城市
    dates: List[str] = field(default_factory=list) # 场次日期 (支持多种格式)
    prices: List[str] = field(default_factory=list)# 票价 (支持多种格式)

    # 功能开关
    fast_mode: bool = True                         # 快速模式 (减少等待时间)
    if_listen: bool = True                         # 监听缺货登记回流
    if_commit_order: bool = False                  # 是否自动提交订单
    max_retries: int = 1000                        # 最大重试次数
    page_load_delay: float = 2.0                   # 页面加载等待 (秒)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DamaiConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# 默认配置文件路径
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "damai_config.json"


# ============================================================
# 抢票引擎
# ============================================================

class DamaiBot:
    """大麦网自动抢票引擎"""

    def __init__(self, config: DamaiConfig, headless: bool = False):
        self.config = config
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None
        self._context = None

        # 运行时状态
        self.running = False
        self.stage = "idle"          # 当前阶段
        self.start_time: Optional[datetime] = None
        self.retry_count = 0
        self.logs: List[Dict] = []   # 运行日志

    # ========== 浏览器管理 ==========

    async def _launch_browser(self):
        """启动浏览器"""
        from playwright.async_api import async_playwright

        self._add_log("info", "步骤1: 启动Playwright...")
        self._playwright = await async_playwright().start()
        self._add_log("info", "步骤2: Playwright已启动，查找Chrome...")

        # 查找 Chrome 可执行文件
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
        ]
        chrome_path = next((p for p in chrome_paths if os.path.exists(p)), None)

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1280,800",
        ]

        if not self.headless:
            launch_args.append("--auto-open-devtools-for-tabs")

        launch_options = {"headless": self.headless, "args": launch_args}

        if chrome_path:
            self._add_log("info", f"步骤3: 找到Chrome: {chrome_path}")
            launch_options["executable_path"] = chrome_path
        else:
            self._add_log("warning", "步骤3: 未找到Chrome，使用默认方式...")

        self._add_log("info", "步骤4: 启动Chrome浏览器...")
        self._browser = await self._playwright.chromium.launch(**launch_options)
        self._add_log("info", "步骤5: Chrome已启动，创建上下文...")

        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        self._page = await self._context.new_page()
        self._add_log("info", f"浏览器已启动 (headless={self.headless})")

    async def _close_browser(self):
        """关闭浏览器"""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass

    def _add_log(self, level: str, message: str):
        """添加运行日志"""
        entry = {"time": datetime.now().isoformat(), "level": level, "message": message}
        self.logs.append(entry)
        if level == "error":
            log.error(f"[DamaiBot] {message}")
        elif level == "warning":
            log.warning(f"[DamaiBot] {message}")
        else:
            log.info(f"[DamaiBot] {message}")

    def _get_sleep(self, base: float) -> float:
        """根据快速模式返回等待时间"""
        if self.config.fast_mode:
            return max(0.1, base * 0.3)
        return base

    # ========== 主流程 ==========

    async def run(self):
        """主入口：执行完整抢票流程"""
        self.running = True
        self.start_time = datetime.now()
        self.retry_count = 0
        self.logs = []

        try:
            # 阶段1：启动浏览器
            self.stage = "launch"
            self._add_log("info", "=" * 50)
            self._add_log("info", "大麦网自动抢票引擎启动")
            self._add_log("info", f"目标URL: {self.config.target_url}")
            self._add_log("info", f"观演人: {', '.join(self.config.users)}")
            self._add_log("info", f"快速模式: {'开启' if self.config.fast_mode else '关闭'}")
            self._add_log("info", f"自动提交: {'开启' if self.config.if_commit_order else '关闭'}")
            self._add_log("info", f"无头模式: {self.headless}")
            self._add_log("info", "=" * 50)

            self._add_log("info", "正在启动浏览器...")
            await self._launch_browser()
            self._add_log("info", "浏览器启动完成")

            # 阶段2：登录
            self.stage = "login"
            self._add_log("info", "阶段2：登录大麦网")
            await self._login()

            # 阶段3：进入详情页并选择
            self.stage = "select"
            self._add_log("info", "阶段3：进入演出详情页")
            await self._navigate_to_target()

            # 阶段4：选择场次、票价、数量
            self._add_log("info", "阶段4：选择场次/票价/数量")
            await self._select_concert_options()

            # 阶段5：轮询预订按钮
            self.stage = "polling"
            self._add_log("info", "阶段5：轮询检测预订按钮...")
            await self._poll_and_book()

            # 阶段6：选择观演人
            self.stage = "select_users"
            self._add_log("info", "阶段6：选择观演人")
            await self._select_viewers()

            # 阶段7：提交订单
            self.stage = "submit"
            self._add_log("info", "阶段7：提交订单")
            if self.config.if_commit_order:
                await self._submit_order()
                self._add_log("success", "订单已提交！请尽快完成支付！")
            else:
                self._add_log("warning", "自动提交已关闭，请在浏览器中手动确认订单")
                # 保持浏览器打开，等待手动操作
                await asyncio.sleep(300)  # 5分钟

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self._add_log("error", f"流程异常: {e}")
            self._add_log("error", f"详细错误:\n{tb[-500:]}")
        finally:
            # 自动提交模式才关浏览器，否则保持打开让用户看到状态
            if self.config.if_commit_order:
                await self._close_browser()
            self.stage = "done"
            self.running = False

    # ========== 阶段实现 ==========

    async def _login(self):
        """登录大麦网 - 扫码方式"""
        await self._page.goto(self.config.login_url, wait_until="domcontentloaded")
        await asyncio.sleep(self._get_sleep(3))

        # 尝试切换到扫码登录
        try:
            # 大麦登录页可能有多种登录方式，查找扫码tab
            qr_tabs = await self._page.query_selector_all('[class*="qrcode"], [class*="scan"], [data-type="qr"]')
            for tab in qr_tabs:
                try:
                    await tab.click()
                    await asyncio.sleep(self._get_sleep(1))
                except Exception:
                    pass

            # 查找并截图二维码
            qr_img = await self._page.query_selector('img[class*="qrcode"], img[src*="qr"], canvas[class*="qr"], .qrcode-img')
            if qr_img:
                # 截图显示给用户
                qr_screenshot = await qr_img.screenshot()
                # 保存到文件供前端读取
                qr_dir = Path(app_settings.LOG_DIR).parent / "data" / "qrcode"
                qr_dir.mkdir(parents=True, exist_ok=True)
                qr_path = qr_dir / f"login_qr_{datetime.now().strftime('%H%M%S')}.png"
                qr_path.write_bytes(qr_screenshot)
                self._add_log("info", f"请使用大麦APP扫描二维码 (已保存到 {qr_path})")
        except Exception as e:
            self._add_log("warning", f"查找二维码失败: {e}")

        self._add_log("info", "等待扫码登录... (超时120秒)")
        # 等待登录完成（检测页面跳转或cookie变化）
        logged_in = False
        for i in range(120):
            try:
                current_url = self._page.url
                if "passport" not in current_url and "login" not in current_url:
                    logged_in = True
                    break
                # 检测cookie
                cookies = await self._context.cookies()
                for c in cookies:
                    if c.get("name") in ("_m_h5_tk", "login_refer", "damai_cn_user"):
                        logged_in = True
                        break
                if logged_in:
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
            if i % 10 == 9:
                self._add_log("info", f"等待登录中... ({i+1}/120)")

        if logged_in:
            self._add_log("success", "登录成功")
        else:
            self._add_log("warning", "登录超时，继续尝试...")

    async def _navigate_to_target(self):
        """进入目标演出详情页"""
        await self._page.goto(self.config.target_url, wait_until="domcontentloaded",
                              timeout=30000)
        await asyncio.sleep(self._get_sleep(self.config.page_load_delay))

        # 自动检测页面类型
        url = self._page.url
        if "m.damai" in url or "mobile" in url:
            self._add_log("info", "检测到移动端页面")
        else:
            self._add_log("info", "检测到PC端页面")
        self._add_log("info", f"当前URL: {url}")

    async def _select_concert_options(self):
        """选择城市、场次、票价、数量"""
        page = self._page
        delay = self._get_sleep

        # --- 选择城市 ---
        if self.config.city:
            try:
                city_btn = await page.query_selector('[class*="city"], [class*="address"], [data-city]')
                if city_btn:
                    await city_btn.click()
                    await asyncio.sleep(delay(0.5))
                    city_items = await page.query_selector_all('[class*="city-item"], [class*="citylist"] li, [class*="select"] li')
                    for item in city_items:
                        text = await item.inner_text()
                        if self.config.city in text:
                            await item.click()
                            self._add_log("info", f"已选择城市: {self.config.city}")
                            await asyncio.sleep(delay(0.5))
                            break
            except Exception as e:
                self._add_log("warning", f"选择城市失败: {e}")

        # --- 选择场次日期 ---
        if self.config.dates:
            try:
                session_items = await page.query_selector_all(
                    '[class*="perform"], [class*="session"], [class*="time-item"], '
                    '[class*="场次"], [class*="item-time"], [data-date]'
                )
                for date_pattern in self.config.dates:
                    for item in session_items:
                        try:
                            text = await item.inner_text()
                            if date_pattern in text:
                                await item.click()
                                self._add_log("info", f"已选择场次: {text.strip()[:30]}")
                                await asyncio.sleep(delay(0.5))
                                break
                        except Exception:
                            continue
            except Exception as e:
                self._add_log("warning", f"选择场次失败: {e}")

        # --- 选择票价 ---
        if self.config.prices:
            try:
                price_items = await page.query_selector_all(
                    '[class*="sku"], [class*="price"], [class*="ticket-item"], '
                    '[class*="票档"], [class*="price-item"], [data-price]'
                )
                for price_pattern in self.config.prices:
                    for item in price_items:
                        try:
                            text = await item.inner_text()
                            # 模糊匹配（去掉¥符号等）
                            clean_text = text.replace('¥', '').replace('￥', '').strip()
                            clean_pattern = price_pattern.replace('¥', '').replace('￥', '').strip()
                            if clean_pattern in clean_text:
                                # 检查是否售罄
                                if '售罄' in text or '缺货' in text or 'disabled' in str(await item.get_attribute('class')):
                                    self._add_log("warning", f"票档「{text.strip()[:20]}」已售罄，跳过")
                                    continue
                                await item.click()
                                self._add_log("info", f"已选择票价: {text.strip()[:30]}")
                                await asyncio.sleep(delay(0.5))
                                break
                        except Exception:
                            continue
            except Exception as e:
                self._add_log("warning", f"选择票价失败: {e}")

        # --- 选择数量 ---
        try:
            ticket_count = len(self.config.users)
            if ticket_count > 1:
                count_btns = await page.query_selector_all(
                    '[class*="count-plus"], [class*="add"], [class*="increase"], '
                    '[class*="plus"], [class*="jia"]'
                )
                for _ in range(ticket_count - 1):
                    for btn in count_btns:
                        try:
                            await btn.click()
                            await asyncio.sleep(delay(0.3))
                            break
                        except Exception:
                            continue
                self._add_log("info", f"已选择数量: {ticket_count}张")
            else:
                self._add_log("info", f"购票数量: 1张")
        except Exception as e:
            self._add_log("warning", f"选择数量失败: {e}")

    async def _poll_and_book(self):
        """轮询检测并点击预订按钮"""
        page = self._page
        delay = self._get_sleep
        max_retries = self.config.max_retries

        self._add_log("info", f"开始轮询预订按钮 (最多{max_retries}次)...")

        for i in range(max_retries):
            if not self.running:
                return
            self.retry_count = i + 1

            try:
                # 查找"立即预订"按钮
                book_btns = await page.query_selector_all('''
                    [class*="buy"], [class*="book"], [class*="purchase"],
                    button:has-text("立即预订"),
                    button:has-text("立即购买"),
                    button:has-text("马上预订"),
                    [class*="buy-btn"], [class*="submit-btn"],
                    a:has-text("立即预订")
                ''')

                for btn in book_btns:
                    try:
                        is_visible = await btn.is_visible()
                        is_disabled = await btn.get_attribute('disabled')
                        classes = await btn.get_attribute('class') or ''

                        if is_visible and not is_disabled and 'disabled' not in classes:
                            text = await btn.inner_text()
                            if any(kw in text for kw in ['预订', '购买', '马上']):
                                await btn.click()
                                self._add_log("success", f"点击预订按钮 (第{i+1}次尝试)")
                                await asyncio.sleep(self._get_sleep(2))
                                return
                    except Exception:
                        continue

                # 监听模式：检测缺货登记是否变成可预订
                if self.config.if_listen:
                    try:
                        register_btn = await page.query_selector(
                            'text=缺货登记, [class*="soldout"], [class*="sold-out"]'
                        )
                        if not register_btn:
                            # 缺货标记消失，可能有票了
                            await page.reload()
                            await asyncio.sleep(self._get_sleep(self.config.page_load_delay))
                            self._add_log("info", "检测到页面状态变化，已刷新")
                    except Exception:
                        pass

                if i % 50 == 49:
                    self._add_log("info", f"轮询中... ({i+1}/{max_retries})")

            except Exception as e:
                pass

            await asyncio.sleep(delay(1.0 if not self.config.fast_mode else 0.3))

        self._add_log("warning", f"轮询结束，未找到可预订按钮 (共{max_retries}次)")

    async def _select_viewers(self):
        """选择观演人"""
        await asyncio.sleep(self._get_sleep(self.config.page_load_delay))
        page = self._page

        # 等待订单确认页加载
        await asyncio.sleep(self._get_sleep(1.5))

        for idx, user_name in enumerate(self.config.users):
            self._add_log("info", f"选择观演人 ({idx+1}/{len(self.config.users)}): {user_name}")
            try:
                # 查找包含用户名的元素
                user_elements = await page.query_selector_all(
                    '[class*="viewer"], [class*="user"], [class*="person"], '
                    '[class*="name"], [class*="观演"], label'
                )
                found = False
                for el in user_elements:
                    try:
                        text = await el.inner_text()
                        if user_name in text:
                            # 查找关联的checkbox/radio
                            checkbox = await el.query_selector('input[type="checkbox"], input[type="radio"]')
                            if checkbox:
                                await checkbox.click()
                            else:
                                await el.click()
                            found = True
                            self._add_log("info", f"已选择: {user_name}")
                            await asyncio.sleep(self._get_sleep(0.3))
                            break
                    except Exception:
                        continue

                if not found:
                    self._add_log("warning", f"未找到观演人: {user_name}")
            except Exception as e:
                self._add_log("error", f"选择观演人失败 [{user_name}]: {e}")

    async def _submit_order(self):
        """提交订单"""
        await asyncio.sleep(self._get_sleep(0.5))
        page = self._page

        submit_selectors = [
            'button:has-text("提交订单")',
            'button:has-text("立即支付")',
            '[class*="submit"]',
            '.submit-btn',
            '#submitOrder',
        ]

        for selector in submit_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    self._add_log("success", "订单已提交！")
                    await asyncio.sleep(3)
                    return
            except Exception:
                continue

        self._add_log("warning", "未找到提交按钮，请手动点击")

    def stop(self):
        """停止抢票"""
        self.running = False
        self._add_log("warning", "用户手动停止")
        asyncio.ensure_future(self._close_browser())

    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "running": self.running,
            "stage": self.stage,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "retry_count": self.retry_count,
            "max_retries": self.config.max_retries,
            "config": self.config.to_dict(),
            "recent_logs": self.logs[-30:],
        }


# ============================================================
# 全局实例管理
# ============================================================

_bot_instance: Optional[DamaiBot] = None


def get_bot() -> Optional[DamaiBot]:
    return _bot_instance


def create_bot(config: DamaiConfig, headless: bool = False) -> DamaiBot:
    global _bot_instance
    if _bot_instance and _bot_instance.running:
        _bot_instance.stop()
    _bot_instance = DamaiBot(config, headless=headless)
    return _bot_instance


def load_config_from_file() -> DamaiConfig:
    """从配置文件加载"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return DamaiConfig.from_dict(data)
    return DamaiConfig()


def save_config_to_file(config: DamaiConfig):
    """保存配置到文件"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
