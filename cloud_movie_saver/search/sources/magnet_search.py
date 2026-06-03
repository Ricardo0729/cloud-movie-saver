"""磁力链接搜索引擎 - 使用BT搜索引擎"""

import re
from typing import List, Optional
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from ..base import BaseSource
from .. import SearchResult, MovieResource, MovieResourceType, MovieQuality, parse_quality_from_title
from . import register_source
from ...utils.anti_crawl import anti_crawl


@register_source("ciligou")
class BTDiggSource(BaseSource):
    """BTDigg / 磁力搜索引擎聚合"""

    name = "ciligou"
    display_name = "磁力搜索"
    base_url = "https://btlibrary.org"
    backup_urls = [
        "https://btdig.com",
        "https://btmet.com",
    ]
    encoding = "utf-8"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        results = []

        # 尝试多个BT搜索引擎
        engines = [
            self._search_btdig,
            self._search_btmet,
        ]

        for engine in engines:
            anti_crawl.random_delay(0.5, 2.0)
            try:
                result = engine(keyword)
                if result:
                    results.append(result)
            except Exception:
                continue

        return results

    def _search_btdig(self, keyword: str) -> Optional[SearchResult]:
        """通过btdig.com搜索"""
        encoded = quote(keyword)
        html = self.fetch(
            f"https://btdig.com/search?q={encoded}",
            headers=anti_crawl.get_headers(referer="https://btdig.com"),
        )
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        resources = []

        # btdig的搜索结果
        for result_div in soup.select(".search_result, .one_result, .result-item"):
            title_tag = result_div.select_one("a[href*='magnet:'], a[href*='/download/']")
            if not title_tag:
                continue

            magnet = title_tag.get("href", "")
            title = title_tag.get_text(strip=True) or title_tag.get("title", "")
            if magnet and magnet.startswith("magnet:"):
                resources.append(MovieResource(
                    title=title or "磁力链接",
                    url=magnet,
                    resource_type=MovieResourceType.MAGNET,
                    quality=parse_quality_from_title(title),
                ))

        # 备用: 直接提取所有磁力链接
        if not resources:
            for magnet_url in self.extract_magnet(html):
                resources.append(MovieResource(
                    title="磁力链接",
                    url=magnet_url,
                    resource_type=MovieResourceType.MAGNET,
                ))

        if resources:
            return self.create_result(
                movie_name=f"{keyword} - BT搜索引擎",
                resources=resources,
                source=self.display_name,
            )
        return None

    def _search_btmet(self, keyword: str) -> Optional[SearchResult]:
        """通过btmet.com搜索"""
        encoded = quote(keyword)
        html = self.fetch(
            f"https://btmet.com/search/{encoded}",
            headers=anti_crawl.get_headers(referer="https://btmet.com"),
        )
        if not html:
            return None

        resources = []
        for magnet_url in self.extract_magnet(html):
            resources.append(MovieResource(
                title="磁力链接",
                url=magnet_url,
                resource_type=MovieResourceType.MAGNET,
            ))

        if resources:
            return self.create_result(
                movie_name=f"{keyword} - BT元搜索",
                resources=resources,
                source=self.display_name,
            )
        return None


@register_source("btbtdy")
class BTDMovieSource(BaseSource):
    """BT电影资源站"""

    name = "btbtdy"
    display_name = "BT电影站"
    base_url = "https://www.btbtdy.com"
    backup_urls = []
    encoding = "utf-8"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        results = []
        html = self._do_search(keyword)
        if not html or len(html) < 500:
            return results

        soup = BeautifulSoup(html, "lxml")

        # 提取磁力链接
        resources = []
        for a_tag in soup.select("a[href*='magnet:']"):
            magnet_url = a_tag.get("href", "")
            if magnet_url:
                resources.append(MovieResource(
                    title=a_tag.get_text(strip=True) or "磁力链接",
                    url=magnet_url,
                    resource_type=MovieResourceType.MAGNET,
                ))

        if not resources:
            resources.extend(self.extract_magnet_link(html))

        if resources:
            results.append(self.create_result(
                movie_name=f"{keyword} - BT资源",
                resources=resources,
                source=self.display_name,
            ))

        return results

    def _do_search(self, keyword: str) -> Optional[str]:
        encoded = quote(keyword)
        return self.fetch(
            f"{self._current_base_url}/search/{encoded}.html",
            headers=anti_crawl.get_headers(referer=self._current_base_url),
        )

    def extract_magnet_link(self, text: str) -> List[MovieResource]:
        """提取磁力链接"""
        resources = []
        for magnet in self.extract_magnet(text):
            resources.append(MovieResource(
                title="磁力链接",
                url=magnet,
                resource_type=MovieResourceType.MAGNET,
            ))
        return resources


@register_source("btdig")
class BTDiggDirect(BaseSource):
    """BTDigg.com 直接搜索"""

    name = "btdig"
    display_name = "BTDigg"
    base_url = "https://btdig.com"
    backup_urls = []
    encoding = "utf-8"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        results = []
        encoded = quote(keyword)

        html = self.fetch(
            f"{self._current_base_url}/search?q={encoded}",
            headers=anti_crawl.get_headers(referer=self._current_base_url),
        )
        if not html:
            return results

        soup = BeautifulSoup(html, "lxml")
        resources = []

        for a_tag in soup.select("a[href*='magnet:']"):
            magnet = a_tag.get("href", "")
            title = a_tag.get_text(strip=True) or a_tag.get("title", "")
            if magnet:
                resources.append(MovieResource(
                    title=title or "磁力链接",
                    url=magnet,
                    resource_type=MovieResourceType.MAGNET,
                ))

        # 从seed信息中获取大小
        for result_div in soup.select(".search_result, .one_result"):
            size_tag = result_div.select_one(".size, .file-size")
            magnet_tag = result_div.select_one("a[href*='magnet:']")
            if magnet_tag and size_tag:
                size_text = size_tag.get_text(strip=True)
                for r in resources:
                    if r.url == magnet_tag.get("href", ""):
                        r.size = size_text
                        break

        if resources:
            results.append(self.create_result(
                movie_name=f"{keyword} - BTDigg",
                resources=resources,
                source=self.display_name,
            ))

        return results
