"""
数据采集服务
基于 Playwright 的票务平台数据采集
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page

from ..config import settings
from ..database import get_session
from ..models.models import (
    Concert, Show, TicketTier, StatusHistory,
    TicketStatus, ChangeType, MonitorLog, LogLevel,
)
from ..utils.logger import log


class ScraperService:
    """Playwright 数据采集器"""

    # 常见 Chrome 安装路径
    _CHROME_PATHS = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]

    def __init__(self):
        self.browser: Optional[Browser] = None
        self._chrome_path: Optional[str] = None

    def _find_chrome(self) -> Optional[str]:
        """自动查找本机 Chrome 可执行文件"""
        import os as _os, shutil as _shutil

        username = _os.environ.get("USERNAME", _os.environ.get("USER", ""))
        for pattern in self._CHROME_PATHS:
            path = pattern.format(username) if "{}" in pattern else pattern
            if _shutil.which(path) or _os.path.exists(path):
                self._chrome_path = path
                return path
        return None

    async def _get_browser(self) -> Browser:
        """获取或创建浏览器实例（自动查找本机 Chrome）"""
        if self.browser is None or not self.browser.is_connected():
            pw = await async_playwright().start()
            self._playwright = pw

            chrome_path = self._find_chrome()
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ]

            if chrome_path:
                log.info(f"使用本机 Chrome: {chrome_path}")
                try:
                    self.browser = await pw.chromium.launch(
                        headless=settings.HEADLESS,
                        executable_path=chrome_path,
                        args=launch_args,
                    )
                    return self.browser
                except Exception as e:
                    log.warning(f"本机 Chrome 启动失败: {e}")

            # Fallback: 尝试 channel="chrome"
            try:
                log.info("尝试通过 Playwright channel 启动 Chrome...")
                self.browser = await pw.chromium.launch(
                    headless=settings.HEADLESS,
                    channel="chrome",
                    args=launch_args,
                )
                return self.browser
            except Exception:
                pass

            # 最后兜底: 使用 Playwright 自带的 Chromium（需要先 playwright install chromium）
            log.warning("未找到 Chrome，尝试 Playwright 自带 Chromium...")
            self.browser = await pw.chromium.launch(
                headless=settings.HEADLESS,
                args=launch_args,
            )
        return self.browser

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None

    async def scrape_concert(self, concert: Concert) -> Dict[str, Any]:
        """
        采集演出数据
        通用采集策略：打开页面 → 提取关键数据 → 解析结构化信息
        """
        browser = await self._get_browser()
        context = await browser.new_context(
            user_agent=settings.USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = await context.new_page()

        result = {
            "concert_name": concert.name,
            "url": concert.url,
            "show_count": 0,
            "shows": [],
        }

        try:
            log.info(f"开始采集: {concert.name} ({concert.url})")

            # 访问目标页面
            await page.goto(concert.url, wait_until="domcontentloaded", timeout=settings.BROWSER_TIMEOUT)
            await asyncio.sleep(2)  # 等待动态内容加载

            # 获取页面内容
            page_content = await page.content()
            page_title = await page.title()

            # 通用提取策略：尝试多种选择器
            extracted_data = await self._extract_page_data(page)

            # 解析场次和票档信息
            shows_data = await self._parse_shows(page, extracted_data)

            # 写入数据库
            db = get_session()
            try:
                concert_obj = db.query(Concert).filter(Concert.id == concert.id).first()

                for show_info in shows_data:
                    # 检查场次是否已存在
                    existing_show = db.query(Show).filter(
                        Show.concert_id == concert.id,
                        Show.name == show_info.get("name", ""),
                    ).first()

                    if not existing_show:
                        show_time = show_info.get("show_time")
                        if show_time and isinstance(show_time, str):
                            try:
                                show_time = datetime.fromisoformat(show_time.replace("Z", "+00:00"))
                            except Exception:
                                show_time = None

                        existing_show = Show(
                            concert_id=concert.id,
                            name=show_info.get("name", ""),
                            show_time=show_time,
                            venue=show_info.get("venue", concert.venue),
                            show_id_platform=show_info.get("show_id", ""),
                        )
                        db.add(existing_show)
                        db.flush()

                    # 更新票档
                    for tier_info in show_info.get("ticket_tiers", []):
                        self._upsert_ticket_tier(db, existing_show.id, tier_info)

                    result["shows"].append({
                        "name": existing_show.name,
                        "tiers": len(show_info.get("ticket_tiers", [])),
                    })

                concert_obj.last_check = datetime.now()
                db.commit()
                result["show_count"] = len(shows_data)

            except Exception as e:
                db.rollback()
                log.error(f"数据库写入失败: {e}")
                raise
            finally:
                db.close()

        except Exception as e:
            log.error(f"页面采集失败 [{concert.name}]: {e}")
            raise
        finally:
            await context.close()

        return result

    async def _extract_page_data(self, page: Page) -> Dict[str, Any]:
        """从页面提取所有可用的结构化数据"""
        data = {}

        # 提取页面中的JSON-LD结构化数据
        try:
            json_ld = await page.eval_on_selector_all(
                'script[type="application/ld+json"]',
                "els => els.map(el => el.textContent)"
            )
            parsed_ld = []
            for ld in json_ld:
                try:
                    parsed_ld.append(json.loads(ld))
                except json.JSONDecodeError:
                    pass
            data["json_ld"] = parsed_ld
        except Exception:
            data["json_ld"] = []

        # 提取所有 script 标签中的 JSON 数据
        try:
            scripts_data = await page.evaluate(r"""
                () => {
                    const scripts = document.querySelectorAll('script');
                    const results = [];
                    scripts.forEach(s => {
                        const text = s.textContent || '';
                        // Try to match JSON objects
                        const matches = text.match(/\{[^}]*"name"[^}]*"price"[^}]*\}/gi) || [];
                        matches.forEach(m => {
                            try { results.push(JSON.parse(m)); } catch(e) {}
                        });
                        // Match __NEXT_DATA__ or window.__INITIAL_STATE__
                        if (text.includes('window.__INITIAL_STATE__') || text.includes('__NEXT_DATA__')) {
                            try {
                                const jsonMatch = text.match(
                                    /(?:window\.__INITIAL_STATE__\s*=\s*|__NEXT_DATA__\s*=\s*)(\{.*\})/s
                                );
                                if (jsonMatch) results.push(JSON.parse(jsonMatch[1]));
                            } catch(e) {}
                        }
                    });
                    return results;
                }
            """)
            data["script_data"] = scripts_data
        except Exception:
            data["script_data"] = []

        # 提取页面文本内容
        try:
            data["body_text"] = await page.inner_text("body")
        except Exception:
            data["body_text"] = ""

        return data

    async def _parse_shows(self, page: Page, extracted_data: Dict) -> List[Dict]:
        """从提取的数据中解析场次和票档"""
        shows = []

        # 策略1: 从 JSON-LD 解析
        for ld in extracted_data.get("json_ld", []):
            if isinstance(ld, dict):
                if ld.get("@type") == "Event":
                    show = self._parse_event_ld(ld)
                    if show:
                        shows.append(show)
                elif isinstance(ld, list):
                    for item in ld:
                        if isinstance(item, dict) and item.get("@type") == "Event":
                            show = self._parse_event_ld(item)
                            if show:
                                shows.append(show)

        # 策略2: 从 JavaScript 状态数据解析
        if not shows:
            for script_data in extracted_data.get("script_data", []):
                parsed = self._parse_script_data(script_data)
                shows.extend(parsed)

        # 策略3: 从 DOM 元素解析（通用选择器）
        if not shows:
            try:
                dom_shows = await page.evaluate("""
                    () => {
                        const shows = [];
                        // 常见票务平台的 DOM 结构
                        const showElements = document.querySelectorAll(
                            '[class*="show"], [class*="session"], [class*="performance"], ' +
                            '[class*="场次"], [class*="演出"], [data-show-id]'
                        );
                        showElements.forEach(el => {
                            const name = el.querySelector('[class*="name"], [class*="title"], h3, h4')?.innerText || '';
                            const time = el.querySelector('[class*="time"], [class*="date"]')?.innerText || '';
                            const tiers = [];
                            const tierElements = el.querySelectorAll(
                                '[class*="ticket"], [class*="tier"], [class*="price"], [class*="票"]'
                            );
                            tierElements.forEach(t => {
                                tiers.push({
                                    name: t.querySelector('[class*="name"], [class*="label"]')?.innerText || '',
                                    price: t.querySelector('[class*="price"], [class*="amount"]')?.innerText || '',
                                    status: t.innerText.includes('售罄') ? 'sold_out' : 'available',
                                });
                            });
                            if (name || time) shows.push({ name, show_time: time, ticket_tiers: tiers });
                        });
                        return shows;
                    }
                """)
                shows = dom_shows
            except Exception:
                pass

        # 策略4: 兜底 - 从 body 文本中提取基本信息
        if not shows:
            body = extracted_data.get("body_text", "")
            # 尝试创建占位场次
            shows = [{
                "name": "默认场次",
                "show_time": None,
                "venue": "",
                "ticket_tiers": [],
            }]

        return shows

    def _parse_event_ld(self, ld: Dict) -> Optional[Dict]:
        """解析 Event 类型的 JSON-LD"""
        if not ld.get("name"):
            return None

        offers = ld.get("offers", {})
        if isinstance(offers, dict):
            offers = [offers]

        tiers = []
        for offer in offers:
            tiers.append({
                "name": offer.get("name", ""),
                "price": float(offer.get("price", 0)),
                "status": "sold_out" if offer.get("availability") == "SoldOut" else "available",
                "tier_id": offer.get("@id", ""),
            })

        return {
            "name": ld.get("name", ""),
            "show_time": ld.get("startDate", ""),
            "venue": ld.get("location", {}).get("name", "") if isinstance(ld.get("location"), dict) else "",
            "show_id": ld.get("@id", ""),
            "ticket_tiers": tiers,
        }

    def _parse_script_data(self, data: Any, depth: int = 0) -> List[Dict]:
        """递归解析 JavaScript 状态数据"""
        if depth > 5:
            return []

        results = []

        if isinstance(data, dict):
            # 查找可能包含演出信息的键
            for key in ["shows", "sessions", "performances", "events", "场次"]:
                if key in data:
                    items = data[key]
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                tiers = self._extract_tiers(item)
                                results.append({
                                    "name": item.get("name") or item.get("title") or "",
                                    "show_time": item.get("time") or item.get("startTime") or item.get("date") or "",
                                    "venue": item.get("venue") or item.get("location") or "",
                                    "show_id": str(item.get("id", "")),
                                    "ticket_tiers": tiers,
                                })

            # 递归搜索
            for value in data.values():
                results.extend(self._parse_script_data(value, depth + 1))

        elif isinstance(data, list):
            for item in data:
                results.extend(self._parse_script_data(item, depth + 1))

        return results

    def _extract_tiers(self, item: Dict) -> List[Dict]:
        """从数据项中提取票档信息"""
        tiers = []
        tier_data = item.get("tickets") or item.get("tiers") or item.get("prices") or item.get("票档") or []

        if isinstance(tier_data, list):
            for t in tier_data:
                if isinstance(t, dict):
                    tiers.append({
                        "name": t.get("name") or t.get("label") or "",
                        "price": float(t.get("price") or t.get("amount") or 0),
                        "status": t.get("status") or ("sold_out" if t.get("soldOut") else "available"),
                        "tier_id": str(t.get("id", "")),
                    })

        return tiers

    def _upsert_ticket_tier(self, db, show_id: int, tier_info: Dict):
        """插入或更新票档，记录状态变更"""
        existing = db.query(TicketTier).filter(
            TicketTier.show_id == show_id,
            TicketTier.name == tier_info.get("name", ""),
        ).first()

        new_status_str = tier_info.get("status", "unknown")
        try:
            new_status = TicketStatus(new_status_str)
        except ValueError:
            new_status = TicketStatus.UNKNOWN

        new_stock = tier_info.get("stock_count", -1)
        new_price = float(tier_info.get("price", 0))

        if existing:
            old_status = existing.status.value if existing.status else "unknown"
            old_stock = existing.stock_count
            old_price = existing.price

            # 检测变化
            changed = False
            change_type = None
            messages = []

            if old_status != new_status.value:
                changed = True
                if new_status == TicketStatus.SOLD_OUT:
                    change_type = ChangeType.SOLD_OUT
                    messages.append(f"票档「{tier_info['name']}」已售罄")
                elif old_status == "sold_out" and new_status == TicketStatus.AVAILABLE:
                    change_type = ChangeType.STOCK
                    messages.append(f"票档「{tier_info['name']}」恢复有票")
                else:
                    change_type = ChangeType.STOCK
                    messages.append(f"票档「{tier_info['name']}」状态变更: {old_status} → {new_status.value}")

            if old_price != new_price and new_price > 0:
                changed = True
                change_type = ChangeType.PRICE if not change_type else change_type
                messages.append(f"票价变更: ¥{old_price} → ¥{new_price}")

            if old_stock != new_stock and new_stock >= 0:
                changed = True
                change_type = ChangeType.STOCK if not change_type else change_type
                messages.append(f"库存变更: {old_stock} → {new_stock}")

            if changed:
                history = StatusHistory(
                    ticket_tier_id=existing.id,
                    old_status=old_status,
                    new_status=new_status.value,
                    old_stock=old_stock,
                    new_stock=new_stock,
                    old_price=old_price,
                    new_price=new_price,
                    change_type=change_type or ChangeType.STOCK,
                    message="; ".join(messages),
                )
                db.add(history)

            # 更新现有记录
            existing.status = new_status
            existing.price = new_price
            existing.stock_count = new_stock
            existing.tier_id_platform = tier_info.get("tier_id", existing.tier_id_platform)

        else:
            # 新建票档
            tier = TicketTier(
                show_id=show_id,
                name=tier_info.get("name", ""),
                price=new_price,
                face_value=tier_info.get("face_value", 0),
                status=new_status,
                stock_count=new_stock,
                tier_id_platform=tier_info.get("tier_id", ""),
            )
            db.add(tier)


# 全局单例
scraper_service = ScraperService()
