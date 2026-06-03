"""BT天堂 & BT搜索引擎 - 使用聚合搜索"""

import re
from typing import List, Optional
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from ..base import BaseSource
from .. import SearchResult, MovieResource, MovieResourceType, MovieQuality
from . import register_source
from ...utils.anti_crawl import anti_crawl


@register_source("bttiantang")
class BTSearchSource(BaseSource):
    """BT综合搜索引擎 - 聚合多个BT站点"""

    name = "bttiantang"
    display_name = "BT搜索"
    base_url = "https://www.btbtt.us"
    backup_urls = [
        "https://www.btschool.org",
        "https://btwiki.org",
    ]
    encoding = "utf-8"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        results = []

        # 使用btbtt.us搜索（一个BT资源站）
        try:
            r = self._search_btbtt(keyword)
            results.extend(r)
        except Exception:
            pass

        return results

    def _search_btbtt(self, keyword: str) -> List[SearchResult]:
        """通过btbtt.us搜索"""
        results = []
        encoded = quote(keyword)

        urls_to_try = [
            f"{self._current_base_url}/search/{encoded}",
            f"{self._current_base_url}/search.php?keyword={encoded}",
        ]

        html = None
        for url in urls_to_try:
            html = self.fetch(url, headers=anti_crawl.get_headers(referer=self._current_base_url))
            if html and len(html) > 500:
                break
        if not html:
            return results

        soup = BeautifulSoup(html, "lxml")

        # 提取所有磁力链接
        magnets = []
        for a_tag in soup.select("a[href*='magnet:']"):
            magnet_url = a_tag.get("href", "").strip()
            if magnet_url:
                text = a_tag.get_text(strip=True) or a_tag.get("title", "")
                magnets.append(MovieResource(
                    title=text or "磁力链接",
                    url=magnet_url,
                    resource_type=MovieResourceType.MAGNET,
                    quality=parse_quality_from_title(text),
                ))

        # 从全文提取磁力链接
        html_magnets = self.extract_magnet(html)
        for magnet in html_magnets:
            if magnet not in [r.url for r in magnets]:
                magnets.append(MovieResource(
                    title="磁力链接",
                    url=magnet,
                    resource_type=MovieResourceType.MAGNET,
                ))

        if magnets:
            results.append(self.create_result(
                movie_name=f"{keyword} - BT搜索结果",
                resources=magnets,
                source=self.display_name,
            ))

        return results


def parse_quality_from_title(title: str) -> MovieQuality:
    """从标题解析画质"""
    title_lower = title.lower()
    if "4k" in title_lower or "2160p" in title_lower or "uhd" in title_lower:
        return MovieQuality.UHD_4K
    if "1080p" in title_lower or "1080" in title_lower:
        return MovieQuality.FULL_HD_1080P
    if "720p" in title_lower or "720" in title_lower:
        return MovieQuality.HD_720P
    if "蓝光" in title_lower or "bluray" in title_lower or "blu-ray" in title_lower:
        return MovieQuality.BLURAY
    if "高清" in title_lower or "hd" in title_lower:
        return MovieQuality.HD_720P
    return MovieQuality.UNKNOWN
