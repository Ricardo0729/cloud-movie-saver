"""搜索源基类 - 所有搜索源需要继承此类"""

import re
import abc
from typing import List, Optional, Dict
from urllib.parse import quote, urlparse, urljoin

import httpx

from ..utils.config import config
from ..utils.anti_crawl import anti_crawl
from . import SearchResult, MovieResource, MovieResourceType, MovieQuality, parse_quality_from_title


class BaseSource(abc.ABC):
    """搜索源基类"""

    # 源名称
    name: str = "base"
    # 显示名称
    display_name: str = "基础源"
    # 基础URL
    base_url: str = ""
    # 备用URL列表
    backup_urls: List[str] = []
    # 编码
    encoding: str = "utf-8"

    def __init__(self):
        self._current_base_url = self.base_url
        self.timeout = config.get("search.timeout", 30)
        self.max_retries = config.get("search.max_retries", 3)
        self.use_curl = config.get("search.anti_crawl.use_curl_impersonate", True)

    @abc.abstractmethod
    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        """搜索电影资源"""
        ...

    def build_url(self, keyword: str) -> str:
        """构建搜索URL"""
        encoded = quote(keyword)
        return f"{self._current_base_url}/search/{encoded}"

    def _get_httpx_client(self) -> httpx.Client:
        """获取httpx客户端"""
        return anti_crawl.create_httpx_client(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
            headers=anti_crawl.get_headers(referer=self._current_base_url),
        )

    def _get_async_client_kwargs(self) -> dict:
        """获取异步客户端参数"""
        kwargs = {
            "timeout": httpx.Timeout(self.timeout),
            "follow_redirects": True,
            "headers": anti_crawl.get_headers(referer=self._current_base_url),
        }
        proxy_url = anti_crawl.get_proxy_url()
        if proxy_url:
            kwargs["proxy"] = proxy_url
        return kwargs

    def fetch(self, url: str, referer: Optional[str] = None,
              headers: Optional[Dict] = None) -> Optional[str]:
        """获取页面内容"""
        if headers is None:
            headers = anti_crawl.get_headers(referer=referer or self._current_base_url)

        proxy_url = anti_crawl.get_proxy_url()

        for attempt in range(self.max_retries):
            try:
                client_kwargs = {
                    "timeout": httpx.Timeout(self.timeout),
                    "follow_redirects": True,
                    "headers": headers,
                    "verify": False,
                }
                if proxy_url:
                    client_kwargs["proxy"] = proxy_url

                with httpx.Client(**client_kwargs) as client:
                    response = client.get(url)
                    response.encoding = self.encoding
                    if response.status_code == 200:
                        return response.text
                    elif response.status_code == 404:
                        return None
                    elif response.status_code in (403, 429):
                        anti_crawl.random_delay(2.0, 5.0)
                        continue
            except Exception as e:
                if attempt < self.max_retries - 1:
                    anti_crawl.random_delay(1.0, 3.0)
                    continue
        return None

    async def fetch_async(self, url: str, referer: Optional[str] = None,
                          headers: Optional[Dict] = None) -> Optional[str]:
        """异步获取页面内容"""
        if headers is None:
            headers = anti_crawl.get_headers(referer=referer or self._current_base_url)

        proxy_url = anti_crawl.get_proxy_url()

        for attempt in range(self.max_retries):
            try:
                client_kwargs = {
                    "timeout": httpx.Timeout(self.timeout),
                    "follow_redirects": True,
                    "headers": headers,
                    "verify": False,
                }
                if proxy_url:
                    client_kwargs["proxy"] = proxy_url

                async with httpx.AsyncClient(**client_kwargs) as client:
                    response = await client.get(url)
                    response.encoding = self.encoding
                    if response.status_code == 200:
                        return response.text
                    elif response.status_code == 404:
                        return None
                    elif response.status_code in (403, 429):
                        await anti_crawl.random_delay_async(2.0, 5.0)
                        continue
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await anti_crawl.random_delay_async(1.0, 3.0)
                    continue
        return None

    def extract_magnet(self, text: str) -> List[str]:
        """从文本中提取磁力链接"""
        # 标准magnet链接
        magnets = re.findall(
            r'magnet:\?xt=urn:btih:[a-zA-Z0-9]{32,}(?:&[a-zA-Z0-9_.=%-]+)*',
            text
        )
        # 带dn参数的完整magnet
        magnets2 = re.findall(
            r'magnet:\?xt=urn:btih:[a-fA-F0-9]{40}(?:&[a-zA-Z0-9_.=%-]+)*',
            text
        )
        all_magnets = list(set(magnets + magnets2))
        # 清理和标准化
        cleaned = []
        for m in all_magnets:
            m = m.strip().strip('"').strip("'").strip("</a>")
            if m not in cleaned:
                cleaned.append(m)
        return cleaned

    def extract_ed2k(self, text: str) -> List[str]:
        """从文本中提取电驴链接"""
        ed2k_links = re.findall(
            r'ed2k://\|file\|[^\|]+\|[0-9]+\|[a-fA-F0-9]+\|/',
            text
        )
        return list(set(ed2k_links))

    def extract_thunder(self, text: str) -> List[str]:
        """从文本中提取迅雷链接"""
        thunder_links = re.findall(
            r'thunder://[a-zA-Z0-9+/=]+',
            text
        )
        return list(set(thunder_links))

    def extract_baidu_links(self, text: str) -> List[str]:
        """提取百度网盘分享链接"""
        patterns = [
            r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
            r'https?://yun\.baidu\.com/s/[a-zA-Z0-9_-]+',
            # 带提取码的格式
            r'链接[:：]\s*https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
        ]
        links = []
        for pattern in patterns:
            links.extend(re.findall(pattern, text))
        return list(set(links))

    def extract_quark_links(self, text: str) -> List[str]:
        """提取夸克网盘分享链接"""
        patterns = [
            r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+',
            r'https?://quark\.cn/s/[a-zA-Z0-9]+',
        ]
        links = []
        for pattern in patterns:
            links.extend(re.findall(pattern, text))
        return list(set(links))

    def extract_xunlei_links(self, text: str) -> List[str]:
        """提取迅雷网盘分享链接"""
        patterns = [
            r'https?://pan\.xunlei\.com/s/[a-zA-Z0-9]+',
            r'https?://www\.xunlei\.com/s/[a-zA-Z0-9]+',
        ]
        links = []
        for pattern in patterns:
            links.extend(re.findall(pattern, text))
        return list(set(links))

    def extract_extract_code(self, text: str, link: str) -> str:
        """提取网盘提取码"""
        # 在链接附近查找提取码
        idx = text.find(link)
        if idx == -1:
            return ""
        nearby = text[idx:idx + 500]

        patterns = [
            r'提取码[:：]?\s*([a-zA-Z0-9]{4})',
            r'密码[:：]?\s*([a-zA-Z0-9]{4})',
            r'提取码[:：]?\s*([a-zA-Z0-9]{6,8})',
            r'密码[:：]?\s*([a-zA-Z0-9]{6,8})',
        ]
        for pattern in patterns:
            match = re.search(pattern, nearby)
            if match:
                return match.group(1)
        return ""

    def extract_all_links(self, text: str) -> List[MovieResource]:
        """从文本中提取所有类型的链接"""
        resources = []

        # 磁力链接
        for magnet in self.extract_magnet(text):
            resources.append(MovieResource(
                title="磁力链接",
                url=magnet,
                resource_type=MovieResourceType.MAGNET,
            ))

        # 电驴链接
        for ed2k in self.extract_ed2k(text):
            resources.append(MovieResource(
                title="电驴链接",
                url=ed2k,
                resource_type=MovieResourceType.ED2K,
            ))

        # 百度网盘
        for link in self.extract_baidu_links(text):
            code = self.extract_extract_code(text, link)
            resources.append(MovieResource(
                title="百度网盘",
                url=link,
                resource_type=MovieResourceType.BAIDU_CLOUD,
                extra_info={"extract_code": code} if code else {},
            ))

        # 夸克网盘
        for link in self.extract_quark_links(text):
            code = self.extract_extract_code(text, link)
            resources.append(MovieResource(
                title="夸克网盘",
                url=link,
                resource_type=MovieResourceType.QUARK_CLOUD,
                extra_info={"extract_code": code} if code else {},
            ))

        # 迅雷网盘
        for link in self.extract_xunlei_links(text):
            code = self.extract_extract_code(text, link)
            resources.append(MovieResource(
                title="迅雷网盘",
                url=link,
                resource_type=MovieResourceType.XUNLEI_CLOUD,
                extra_info={"extract_code": code} if code else {},
            ))

        return resources

    def create_result(self, movie_name: str, resources: List[MovieResource],
                      source: str = "", description: str = "",
                      year: str = "", poster: str = "",
                      rating: float = 0.0) -> SearchResult:
        """创建搜索结果"""
        # 从标题推断画质
        for resource in resources:
            if resource.quality == MovieQuality.UNKNOWN:
                resource.quality = parse_quality_from_title(movie_name)

        return SearchResult(
            movie_name=movie_name,
            year=year,
            resources=resources,
            source=source or self.display_name,
            description=description,
            poster_url=poster,
            rating=rating,
        )

    def is_accessible(self) -> bool:
        """检查源是否可访问"""
        try:
            html = self.fetch(self._current_base_url)
            return html is not None
        except Exception:
            return False
