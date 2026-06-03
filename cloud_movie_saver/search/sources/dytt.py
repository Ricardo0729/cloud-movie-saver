"""电影天堂 (dytt8899.com / dy2018.com) 搜索源"""

import re
import time
from typing import List, Optional
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from ..base import BaseSource
from .. import SearchResult, MovieResource, MovieResourceType, MovieQuality, parse_quality_from_title
from . import register_source
from ...utils.anti_crawl import anti_crawl


@register_source("dytt")
class DyttSource(BaseSource):
    """电影天堂搜索源 - 支持多个镜像域名自动切换"""

    name = "dytt"
    display_name = "电影天堂"
    base_url = "https://www.dytt8899.com"
    backup_urls = [
        "https://www.dytt8899.com",
        "https://www.ygdy8.com",
        "https://www.dy2018.com",
        "https://www.dytt8.net",
        "https://www.dytt89.com",
    ]
    encoding = "gb2312"

    def __init__(self):
        super().__init__()
        self._active_url = self._find_active_url()

    def _find_active_url(self) -> str:
        """查找可用的域名（跟随重定向）"""
        import httpx
        headers = {"User-Agent": anti_crawl.get_random_ua()}
        for url in [self.base_url] + self.backup_urls:
            try:
                with httpx.Client(timeout=10, follow_redirects=True, verify=False) as client:
                    resp = client.get(url, headers=headers)
                    final_url = str(resp.url).rstrip("/")
                    if resp.status_code == 200:
                        self._current_base_url = final_url
                        return final_url
            except Exception:
                continue
        return self.base_url

    def search(self, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        """搜索电影资源"""
        results = []

        # 策略1: 通过首页分类浏览 + 关键词匹配（绕过搜索限制）
        try:
            results.extend(self._search_via_browse(keyword))
        except Exception:
            pass

        # 如果策略1没结果，尝试策略2: 直接搜索详情页
        if not results:
            try:
                html = self._direct_search(keyword)
                if html:
                    results.extend(self._parse_search_page(html, keyword))
            except Exception:
                pass

        return results

    def _search_via_browse(self, keyword: str) -> List[SearchResult]:
        """通过浏览分类页 + 关键词匹配来搜索（绕过搜索反爬）"""
        results = []
        # 电影天堂的页码结构: /[categoryid]/ (最新), /[categoryid]/index_2.html, etc.
        categories = [4, 1, 0, 2, 3, 8, 5, 7, 14, 15]  # 科幻/喜剧/剧情/动作/爱情/恐怖/动画/惊悚/战争/犯罪

        for cat_id in categories:
            anti_crawl.random_delay(0.5, 1.5)
            for page in range(1, 4):  # 每类看3页
                try:
                    if page == 1:
                        url = f"{self._active_url}/{cat_id}/"
                    else:
                        url = f"{self._active_url}/{cat_id}/index_{page}.html"

                    html = self.fetch(url, headers=anti_crawl.get_headers(referer=self._active_url))
                    if not html:
                        continue

                    soup = BeautifulSoup(html, "lxml")
                    for a_tag in soup.select("a[href]"):
                        href = a_tag.get("href", "")
                        text = a_tag.get_text(strip=True)
                        if not href or not text or len(text) < 4:
                            continue
                        if keyword.lower() in text.lower():
                            if not href.startswith("http"):
                                href = urljoin(self._active_url, href)
                            # 避免重复
                            if any(r.movie_name == text for r in results):
                                continue

                            anti_crawl.random_delay(0.3, 0.8)
                            detail_html = self.fetch(href, referer=url)
                            if detail_html:
                                detail_soup = BeautifulSoup(detail_html, "lxml")
                                result = self._parse_detail_page(detail_soup, text, href)
                                if result:
                                    results.append(result)
                except Exception:
                    continue

                if len(results) >= 10:  # 找到足够结果就停止
                    break
            if len(results) >= 10:
                break

        return results

    def _direct_search(self, keyword: str) -> Optional[str]:
        """直接尝试搜索"""
        encoded = quote(keyword)
        search_urls = [
            f"{self._active_url}/e/search/index.php",
            f"{self._active_url}/plus/search.php",
        ]

        headers = anti_crawl.get_headers(referer=self._active_url)
        proxies = anti_crawl.get_proxies()

        import httpx

        # 先访问首页获取cookies
        try:
            with httpx.Client(timeout=15, follow_redirects=True, verify=False) as c:
                c.get(self._active_url, headers=headers)
                # 然后用这个session搜索
                search_data = {
                    "keyboard": keyword,
                    "show": "title",
                    "tempid": 1,
                    "tbname": "article",
                    "submit": "搜索",
                }
                resp = c.post(
                    search_urls[0],
                    data=search_data,
                    headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                )
                resp.encoding = self.encoding
                if resp.status_code == 200 and len(resp.text) > 2000:
                    return resp.text
        except Exception:
            pass

        return None

    def _parse_search_page(self, html: str, keyword: str) -> List[SearchResult]:
        """解析搜索页面"""
        results = []
        soup = BeautifulSoup(html, "lxml")

        # 提取搜索结果中的链接
        links = []
        for a_tag in soup.select("a[href]"):
            href = a_tag.get("href", "")
            text = a_tag.get_text(strip=True)
            if href and text and len(text) > 4:
                if not href.startswith("http"):
                    href = urljoin(self._active_url, href)
                links.append((text, href))

        # 去重
        seen = set()
        unique_links = []
        for text, href in links:
            if href not in seen:
                seen.add(href)
                unique_links.append((text, href))

        for text, href in unique_links[:15]:
            anti_crawl.random_delay(0.3, 1.0)
            try:
                detail_html = self.fetch(href, referer=self._active_url)
                if not detail_html:
                    continue
                detail_soup = BeautifulSoup(detail_html, "lxml")
                result = self._parse_detail_page(detail_soup, text, href)
                if result:
                    results.append(result)
            except Exception:
                continue

        return results

    def _parse_detail_page(self, soup: BeautifulSoup, title: str, url: str) -> Optional[SearchResult]:
        """解析电影详情页"""
        try:
            # 查找下载链接区域
            page_text = soup.get_text(" ", strip=True)
            all_resources = []

            # 方法1: 查找下载区
            for selector in [".downlist", ".download", "#downlist", ".down",
                             ".intro", ".co_content8", ".p_downlinks"]:
                area = soup.select_one(selector)
                if area:
                    area_text = area.get_text(" ", strip=True)
                    all_resources.extend(self.extract_all_links(area_text))

            # 方法2: 从全文提取
            all_resources.extend(self.extract_all_links(page_text))

            # 方法3: 提取所有a标签中的链接
            for a_tag in soup.select("a[href]"):
                href = a_tag.get("href", "").strip()
                if not href:
                    continue
                # FTP/HTTP直链
                if href.startswith(("ftp://", "http://", "https://")) and any(
                    ext in href.lower() for ext in ['.mp4', '.mkv', '.avi', '.rmvb', '.wmv', '.ts']
                ):
                    all_resources.append(MovieResource(
                        title=a_tag.get_text(strip=True) or "下载",
                        url=href,
                        resource_type=MovieResourceType.DIRECT,
                    ))
                # Thunder links
                elif href.startswith("thunder://"):
                    all_resources.append(MovieResource(
                        title="迅雷下载",
                        url=href,
                        resource_type=MovieResourceType.THUNDER,
                    ))

            # 去重
            seen = set()
            unique = []
            for r in all_resources:
                if r.url not in seen:
                    seen.add(r.url)
                    unique.append(r)

            if not unique:
                return None

            # 获取title标签
            page_title = ""
            if soup.find("title"):
                page_title = soup.find("title").get_text(strip=True)

            movie_name = title or page_title
            movie_name = re.sub(r'<[^>]+>', '', movie_name).strip()
            movie_name = re.sub(r'最新电影|迅雷下载|免费下载|高清下载', '', movie_name).strip()

            # 提取年份
            year = ""
            year_match = re.search(r'(20\d{2})', movie_name or "")
            if year_match:
                year = year_match.group(1)

            result = self.create_result(
                movie_name=movie_name,
                resources=unique,
                source=self.display_name,
                year=year,
            )
            return result

        except Exception:
            return None
