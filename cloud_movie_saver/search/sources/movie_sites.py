"""综合电影资源站点搜索源 - 片库网、6v电影、高清MP4、BT猫等"""

import re
import time
from typing import List, Optional, Dict
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from ..base import BaseSource
from .. import SearchResult, MovieResource, MovieResourceType, MovieQuality, parse_quality_from_title
from . import register_source
from ...utils.anti_crawl import anti_crawl


@register_source("6vhao")
class SixVSource(BaseSource):
    """6v电影搜索源 (6vhao.net)"""

    name = "6vhao"
    display_name = "6v电影"
    base_url = "https://www.6vhao.net"
    backup_urls = [
        "https://www.6vhao.tv",
        "https://www.6vdy.com",
        "https://www.6vhao.org",
    ]
    encoding = "gb2312"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        results = []
        # 6v电影搜索会被限制，改用分类浏览+关键词匹配
        try:
            results.extend(self._browse_search(keyword))
        except Exception:
            pass
        return results

    def _browse_search(self, keyword: str) -> List[SearchResult]:
        """通过浏览分类页搜索"""
        results = []
        categories = [1, 2, 3, 4, 5, 6]  # 电影分类ID

        for cat_id in categories:
            anti_crawl.random_delay(0.5, 1.5)
            for page in range(3):
                try:
                    if page == 0:
                        url = f"{self._current_base_url}/list/{cat_id}.html"
                    else:
                        url = f"{self._current_base_url}/list/{cat_id}_{page}.html"

                    html = self.fetch(url, headers=anti_crawl.get_headers(referer=self._current_base_url))
                    if not html:
                        continue

                    soup = BeautifulSoup(html, "lxml")
                    for a_tag in soup.select("a[href]"):
                        href = a_tag.get("href", "")
                        text = a_tag.get_text(strip=True)
                        if not href or not text:
                            continue
                        if keyword.lower() in text.lower() and len(text) > 4:
                            if not href.startswith("http"):
                                href = urljoin(self._current_base_url, href)

                            anti_crawl.random_delay(0.3, 0.8)
                            detail_html = self.fetch(href, referer=url)
                            if detail_html:
                                detail_soup = BeautifulSoup(detail_html, "lxml")
                                result = self._parse_detail(detail_soup, text)
                                if result:
                                    result.source = self.display_name
                                    results.append(result)
                except Exception:
                    continue

                if len(results) >= 8:
                    break
            if len(results) >= 8:
                break

        return results

    def _parse_detail(self, soup: BeautifulSoup, title: str) -> Optional[SearchResult]:
        """解析详情页"""
        try:
            page_text = soup.get_text(" ", strip=True)
            resources = self.extract_all_links(page_text)

            # 6v电影特有的FTP/ED2K区域
            for a_tag in soup.select("a[href^='ftp://']"):
                resources.append(MovieResource(
                    title="FTP下载",
                    url=a_tag.get("href", ""),
                    resource_type=MovieResourceType.DIRECT,
                ))

            seen = set()
            unique = []
            for r in resources:
                if r.url not in seen:
                    seen.add(r.url)
                    unique.append(r)

            if not unique:
                return None

            year = ""
            year_match = re.search(r'(20\d{2})', title)
            if year_match:
                year = year_match.group(1)

            return self.create_result(
                movie_name=title, resources=unique,
                source=self.display_name, year=year
            )
        except Exception:
            return None


@register_source("btcat")
class BTCatSource(BaseSource):
    """BT猫搜索源"""

    name = "btcat"
    display_name = "BT猫"
    base_url = "https://www.btcat.org"
    backup_urls = [
        "https://btcat.org",
        "https://www.btcat.me",
        "https://www.btcat.cc",
    ]
    encoding = "utf-8"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        results = []
        html = self._search_site(keyword)
        if not html:
            return results

        # BT猫可能返回JS跳转，检查并处理
        soup = BeautifulSoup(html, "lxml")

        # 直接从页面提取磁力链接
        resources = []
        for a_tag in soup.select("a[href*='magnet:']"):
            resources.append(MovieResource(
                title=a_tag.get_text(strip=True) or "磁力链接",
                url=a_tag.get("href", ""),
                resource_type=MovieResourceType.MAGNET,
            ))

        # 从全文提取
        resources.extend([r for r in self.extract_all_links(html) if r.resource_type == MovieResourceType.MAGNET])

        seen = set()
        unique = []
        for r in resources:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        if unique:
            results.append(self.create_result(
                movie_name=f"{keyword} - BT猫搜索结果",
                resources=unique,
                source=self.display_name,
            ))

        return results

    def _search_site(self, keyword: str) -> Optional[str]:
        """搜索BT猫"""
        encoded = quote(keyword)
        urls = [
            f"{self._current_base_url}/search/{encoded}",
            f"{self._current_base_url}/s/{encoded}.html",
            f"{self._current_base_url}/search?q={encoded}",
        ]
        for url in urls:
            html = self.fetch(url, headers=anti_crawl.get_headers(referer=self._current_base_url))
            if html and len(html) > 1000:
                return html
        return None


@register_source("gaoding")
class GaoQingSource(BaseSource):
    """高清MP4吧 - 专注百度网盘资源"""

    name = "gaoding"
    display_name = "高清MP4"
    base_url = "https://www.gaoqingmp4.com"
    backup_urls = [
        "https://gaoqingmp4.com",
    ]
    encoding = "utf-8"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        results = []
        html = self._do_search(keyword)
        if not html:
            return results

        soup = BeautifulSoup(html, "lxml")
        items = self._extract_items(soup)

        for item in items[:10]:
            anti_crawl.random_delay(0.5, 1.5)
            try:
                detail_html = self.fetch(item["url"], referer=self._current_base_url)
                if not detail_html:
                    continue
                detail_soup = BeautifulSoup(detail_html, "lxml")
                result = self._parse_detail(detail_soup, item)
                if result:
                    results.append(result)
            except Exception:
                continue

        return results

    def _do_search(self, keyword: str) -> Optional[str]:
        encoded = quote(keyword)
        urls = [
            f"{self._current_base_url}/search/{encoded}",
            f"{self._current_base_url}/?s={encoded}",
        ]
        for url in urls:
            html = self.fetch(url, headers=anti_crawl.get_headers(referer=self._current_base_url))
            if html and "404" not in html[:100] and len(html) > 1000:
                return html
        return None

    def _extract_items(self, soup: BeautifulSoup) -> List[dict]:
        items = []
        for a_tag in soup.select("article a[href], .post a[href], h2 a[href], .entry-title a[href], .search-item a"):
            href = a_tag.get("href", "")
            title = a_tag.get_text(strip=True) or a_tag.get("title", "")
            # 过滤非内容链接
            if href and title and len(title) > 4 and href != "#":
                if not href.startswith("http"):
                    href = urljoin(self._current_base_url, href)
                if href not in [i["url"] for i in items]:
                    items.append({"title": title, "url": href})
        return items

    def _parse_detail(self, soup: BeautifulSoup, item: dict) -> Optional[SearchResult]:
        try:
            page_text = soup.get_text(" ", strip=True)
            resources = self.extract_all_links(page_text)

            # 高清MP4重点提取百度网盘链接
            from ...cloud.extractor import CloudLinkExtractor
            cloud_links = CloudLinkExtractor.extract_baidu(page_text)
            for cl in cloud_links:
                if cl.url not in [r.url for r in resources]:
                    resources.append(MovieResource(
                        title="百度网盘",
                        url=cl.url,
                        resource_type=MovieResourceType.BAIDU_CLOUD,
                        extra_info={"extract_code": cl.extract_code} if cl.extract_code else {},
                    ))

            seen = set()
            unique = []
            for r in resources:
                if r.url not in seen:
                    seen.add(r.url)
                    unique.append(r)

            if not unique:
                return None

            movie_name = item["title"]
            year = re.search(r'(20\d{2})', movie_name)
            return self.create_result(
                movie_name=movie_name, resources=unique,
                source=self.display_name,
                year=year.group(1) if year else ""
            )
        except Exception:
            return None


@register_source("pianku")
class PiankuSource(BaseSource):
    """片库搜索源"""

    name = "pianku"
    display_name = "片库资源"
    base_url = "https://www.pianku.tv"
    backup_urls = []
    encoding = "utf-8"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        return []


@register_source("6vhao_alt")
class SixVAltSource(BaseSource):
    """6v电影替代搜索"""

    name = "6vhao_alt"
    display_name = "6v资源"
    base_url = "https://www.6vdy.com"
    backup_urls = ["https://www.6vhao.net"]
    encoding = "gb2312"

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        return []
