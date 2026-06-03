"""Web搜索聚合器 - 通过搜索引擎查找电影网盘资源"""

import re
import time
import random
from typing import List, Optional
from urllib.parse import quote, urlparse, parse_qs

from bs4 import BeautifulSoup
import httpx

from ..base import BaseSource
from .. import SearchResult, MovieResource, MovieResourceType, MovieQuality, parse_quality_from_title
from . import register_source
from ...utils.anti_crawl import anti_crawl


@register_source("bing")
class BingSearchSource(BaseSource):
    """通过Bing搜索查找电影网盘资源 - 不需要代理，国内可用"""

    name = "bing"
    display_name = "Bing搜索"
    base_url = "https://www.bing.com"
    backup_urls = ["https://cn.bing.com"]
    encoding = "utf-8"

    # 云盘链接模式
    CLOUD_PATTERNS = {
        'baidu': r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
        'quark': r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+',
        'xunlei': r'https?://pan\.xunlei\.com/s/[a-zA-Z0-9]+',
        'magnet': r'magnet:\?xt=urn:btih:[a-fA-F0-9]{40}(?:&[a-zA-Z0-9_.=%-]+)*',
    }

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        """通过Bing搜索电影网盘资源"""
        # 构建多个搜索查询，提高命中率
        search_queries = [
            f"{keyword} 百度网盘",
            f"{keyword} 夸克网盘 资源",
            f"{keyword} 磁力链接 下载",
        ]
        if quality:
            search_queries.insert(0, f"{keyword} {quality} 下载")

        all_resources = []
        all_urls = set()

        for query in search_queries[:3]:
            anti_crawl.random_delay(1.0, 3.0)
            try:
                result_urls = self._search_bing(query)
                for url in result_urls:
                    if url not in all_urls:
                        all_urls.add(url)
                        # 抓取每个结果页面，提取云盘链接
                        page_resources = self._crawl_page(url, keyword)
                        all_resources.extend(page_resources)
            except Exception:
                continue

        # 也直接从Bing搜索结果页面提取链接
        anti_crawl.random_delay(0.5, 1.5)
        try:
            direct_resources = self._search_direct(keyword)
            all_resources.extend(direct_resources)
        except Exception:
            pass

        # 去重
        seen = set()
        unique = []
        for r in all_resources:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        if unique:
            return [self.create_result(
                movie_name=f"{keyword} - 全网搜索",
                resources=unique,
                source=self.display_name,
            )]
        return []

    def _search_bing(self, query: str) -> List[str]:
        """在Bing上搜索，返回结果URL列表"""
        encoded = quote(query)
        urls_to_try = [
            f"https://cn.bing.com/search?q={encoded}",
            f"https://www.bing.com/search?q={encoded}",
        ]

        for search_url in urls_to_try:
            try:
                headers = anti_crawl.get_headers(referer="https://cn.bing.com")
                headers["Accept-Language"] = "zh-CN,zh;q=0.9"
                with httpx.Client(
                    timeout=httpx.Timeout(self.timeout),
                    follow_redirects=True,
                    headers=headers,
                    verify=False,
                ) as client:
                    resp = client.get(search_url)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "lxml")
                    result_urls = []

                    # Bing搜索结果
                    for result in soup.select("li.b_algo h2 a, .b_algo h2 a"):
                        href = result.get("href", "")
                        if href and href.startswith(("http://", "https://")):
                            result_urls.append(href)

                    return result_urls
            except Exception:
                continue

        return []

    def _crawl_page(self, url: str, keyword: str) -> List[MovieResource]:
        """抓取页面，提取云盘和磁力链接"""
        # 跳过搜索引擎自身页面
        skip_domains = ["bing.com", "baidu.com", "google.com", "sogou.com", "so.com"]
        if any(d in url.lower() for d in skip_domains):
            return []

        resources = []
        try:
            anti_crawl.random_delay(0.3, 1.0)
            headers = anti_crawl.get_headers(referer=url)
            with httpx.Client(
                timeout=httpx.Timeout(15),
                follow_redirects=True,
                headers=headers,
                verify=False,
            ) as client:
                resp = client.get(url)
                html = resp.text

                # 提取百度网盘链接
                for match in re.finditer(self.CLOUD_PATTERNS['baidu'], html):
                    link = match.group()
                    # 查找提取码
                    code = self._find_extract_code(html, match.start())
                    resources.append(MovieResource(
                        title="百度网盘",
                        url=link,
                        resource_type=MovieResourceType.BAIDU_CLOUD,
                        extra_info={"extract_code": code} if code else {},
                    ))

                # 提取夸克网盘链接
                for match in re.finditer(self.CLOUD_PATTERNS['quark'], html):
                    link = match.group()
                    resources.append(MovieResource(
                        title="夸克网盘",
                        url=link,
                        resource_type=MovieResourceType.QUARK_CLOUD,
                    ))

                # 提取迅雷网盘链接
                for match in re.finditer(self.CLOUD_PATTERNS['xunlei'], html):
                    link = match.group()
                    resources.append(MovieResource(
                        title="迅雷网盘",
                        url=link,
                        resource_type=MovieResourceType.XUNLEI_CLOUD,
                    ))

                # 提取磁力链接
                for match in re.finditer(self.CLOUD_PATTERNS['magnet'], html):
                    link = match.group()
                    resources.append(MovieResource(
                        title="磁力链接",
                        url=link,
                        resource_type=MovieResourceType.MAGNET,
                    ))

        except Exception:
            pass

        return resources

    def _search_direct(self, keyword: str) -> List[MovieResource]:
        """直接从Bing搜索结果的摘要中提取链接"""
        resources = []
        encoded = quote(f"{keyword} 百度网盘 OR 夸克网盘 OR 磁力")

        try:
            headers = anti_crawl.get_headers(referer="https://cn.bing.com")
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers, verify=False) as client:
                resp = client.get(f"https://cn.bing.com/search?q={encoded}")
                if resp.status_code == 200:
                    # 从搜索结果文本中提取链接
                    for provider, pattern in self.CLOUD_PATTERNS.items():
                        for match in re.finditer(pattern, resp.text):
                            link = match.group()
                            provider_name = {"baidu": "百度网盘", "quark": "夸克网盘", "xunlei": "迅雷网盘", "magnet": "磁力链接"}.get(provider, provider)
                            rtype = {
                                "baidu": MovieResourceType.BAIDU_CLOUD,
                                "quark": MovieResourceType.QUARK_CLOUD,
                                "xunlei": MovieResourceType.XUNLEI_CLOUD,
                                "magnet": MovieResourceType.MAGNET,
                            }.get(provider, MovieResourceType.MAGNET)

                            resources.append(MovieResource(
                                title=provider_name,
                                url=link,
                                resource_type=rtype,
                            ))
        except Exception:
            pass

        return resources

    def _find_extract_code(self, html: str, link_pos: int) -> str:
        """在链接附近查找提取码"""
        start = max(0, link_pos - 300)
        end = min(len(html), link_pos + 300)
        nearby = html[start:end]

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


@register_source("sogou")
class SogouSearchSource(BaseSource):
    """通过搜狗搜索查找电影资源 - 国内可用"""

    name = "sogou"
    display_name = "搜狗搜索"
    base_url = "https://www.sogou.com"
    backup_urls = []
    encoding = "utf-8"

    CLOUD_PATTERNS = {
        'baidu': r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
        'quark': r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+',
        'magnet': r'magnet:\?xt=urn:btih:[a-fA-F0-9]{40}(?:&[a-zA-Z0-9_.=%-]+)*',
    }

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        query = f"{keyword} 电影下载"
        if quality:
            query = f"{keyword} {quality}"
        resources = []

        try:
            encoded = quote(query)
            headers = anti_crawl.get_headers(referer=self._current_base_url)
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers, verify=False) as client:
                resp = client.get(f"https://www.sogou.com/web?query={encoded}")
                if resp.status_code == 200:
                    # 直接搜索链接
                    for provider, pattern in self.CLOUD_PATTERNS.items():
                        for match in re.finditer(pattern, resp.text):
                            link = match.group()
                            rtype = {"baidu": MovieResourceType.BAIDU_CLOUD, "quark": MovieResourceType.QUARK_CLOUD, "magnet": MovieResourceType.MAGNET}.get(provider, MovieResourceType.MAGNET)
                            resources.append(MovieResource(
                                title=f"{'百度网盘' if provider=='baidu' else '夸克网盘' if provider=='quark' else '磁力链接'}",
                                url=link,
                                resource_type=rtype,
                            ))

                    # 提取结果页面中的链接并抓取
                    soup = BeautifulSoup(resp.text, "lxml")
                    for result in soup.select(".vrwrap a[href], .result a[href], .rb a[href]"):
                        href = result.get("href", "")
                        if href and href.startswith(("http://", "https://")):
                            if any(s in href for s in ["sogou.com", "bing.com", "google"]):
                                continue
                            # 获取实际URL（搜狗跳转）
                            if "/link?" in href:
                                try:
                                    parsed = urlparse(href)
                                    params = parse_qs(parsed.query)
                                    href = params.get("url", [params.get("u", [""])])[0]
                                except Exception:
                                    pass

                            if href and href.startswith(("http://", "https://")):
                                page_resources = self._crawl_page(href)
                                resources.extend(page_resources)
        except Exception:
            pass

        seen = set()
        unique = []
        for r in resources:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        if unique:
            return [self.create_result(
                movie_name=f"{keyword} - 全网搜索",
                resources=unique,
                source=self.display_name,
            )]
        return []

    def _crawl_page(self, url: str) -> List[MovieResource]:
        resources = []
        try:
            anti_crawl.random_delay(0.3, 1.0)
            with httpx.Client(timeout=15, follow_redirects=True, verify=False) as client:
                resp = client.get(url, headers=anti_crawl.get_headers(referer=url))
                html = resp.text
                for provider, pattern in self.CLOUD_PATTERNS.items():
                    for match in re.finditer(pattern, html):
                        link = match.group()
                        rtype = {"baidu": MovieResourceType.BAIDU_CLOUD, "quark": MovieResourceType.QUARK_CLOUD, "magnet": MovieResourceType.MAGNET}.get(provider, MovieResourceType.MAGNET)
                        resources.append(MovieResource(
                            title="网盘资源",
                            url=link,
                            resource_type=rtype,
                        ))
        except Exception:
            pass
        return resources
