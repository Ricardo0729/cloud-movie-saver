"""搜索结果数据模型"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class MovieQuality(Enum):
    """电影画质等级"""
    UNKNOWN = "未知"
    SD_480P = "480p"
    HD_720P = "720p"
    FULL_HD_1080P = "1080p"
    QHD_2K = "2K"
    UHD_4K = "4K"
    BLURAY = "BluRay"
    REMUX = "Remux"
    WEB_DL = "Web-DL"
    HDR = "HDR"


class MovieResourceType(Enum):
    """资源类型"""
    MAGNET = "magnet"         # 磁力链接
    ED2K = "ed2k"             # 电驴链接
    BAIDU_CLOUD = "baidu"     # 百度网盘
    QUARK_CLOUD = "quark"     # 夸克网盘
    XUNLEI_CLOUD = "xunlei"   # 迅雷网盘
    TORRENT = "torrent"       # BT种子文件
    THUNDER = "thunder"       # 迅雷链接
    DIRECT = "direct"         # 直链


@dataclass
class MovieResource:
    """单个电影资源"""
    title: str                       # 资源标题
    url: str                         # 资源链接
    resource_type: MovieResourceType # 资源类型
    quality: MovieQuality = MovieQuality.UNKNOWN  # 画质
    size: str = ""                   # 文件大小
    format_info: str = ""            # 格式信息 (MKV, MP4等)
    source_site: str = ""            # 来源站点
    extra_info: dict = field(default_factory=dict)  # 额外信息


@dataclass
class SearchResult:
    """搜索结果"""
    movie_name: str                  # 电影名称
    year: str = ""                   # 年份
    resources: List[MovieResource] = field(default_factory=list)  # 资源列表
    source: str = ""                 # 来源
    description: str = ""            # 描述
    poster_url: str = ""             # 海报URL
    categories: List[str] = field(default_factory=list)  # 分类
    rating: float = 0.0              # 评分
    score: float = 0.0               # 综合评分（用于排序）
    extra: dict = field(default_factory=dict)


def parse_quality_from_title(title: str) -> MovieQuality:
    """从标题中解析画质"""
    title_lower = title.lower()

    quality_patterns = [
        (MovieQuality.REMUX, ["remux"]),
        (MovieQuality.BLURAY, ["bluray", "blu-ray", "蓝光"]),
        (MovieQuality.HDR, ["hdr", "hdr10", "dolby vision", "杜比"]),
        (MovieQuality.UHD_4K, ["4k", "2160p", "4k ultra hd", "uhd"]),
        (MovieQuality.QHD_2K, ["2k", "1440p"]),
        (MovieQuality.WEB_DL, ["web-dl", "webdl", "webrip", "web rip"]),
        (MovieQuality.FULL_HD_1080P, ["1080p", "1080", "hd 1080"]),
        (MovieQuality.HD_720P, ["720p", "hd 720"]),
        (MovieQuality.SD_480P, ["480p", "720*480", "dvdrip", "dvd"]),
    ]

    for quality, patterns in quality_patterns:
        if any(p in title_lower for p in patterns):
            return quality

    # 检查BD/HD/BDRip关键词
    if any(kw in title_lower for kw in ["bd", "hd", "高清"]):
        return MovieQuality.HD_720P

    return MovieQuality.UNKNOWN


def parse_size(size_str: str) -> int:
    """将大小字符串转为字节数用于排序"""
    if not size_str:
        return 0
    size_str = size_str.strip().upper()
    try:
        if "GB" in size_str:
            return int(float(size_str.replace("GB", "").strip()) * 1024 * 1024 * 1024)
        elif "MB" in size_str:
            return int(float(size_str.replace("MB", "").strip()) * 1024 * 1024)
        elif "KB" in size_str:
            return int(float(size_str.replace("KB", "").strip()) * 1024)
        elif "TB" in size_str:
            return int(float(size_str.replace("TB", "").strip()) * 1024 * 1024 * 1024 * 1024)
        elif "B" in size_str:
            return int(float(size_str.replace("B", "").strip()))
    except (ValueError, AttributeError):
        pass
    return 0


class SearchResultSet:
    """搜索结果集合"""

    def __init__(self):
        self._results: List[SearchResult] = []

    def add(self, result: SearchResult) -> None:
        """添加结果"""
        # 去重：同电影同来源去重
        for existing in self._results:
            if existing.movie_name == result.movie_name and existing.source == result.source:
                existing.resources.extend(result.resources)
                return
        self._results.append(result)

    def extend(self, results: List[SearchResult]) -> None:
        for r in results:
            self.add(r)

    def sort_by_quality(self) -> List[SearchResult]:
        """按画质排序"""
        quality_order = {
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

        for result in self._results:
            if result.resources:
                best_quality = max(
                    (r.quality for r in result.resources),
                    key=lambda q: quality_order.get(q, 0)
                )
                result.score = quality_order.get(best_quality, 0)
                # 有资源加分
                result.score += min(len(result.resources) * 5, 20)

        self._results.sort(key=lambda r: r.score, reverse=True)
        return self._results

    @property
    def all(self) -> List[SearchResult]:
        return self._results

    @property
    def count(self) -> int:
        return len(self._results)

    def __len__(self) -> int:
        return len(self._results)

    def __iter__(self):
        return iter(self._results)
