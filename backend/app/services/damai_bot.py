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
            # === 阶段1：启动浏览器 ===
            self.stage = "launch"
            self._add_log("info", f"目标: {self.config.target_url}")
            self._add_log("info", f"观演人: {', '.join(self.config.users)}")
            self._add_log("info", f"日期: {', '.join(self.config.dates) if self.config.dates else '默认'}")
            self._add_log("info", f"票价: {', '.join(self.config.prices) if self.config.prices else '默认'}")
            self._add_log("info", f"自动提交: {'是' if self.config.if_commit_order else '否'}")
            await self._launch_browser()

            # === 阶段2：登录 ===
            self.stage = "login"
            await self._login()

            # === 阶段3：进入详情页 + 选择 ===
            self.stage = "select"
            await self._navigate_to_target()
            self._add_log("info", ">>> 开始自动选择场次/票价...")
            await self._select_concert_options()

            # === 阶段4：轮询预订按钮 ===
            self.stage = "polling"
            self._add_log("info", ">>> 开始轮询预订按钮...")
            await self._poll_and_book()

            # === 阶段5：选择观演人 ===
            self.stage = "select_users"
            self._add_log("info", ">>> 选择观演人...")
            await self._select_viewers()

            # === 阶段6：提交订单 ===
            self.stage = "submit"
            if self.config.if_commit_order:
                self._add_log("info", ">>> 提交订单...")
                await self._submit_order()
                self._add_log("success", "========== 订单已提交！请尽快付款！==========")
            else:
                self._add_log("warning", "自动提交已关闭，浏览器保持打开，请手动操作")
                await asyncio.sleep(300)

        except Exception as e:
            import traceback
            self._add_log("error", f"异常: {e}")
            self._add_log("error", traceback.format_exc()[-300:])
        finally:
            self.stage = "done"
            self.running = False

    # ========== 阶段实现 ==========

    async def _login(self):
        """登录大麦网 - 极简版，不触发任何页面操作"""
        self._add_log("info", "打开大麦登录页...")

        # 直接进登录页
        await self._page.goto("https://passport.damai.cn/login", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 可能已经登录（记住密码自动跳转了）
        if "passport" not in self._page.url and "login" not in self._page.url:
            self._add_log("success", "已登录，无需扫码")
            return

        self._add_log("info", "=" * 50)
        self._add_log("info", "  请打开大麦APP扫描二维码")
        self._add_log("info", "  二维码每2分钟自动刷新是正常的")
        self._add_log("info", "  等待时间: 最多5分钟")
        self._add_log("info", "=" * 50)

        # 等待登录，不刷新不跳转不操作页面
        for i in range(300):
            try:
                url = self._page.url
                if "passport" not in url and "login" not in url:
                    self._add_log("success", "登录成功！")
                    # 确保 cookie 在 damai.cn 域下生效
                    await self._page.goto("https://www.damai.cn/", wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(2)
                    return
                cookies = await self._context.cookies()
                for c in cookies:
                    if c.get("name") in ("_m_h5_tk", "login_refer", "damai_cn_user", "cookie2"):
                        if c.get("value", ""):
                            self._add_log("success", "登录成功！")
                            await self._page.goto("https://www.damai.cn/", wait_until="domcontentloaded", timeout=15000)
                            await asyncio.sleep(2)
                            return
            except Exception:
                pass
            await asyncio.sleep(1)
            if i % 60 == 59:
                self._add_log("info", f"等待扫码... ({i+1}/300 秒)")

        self._add_log("warning", "登录超时")


    async def _navigate_to_target(self):
        """进入目标演出详情页"""
        target = self.config.target_url
        self._add_log("info", f"打开: {target}")
        await self._page.goto(target, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)  # 等SPA渲染

        url = self._page.url
        self._add_log("info", f"当前URL: {url}")

        # 如果被重定向到登录页，说明 cookie 过期了
        if "login" in url or "passport" in url:
            self._add_log("warning", "被重定向到登录页，请重新扫码...")
            await self._login_again()
            # 重新跳转
            await self._page.goto(target, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)
            self._add_log("info", f"重试后URL: {self._page.url}")

        # PC端：点击"不，立即购票"关闭手机购买提示
        url = self._page.url
        if "m.damai" not in url:
            self._add_log("info", "PC端页面，关闭手机购买提示...")
            try:
                link = self._page.locator(".buy-link").first
                if await link.count() > 0 and await link.is_visible():
                    await link.click()
                    await asyncio.sleep(2)
                    self._add_log("info", "已点击'不，立即购票'")
            except Exception:
                pass
            try:
                link = self._page.locator("text=立即购票").first
                if await link.count() > 0 and await link.is_visible():
                    await link.click()
                    await asyncio.sleep(2)
                    self._add_log("info", "已点击'立即购票'")
            except Exception:
                pass

    async def _login_again(self):
        """重新登录"""
        await self._page.goto("https://passport.damai.cn/login", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        self._add_log("info", "请再次扫码登录...")
        for i in range(120):
            try:
                url = self._page.url
                if "passport" not in url and "login" not in url:
                    return
                cookies = await self._context.cookies()
                for c in cookies:
                    if c.get("name") in ("_m_h5_tk", "login_refer", "damai_cn_user", "cookie2"):
                        if c.get("value"):
                            return
            except Exception:
                pass
            await asyncio.sleep(1)

    async def _save_debug_screenshot(self, name: str):
        """保存调试截图、HTML、元素数据"""
        try:
            ss_dir = Path("data/screenshots")
            ss_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime('%H%M%S')

            # 截图
            path = ss_dir / f"{name}_{ts}.png"
            await self._page.screenshot(path=str(path), full_page=True)
            self._add_log("info", f"截图已保存: {path}")

            # 保存 HTML
            html_path = ss_dir / f"{name}_{ts}.html"
            html = await self._page.content()
            html_path.write_text(html, encoding="utf-8")
            self._add_log("info", f"HTML已保存: {html_path} ({len(html)} 字符)")

            # 提取关键元素
            elements = await self._page.evaluate("""
                () => {
                    const results = [];
                    const allEls = document.querySelectorAll('*');
                    allEls.forEach(el => {
                        if (['SCRIPT','STYLE','NOSCRIPT','SVG','PATH','META','LINK'].includes(el.tagName)) return;
                        const rect = el.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0 || rect.y > 10000) return;
                        const text = (el.textContent || '').trim().replace(/\\s+/g, ' ');
                        if (text.length < 2 || text.length > 200) return;
                        if (el.children.length > 5) return;
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: text.slice(0, 100),
                            id: el.id || '',
                            cls: (typeof el.className === 'string') ? el.className.slice(0, 120) : '',
                            href: el.href || '',
                            disabled: el.disabled || false,
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            w: Math.round(rect.width),
                            h: Math.round(rect.height),
                        });
                    });
                    return results;
                }
            """)
            elem_path = ss_dir / f"{name}_{ts}_elements.json"
            import json as _json
            elem_path.write_text(_json.dumps(elements, ensure_ascii=False, indent=2), encoding="utf-8")
            self._add_log("info", f"元素数据已保存: {elem_path} ({len(elements)} 个元素)")
        except Exception:
            pass

    async def _click_text(self, text: str) -> bool:
        """
        点击页面上包含指定文本的可点击元素
        多层策略：精确文本匹配 → 包含匹配 → JS 搜索+点击
        """
        page = self._page

        # 策略1: Playwright getByText (精确匹配)
        try:
            loc = page.get_by_text(text, exact=True).first
            if await loc.count() > 0:
                tag = await loc.evaluate("el => el.tagName.toLowerCase()")
                if tag not in ("html", "body"):
                    await loc.scroll_into_view_if_needed()
                    await asyncio.sleep(0.1)
                    await loc.click(timeout=3000)
                    self._add_log("info", f"  -> 点击成功(精确): '{text}' <{tag}>")
                    return True
        except Exception:
            pass

        # 策略2: 包含文本匹配
        try:
            loc = page.locator(f"text={text}").first
            if await loc.count() > 0:
                tag = await loc.evaluate("el => el.tagName.toLowerCase()")
                if tag not in ("html", "body"):
                    await loc.scroll_into_view_if_needed()
                    await asyncio.sleep(0.1)
                    await loc.click(timeout=3000)
                    self._add_log("info", f"  -> 点击成功(包含): '{text}' <{tag}>")
                    return True
        except Exception:
            pass

        # 策略3: JS 搜索所有叶子元素，找文本匹配的
        try:
            result = await page.evaluate(f"""
                (() => {{
                    const target = {json.dumps(text)};
                    // 获取所有叶子或小容器元素
                    const candidates = [];
                    const all = document.querySelectorAll('*');
                    for (const el of all) {{
                        if (el.children.length > 3) continue;
                        const txt = (el.textContent || '').trim();
                        if (txt.includes(target) && txt.length < 100) {{
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && rect.y < 8000) {{
                                candidates.push({{
                                    el: el,
                                    score: txt.length,
                                    y: rect.y,
                                }});
                            }}
                        }}
                    }}
                    // 取最短匹配（最精确）的
                    candidates.sort((a, b) => a.score - b.score);
                    for (const c of candidates) {{
                        try {{
                            c.el.scrollIntoView({{block: 'center', behavior: 'instant'}});
                            c.el.click();
                            return JSON.stringify({{tag: c.el.tagName, text: c.el.textContent.trim().slice(0,50)}});
                        }} catch(e) {{ continue; }}
                    }}
                    return null;
                }})()
            """)
            if result:
                data = json.loads(result)
                self._add_log("info", f"  -> 点击成功(JS): '{text}' <{data['tag']}>='{data['text']}'")
                await asyncio.sleep(0.2)
                return True
        except Exception:
            pass

        # 策略4: 终极兜底 —— 用 text selector 找父级可点击元素
        try:
            # 找到包含文本的最近的可点击父元素
            clickable = await page.evaluate(f"""
                (() => {{
                    const target = {json.dumps(text)};
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    let node;
                    while (node = walker.nextNode()) {{
                        if (node.textContent.includes(target)) {{
                            // 向上找可点击的父元素
                            let parent = node.parentElement;
                            for (let i = 0; i < 5 && parent; i++) {{
                                const tag = parent.tagName;
                                const role = parent.getAttribute('role');
                                const cls = parent.className || '';
                                const clickable = (
                                    tag === 'A' || tag === 'BUTTON' ||
                                    role === 'button' ||
                                    cls.includes('btn') || cls.includes('item') ||
                                    cls.includes('select') || cls.includes('option') ||
                                    cls.includes('sku') || cls.includes('tab') ||
                                    parent.onclick
                                );
                                if (clickable) {{
                                    try {{
                                        parent.scrollIntoView({{block: 'center', behavior: 'instant'}});
                                        parent.click();
                                        return JSON.stringify({{tag: tag, cls: cls.slice(0,60), text: parent.textContent.trim().slice(0,50)}});
                                    }} catch(e) {{ return null; }}
                                }}
                                parent = parent.parentElement;
                            }}
                        }}
                    }}
                    return null;
                }})()
            """)
            if clickable:
                data = json.loads(clickable)
                self._add_log("info", f"  -> 点击成功(父级): '{text}' <{data['tag']}>='{data['text']}'")
                await asyncio.sleep(0.2)
                return True
        except Exception:
            pass

        return False

    async def _select_concert_options(self):
        """选择场次、票价、数量 — 基于真实大麦页面结构"""
        page = self._page
        delay = self._get_sleep

        await asyncio.sleep(2.0)
        self._add_log("info", "页面渲染完毕，开始自动选择...")
        await self._save_debug_screenshot("01_before_select")

        # --- 选择城市 (大麦PC端: 点击城市名打开下拉，再选目标) ---
        if self.config.city:
            self._add_log("info", f"选择城市: {self.config.city}")
            await asyncio.sleep(delay(0.5))
            # 先尝试点城市切换按钮
            try:
                city_switch = await page.query_selector('[class*="city-switch"], [class*="address"] span, a:has-text("全国")')
                if city_switch:
                    await city_switch.click()
                    await asyncio.sleep(delay(0.5))
            except Exception:
                pass
            # 再点目标城市
            clicked = await self._click_text(self.config.city)
            if clicked:
                self._add_log("info", f"已选择城市: {self.config.city}")
                await asyncio.sleep(delay(1.0))
            else:
                self._add_log("warning", f"未找到城市: {self.config.city}")

        # --- 选择场次日期 ---
        # 大麦PC端: div.select_right_list_item (在 perform__order__select__performs 下面)
        if self.config.dates:
            for date_pattern in self.config.dates:
                self._add_log("info", f"选择场次: {date_pattern}")
                await asyncio.sleep(delay(0.3))

                # 大麦PC日期格式是 "2026-07-11"，配置可能是 "2026.7.11"
                # 转换格式
                date_variants = [date_pattern]
                if "." in date_pattern:
                    p = date_pattern.split(".")
                    if len(p) == 3:
                        date_variants += [f"{p[0]}-{p[1].zfill(2)}-{p[2].zfill(2)}",
                                          f"{int(p[1])}月{int(p[2])}日"]

                clicked = False
                for dv in date_variants:
                    # 精准匹配：找包含日期文字的 select_right_list_item
                    try:
                        items = await page.query_selector_all('.select_right_list_item')
                        for item in items:
                            text = (await item.inner_text()).strip()
                            if dv in text:
                                is_active = 'active' in ((await item.get_attribute('class')) or '')
                                if not is_active:
                                    await item.scroll_into_view_if_needed()
                                    await item.click()
                                    self._add_log("info", f"已选择场次: {text[:30]}")
                                    clicked = True
                                    await asyncio.sleep(delay(0.5))
                                    break
                        if clicked:
                            break
                    except Exception:
                        continue

                if not clicked:
                    # 用通用 _click_text 兜底
                    for dv in date_variants:
                        if await self._click_text(dv):
                            clicked = True
                            break

                if not clicked:
                    self._add_log("warning", f"未找到场次: {date_pattern}")

        # --- 选择票价 ---
        # 大麦PC端: div.select_right_list_item.sku_item, 内含 div.skuname
        if self.config.prices:
            for price_pattern in self.config.prices:
                self._add_log("info", f"选择票档: {price_pattern}")
                await asyncio.sleep(delay(0.3))

                clean = price_pattern.replace("¥", "").replace("￥", "").strip()
                clicked = False

                # 精准匹配：找 sku_item 中包含价格数字的
                try:
                    sku_items = await page.query_selector_all('.sku_item')
                    for item in sku_items:
                        text = (await item.inner_text()).strip()
                        if clean in text:
                            # 检查是否售罄
                            if '售罄' in text or '缺货' in text:
                                self._add_log("warning", f"票档已售罄: {text[:30]}")
                                continue
                            is_active = 'active' in ((await item.get_attribute('class')) or '')
                            if not is_active:
                                await item.scroll_into_view_if_needed()
                                await item.click()
                                self._add_log("info", f"已选择票档: {text[:40]}")
                                clicked = True
                                await asyncio.sleep(delay(0.5))
                                break
                except Exception:
                    pass

                if not clicked:
                    # 用通用 _click_text 兜底
                    for variant in [clean, f"¥{clean}", f"￥{clean}", f"{clean}元"]:
                        if await self._click_text(variant):
                            clicked = True
                            break

                if not clicked:
                    self._add_log("warning", f"未找到票档: {price_pattern}")

        # --- 选择数量 ---
        ticket_count = len(self.config.users)
        if ticket_count > 1:
            self._add_log("info", f"设置购票数量: {ticket_count}")
            for _ in range(ticket_count - 1):
                try:
                    # 大麦PC: div.cafe-c-input-number 中的加号
                    plus = await page.query_selector('.cafe-c-input-number [class*="plus"], .cafe-c-input-number [class*="increase"], .cafe-c-input-number__plus')
                    if plus:
                        await plus.click()
                        clicked = True
                    else:
                        clicked = await self._click_text("+")
                except Exception:
                    clicked = False
                if clicked:
                    await asyncio.sleep(delay(0.3))
                else:
                    self._add_log("warning", "未找到数量加号")
                    break
            self._add_log("info", f"购票数量: {ticket_count}张")
        else:
            self._add_log("info", "购票数量: 1张")

        await self._save_debug_screenshot("02_after_select")
        self._add_log("info", "选择阶段完成")

    async def _poll_and_book(self):
        """轮询检测并点击预订按钮 — 文本定位"""
        page = self._page
        delay = self._get_sleep
        max_retries = self.config.max_retries

        self._add_log("info", f"开始轮询预订按钮 (最多{max_retries}次)...")

        for i in range(max_retries):
            if not self.running:
                return
            self.retry_count = i + 1

            try:
                # 用文本定位直接找购买按钮（PC端是"立即购票"，移动端是"立即预订"）
                for keyword in ["立即购票", "立即预订", "立即购买", "马上预订", "马上抢", "立即抢票"]:
                    try:
                        btn = page.locator(f"button:has-text('{keyword}'), a:has-text('{keyword}'), [role='button']:has-text('{keyword}')").first
                        if await btn.count() > 0 and await btn.is_visible():
                            # 检查是否被禁用
                            is_disabled = await btn.get_attribute('disabled')
                            classes = (await btn.get_attribute('class')) or ''
                            if not is_disabled and 'disabled' not in classes and 'disable' not in classes:
                                await btn.click(timeout=3000)
                                self._add_log("success", f"点击预订按钮 (第{i+1}次尝试, '{keyword}')")
                                await asyncio.sleep(self._get_sleep(2))
                                return
                    except Exception:
                        continue

                # 兜底：JS 查找所有包含预订文字的按钮
                try:
                    clicked = await page.evaluate("""
                        (() => {
                            const keywords = ['立即购票', '立即预订', '立即购买', '马上预订', '立即抢票'];
                            const elements = document.querySelectorAll('button, a, [role="button"], div[class*="buy"], span[class*="buy"]');
                            for (const el of elements) {
                                const text = (el.textContent || '').trim();
                                if (keywords.some(k => text.includes(k))) {
                                    if (!el.disabled && !el.classList.contains('disabled')) {
                                        el.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        })()
                    """)
                    if clicked:
                        self._add_log("success", f"点击预订按钮 (第{i+1}次尝试, JS)")
                        await asyncio.sleep(self._get_sleep(2))
                        return
                except Exception:
                    pass

                # 更激进的尝试：用 JS 找 btn-title 或其他购买按钮
                if i % 3 == 0:
                    try:
                        clicked = await page.evaluate("""
                            (() => {
                                // 找所有可能包含购买文字的按钮
                                const all = document.querySelectorAll('button, a, [role="button"], .btn-title, [class*="buy"], [class*="submit"]');
                                for (const el of all) {
                                    const text = (el.textContent || '').trim();
                                    if (/立即购票|立即预订|立即购买|马上预订|去支付|提交订单/.test(text)) {
                                        if (!el.disabled && !el.classList.contains('disabled') && !el.classList.contains('disable')) {
                                            const rect = el.getBoundingClientRect();
                                            if (rect.width > 0 && rect.height > 0) {
                                                el.scrollIntoView({block: 'center', behavior: 'instant'});
                                                el.click();
                                                return JSON.stringify({tag: el.tagName, text: text.slice(0,50)});
                                            }
                                        }
                                    }
                                }
                                return null;
                            })()
                        """)
                        if clicked:
                            import json as _j
                            info = _j.loads(clicked)
                            self._add_log("success", f"暴力点击成功: {info['tag']} '{info['text']}' (第{i+1}次)")
                            await asyncio.sleep(self._get_sleep(2))
                            return
                    except Exception:
                        pass

                # 心跳日志（不刷新页面）
                if i % 100 == 99:
                    try:
                        body_text = await page.inner_text("body")
                        if "缺货登记" in body_text:
                            self._add_log("info", f"当前状态: 缺货登记 (第{i+1}次轮询)")
                        elif "即将开售" in body_text:
                            self._add_log("info", f"当前状态: 即将开售 (第{i+1}次轮询)")
                        elif "售罄" in body_text:
                            self._add_log("info", f"当前状态: 售罄 (第{i+1}次轮询)")
                        else:
                            self._add_log("info", f"轮询中... (第{i+1}次)")
                    except Exception:
                        pass

                if i % 50 == 49:
                    self._add_log("info", f"轮询中... ({i+1}/{max_retries})")

            except Exception:
                pass

            await asyncio.sleep(delay(1.0 if not self.config.fast_mode else 0.3))

        self._add_log("warning", f"轮询结束，未找到可预订按钮 (共{max_retries}次)")

    async def _select_viewers(self):
        """选择观演人 - 文本定位点击"""
        await asyncio.sleep(self._get_sleep(2.0))
        page = self._page

        for idx, user_name in enumerate(self.config.users):
            self._add_log("info", f"选择观演人 ({idx+1}/{len(self.config.users)}): {user_name}")
            await asyncio.sleep(self._get_sleep(0.5))
            try:
                clicked = await self._click_text(user_name)
                if clicked:
                    self._add_log("info", f"已选择: {user_name}")
                    await asyncio.sleep(self._get_sleep(0.3))
                else:
                    self._add_log("warning", f"未找到观演人: {user_name}")
            except Exception as e:
                self._add_log("error", f"选择观演人失败 [{user_name}]: {e}")

    async def _submit_order(self):
        """提交订单 - 文本定位"""
        await asyncio.sleep(self._get_sleep(1.0))
        page = self._page

        # 用文本定位找提交按钮
        for keyword in ["提交订单", "立即支付", "确认下单", "去支付"]:
            try:
                btn = page.locator(f"text={keyword}").first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click(timeout=3000)
                    self._add_log("success", f"订单已提交！(匹配: {keyword})")
                    await asyncio.sleep(3)
                    return
            except Exception:
                continue

        # 兜底：用JS找
        try:
            clicked = await page.evaluate("""
                (() => {
                    const btns = document.querySelectorAll('button, a, [role="button"], .submit-btn');
                    for (const btn of btns) {
                        const text = btn.textContent || '';
                        if (/提交订单|立即支付|去支付|确认下单/.test(text)) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                })()
            """)
            if clicked:
                self._add_log("success", "订单已提交！(JS兜底)")
                await asyncio.sleep(3)
                return
        except Exception:
            pass

        self._add_log("warning", "未找到提交按钮，请手动点击提交")

    def stop(self):
        """停止抢票"""
        self.running = False
        self._add_log("warning", "用户手动停止 - 浏览器将在当前操作完成后关闭")

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
