"""电影分类器和整理器"""

import re
import json
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

from ..utils.config import config


# 预定义分类关键词映射
DEFAULT_CATEGORIES = {
    "动作": ["动作", "犯罪", "警匪", "武打", "格斗", "战争", "枪战", "黑帮", "动作片", "Action"],
    "喜剧": ["喜剧", "搞笑", "幽默", "欢乐", "喜剧片", "Comedy"],
    "爱情": ["爱情", "浪漫", "恋爱", "情感", "言情", "爱情片", "Romance"],
    "科幻": ["科幻", "奇幻", "Sci-Fi", "幻想", "魔幻", "异世界", "穿越", "科幻片", "奇幻片"],
    "恐怖": ["恐怖", "惊悚", "Horror", "悬疑", "鬼怪", "灵异", "僵尸", "恐怖片", "惊悚片"],
    "动画": ["动画", "Anime", "动漫", "卡通", "动画电影", "动画片"],
    "剧情": ["剧情", "文艺", "Drama", "传记", "历史", "纪实", "剧情片"],
    "纪录片": ["纪录片", "Documentary", "纪录", "纪实"],
    "悬疑": ["悬疑", "推理", "Mystery", "烧脑", "反转", "悬疑片"],
    "战争": ["战争", "军事", "War"],
}


class MovieCategorizer:
    """电影分类器 - 根据电影名称和描述判断分类"""

    def __init__(self):
        self.categories = config.get("categories", DEFAULT_CATEGORIES)
        self.tmdb_enabled = config.get("tmdb.enabled", False)
        self.tmdb_api_key = config.get("tmdb.api_key", "")
        self._genre_cache: Dict[str, List[str]] = {}
        self._tmdb_session = None

    def categorize(self, movie_name: str, description: str = "") -> List[str]:
        """
        对电影进行分类

        Args:
            movie_name: 电影名称
            description: 电影描述

        Returns:
            分类列表
        """
        # 先尝试TMDB分类（如果启用）
        if self.tmdb_enabled and self.tmdb_api_key:
            tmdb_cats = self._categorize_via_tmdb(movie_name)
            if tmdb_cats:
                return tmdb_cats

        # 使用关键词匹配
        return self._categorize_via_keywords(movie_name, description)

    def _categorize_via_keywords(self, movie_name: str, description: str) -> List[str]:
        """通过关键词匹配分类"""
        text = f"{movie_name} {description}".lower()
        matched_categories = []

        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    matched_categories.append(category)
                    break

        # 如果没有匹配到任何分类，返回"未分类"
        if not matched_categories:
            # 尝试按标题特征推断
            if re.search(r'(20\d{2})', movie_name):
                # 有年份的可能是剧情片
                matched_categories.append("剧情")

        return matched_categories or ["未分类"]

    def _categorize_via_tmdb(self, movie_name: str) -> List[str]:
        """通过TMDB API分类"""
        if movie_name in self._genre_cache:
            return self._genre_cache[movie_name]

        try:
            # 清理名称，提取中文名
            name = self._clean_movie_name(movie_name)
            if not name:
                return []

            import httpx
            # 搜索电影
            search_url = "https://api.themoviedb.org/3/search/movie"
            resp = httpx.get(search_url, params={
                "api_key": self.tmdb_api_key,
                "query": name,
                "language": config.get("tmdb.language", "zh-CN"),
            }, timeout=10)

            if resp.status_code != 200:
                return []

            data = resp.json()
            if not data.get("results"):
                return []

            movie = data["results"][0]
            genre_ids = movie.get("genre_ids", [])

            # TMDB分类ID到中文分类的映射
            tmdb_genre_map = {
                28: "动作", 12: "动作", 80: "动作",    # Action, Adventure, Crime -> 动作
                35: "喜剧",
                18: "剧情",
                14: "科幻",
                27: "恐怖",
                53: "悬疑",
                878: "科幻",
                10770: "剧情",   # TV Movie -> 剧情
                10749: "爱情",
                16: "动画",
                99: "纪录片",
                36: "剧情",      # History -> 剧情
                10752: "战争",
                9648: "悬疑",
                10402: "剧情",   # Music -> 剧情
            }

            cats = []
            for gid in genre_ids:
                if gid in tmdb_genre_map:
                    cat = tmdb_genre_map[gid]
                    if cat not in cats:
                        cats.append(cat)

            self._genre_cache[movie_name] = cats
            return cats if cats else ["未分类"]

        except Exception:
            return []

    def _clean_movie_name(self, raw_name: str) -> str:
        """清理电影名称，去除画质、格式等信息"""
        # 去除常见后缀
        name = raw_name
        patterns = [
            r'\.\d{4}\..*', r'[\(（].*?[\)）]', r'\d{4}.*', r'高清.*', r'BluRay.*',
            r'1080p.*', r'720p.*', r'4K.*', r'2160p.*', r'HDR.*', r'WEB-DL.*',
            r'x264.*', r'x265.*', r'HEVC.*', r'AAC.*', r'DDP5.*', r'Atmos.*',
        ]
        for p in patterns:
            name = re.sub(p, '', name)
        return name.strip().strip('.').strip()

    def get_all_categories(self) -> List[str]:
        """获取所有可用的分类"""
        return list(self.categories.keys())


class MovieManager:
    """电影资源管理器 - 管理资源的本地和云端存储"""

    def __init__(self):
        self.categorizer = MovieCategorizer()
        self.default_save_path = config.get("baidu.save_path", "/已保存电影")

    def organize_result(self, result) -> Dict:
        """
        组织搜索结果，添加分类和整理信息

        Args:
            result: SearchResult对象

        Returns:
            整理后的结果字典
        """
        # 确定分类
        categories = result.categories
        if not categories:
            categories = self.categorizer.categorize(result.movie_name, result.description)

        # 按画质分组资源
        resources_by_quality = {}
        for res in result.resources:
            quality_str = res.quality.value if res.quality else "未知"
            if quality_str not in resources_by_quality:
                resources_by_quality[quality_str] = []
            resources_by_quality[quality_str].append({
                "title": res.title,
                "url": res.url,
                "type": res.resource_type.value if res.resource_type else "unknown",
                "size": res.size,
                "quality": quality_str,
            })

        return {
            "name": result.movie_name,
            "year": result.year,
            "categories": categories,
            "primary_category": categories[0] if categories else "未分类",
            "source": result.source,
            "rating": result.rating,
            "description": result.description[:300] if result.description else "",
            "resources_by_quality": resources_by_quality,
            "all_resources": [
                {
                    "title": r.title,
                    "url": r.url,
                    "type": r.resource_type.value if r.resource_type else "unknown",
                    "quality": r.quality.value if r.quality else "未知",
                    "size": r.size,
                    "source_site": r.source_site,
                    "extract_code": r.extra_info.get("extract_code", ""),
                }
                for r in result.resources
            ],
        }

    def get_suggested_save_path(self, result) -> str:
        """获取建议的云盘保存路径"""
        categories = result.categories or self.categorizer.categorize(result.movie_name, result.description)
        primary_cat = categories[0] if categories else "未分类"
        movie_name_clean = re.sub(r'[<>:"/\\|?*]', '', result.movie_name)[:50]
        return f"{self.default_save_path}/{primary_cat}/{movie_name_clean}"

    def generate_summary(self, results: List[Dict]) -> str:
        """生成资源汇总报告"""
        summary = []
        summary.append("=" * 60)
        summary.append("📋 电影资源搜索汇总报告")
        summary.append("=" * 60)

        for i, item in enumerate(results, 1):
            summary.append(f"\n{i}. 🎬 {item['name']} ({item.get('year', '未知年份')})")
            summary.append(f"   来源: {item.get('source', '未知')}")
            summary.append(f"   分类: {' / '.join(item.get('categories', ['未分类']))}")
            summary.append(f"   评分: {item.get('rating', 'N/A')}")

            resources = item.get('all_resources', [])
            if resources:
                summary.append(f"   资源数量: {len(resources)} 个")
                # 统计各类型
                from collections import Counter
                type_counts = Counter(r['type'] for r in resources)
                summary.append(f"   类型分布: {', '.join(f'{k}={v}' for k, v in type_counts.items())}")

                # 最佳资源
                best = resources[0]
                summary.append(f"   最佳资源: [{best['quality']}] {best['url'][:60]}...")

        summary.append("\n" + "=" * 60)
        summary.append(f"共搜索到 {len(results)} 部电影资源")
        summary.append("=" * 60)

        return "\n".join(summary)
