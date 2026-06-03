"""反爬虫策略管理器"""

import random
import time
import asyncio
import logging
from typing import Optional, Dict, List

# 抑制 fake_useragent 的烦人错误日志
logging.getLogger('fake_useragent').setLevel(logging.ERROR)

from fake_useragent import UserAgent

from .config import config


class AntiCrawlManager:
    """反爬虫管理器 - 处理请求头、延迟、代理等"""

    _instance = None
    _ua: Optional[UserAgent] = None

    # 稳定的浏览器User-Agent列表（fake_useragent 可能失败时的备选）
    FALLBACK_USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    ]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._ua is None:
            try:
                self._ua = UserAgent(
                    browsers=['chrome', 'edge', 'firefox', 'safari'],
                    os=['Windows', 'MacOS'],
                    min_version=100.0
                )
            except Exception:
                self._ua = None

    def get_random_ua(self) -> str:
        """获取随机User-Agent"""
        if config.get("anti_crawl.rotate_ua", True):
            try:
                if self._ua:
                    return self._ua.random
            except Exception:
                pass
        return random.choice(self.FALLBACK_USER_AGENTS)

    def get_headers(self, referer: Optional[str] = None,
                    origin: Optional[str] = None,
                    additional: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """生成请求头"""
        headers = {
            "User-Agent": self.get_random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

        if referer:
            headers["Referer"] = referer
            headers["Sec-Fetch-Site"] = "same-origin"
        if origin:
            headers["Origin"] = origin

        if additional:
            headers.update(additional)

        return headers

    def get_ajax_headers(self, referer: str,
                         x_requested_with: bool = True) -> Dict[str, str]:
        """生成AJAX请求头"""
        headers = self.get_headers(referer=referer)
        headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest" if x_requested_with else "",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })
        return headers

    def random_delay(self, min_s: float = None, max_s: float = None) -> None:
        """随机延迟"""
        min_s = min_s or config.get("anti_crawl.delay_min", 1.0)
        max_s = max_s or config.get("anti_crawl.delay_max", 3.0)
        delay = random.uniform(min_s, max_s)
        time.sleep(delay)

    async def random_delay_async(self, min_s: float = None, max_s: float = None) -> None:
        """异步随机延迟"""
        min_s = min_s or config.get("anti_crawl.delay_min", 1.0)
        max_s = max_s or config.get("anti_crawl.delay_max", 3.0)
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    def get_proxies(self) -> Optional[Dict[str, str]]:
        """获取代理配置"""
        if not config.get("search.proxy.enabled", False):
            return None

        proxies = {}
        http_proxy = config.get("search.proxy.http", "")
        https_proxy = config.get("search.proxy.https", "")
        socks5_proxy = config.get("search.proxy.socks5", "")

        if http_proxy:
            proxies["http://"] = http_proxy
        if https_proxy:
            proxies["https://"] = https_proxy
        if socks5_proxy:
            proxies["http://"] = socks5_proxy
            proxies["https://"] = socks5_proxy

        return proxies if proxies else None


# 全局单例
anti_crawl = AntiCrawlManager()
