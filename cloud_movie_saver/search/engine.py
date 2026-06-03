"""搜索引擎 - 协调多个搜索源进行搜索"""

import asyncio
import concurrent.futures
from typing import List, Optional, Dict
from datetime import datetime

from ..utils.config import config
from ..utils.anti_crawl import anti_crawl
from . import SearchResult, SearchResultSet, MovieQuality, MovieResourceType
from .sources import get_source, get_all_sources, get_source_names


class SearchEngine:
    """搜索引擎 - 聚合多个搜索源"""

    def __init__(self):
        self.source_names = config.get("search.source_priority", get_source_names())
        self.concurrent = config.get("search.concurrent", 5)
        self.min_quality_str = config.get("search.min_quality", "720p")
        self.prefer_quality_str = config.get("search.prefer_quality", "1080p")
        self.min_quality = self._parse_quality(self.min_quality_str)
        self.prefer_quality = self._parse_quality(self.prefer_quality_str)

    def _parse_quality(self, q: str) -> MovieQuality:
        """解析画质字符串"""
        mapping = {
            "480p": MovieQuality.SD_480P,
            "720p": MovieQuality.HD_720P,
            "1080p": MovieQuality.FULL_HD_1080P,
            "2k": MovieQuality.QHD_2K,
            "4k": MovieQuality.UHD_4K,
            "bluray": MovieQuality.BLURAY,
            "remux": MovieQuality.REMUX,
        }
        return mapping.get(q.lower(), MovieQuality.HD_720P)

    def search(self, keyword: str, quality: Optional[str] = None,
               sources: Optional[List[str]] = None) -> SearchResultSet:
        """搜索电影资源（同步，多线程并发）"""
        result_set = SearchResultSet()
        sources_to_use = sources or self.source_names

        # 过滤可用源
        available_sources = []
        for name in sources_to_use:
            try:
                source = get_source(name)
                available_sources.append(source)
            except (ValueError, Exception) as e:
                continue

        if not available_sources:
            return result_set

        # 使用线程池并发搜索
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            future_to_source = {
                executor.submit(self._search_single, source, keyword, quality): source
                for source in available_sources
            }

            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    results = future.result()
                    if results:
                        result_set.extend(results)
                except Exception as e:
                    continue

        # 按画质排序
        result_set.sort_by_quality()
        return result_set

    async def search_async(self, keyword: str, quality: Optional[str] = None,
                           sources: Optional[List[str]] = None) -> SearchResultSet:
        """搜索电影资源（异步）"""
        result_set = SearchResultSet()
        sources_to_use = sources or self.source_names

        tasks = []
        for name in sources_to_use:
            try:
                source = get_source(name)
                tasks.append(self._search_single_async(source, keyword, quality))
            except ValueError:
                continue

        if not tasks:
            return result_set

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        for results in results_lists:
            if isinstance(results, Exception):
                continue
            if results:
                result_set.extend(results)

        result_set.sort_by_quality()
        return result_set

    def _search_single(self, source, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        """单个源搜索（同步）"""
        try:
            anti_crawl.random_delay(0.3, 1.0)
            results = source.search(keyword, quality)
            # 过滤和标记
            for result in results:
                # 标记来源
                result.source = source.display_name
                # 过滤低画质资源
                result.resources = [
                    r for r in result.resources
                    if self._quality_score(r.quality) >= self._quality_score(self.min_quality)
                ]
            return [r for r in results if r.resources]
        except Exception as e:
            return []

    async def _search_single_async(self, source, keyword: str, quality: Optional[str] = None) -> List[SearchResult]:
        """单个源搜索（异步）"""
        try:
            await anti_crawl.random_delay_async(0.3, 1.0)
            # 简单异步适配 - 在线程中运行同步代码
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, source.search, keyword, quality)
            for result in results:
                result.source = source.display_name
                result.resources = [
                    r for r in result.resources
                    if self._quality_score(r.quality) >= self._quality_score(self.min_quality)
                ]
            return [r for r in results if r.resources]
        except Exception:
            return []

    def _quality_score(self, quality: MovieQuality) -> int:
        """画质评分"""
        scores = {
            MovieQuality.REMUX: 100,
            MovieQuality.BLURAY: 90,
            MovieQuality.HDR: 85,
            MovieQuality.UHD_4K: 80,
            MovieQuality.WEB_DL: 75,
            MovieQuality.QHD_2K: 70,
            MovieQuality.FULL_HD_1080P: 60,
            MovieQuality.HD_720P: 40,
            MovieQuality.SD_480P: 20,
            MovieQuality.UNKNOWN: 10,
        }
        return scores.get(quality, 10)

    def get_available_sources(self) -> List[str]:
        """获取可用源列表"""
        available = []
        for name in self.source_names:
            try:
                source = get_source(name)
                available.append(f"{name} ({source.display_name})")
            except ValueError:
                continue
        return available
