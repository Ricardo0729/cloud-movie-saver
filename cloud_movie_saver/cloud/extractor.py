"""云盘链接提取器 - 从页面文本中提取各类云盘分享链接"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class CloudLink:
    """云盘链接"""
    provider: str         # baidu, quark, xunlei
    url: str              # 分享链接
    extract_code: str = ""  # 提取码
    source_text: str = ""   # 来源上下文
    is_valid: bool = True


class CloudLinkExtractor:
    """云盘链接提取器"""

    # 百度网盘链接模式
    BAIDU_PATTERNS = [
        r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
        r'https?://yun\.baidu\.com/s/[a-zA-Z0-9_-]+',
    ]

    # 夸克网盘链接模式
    QUARK_PATTERNS = [
        r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+',
        r'https?://quark\.cn/s/[a-zA-Z0-9]+',
        r'https?://pan\.quark\.cn/s/[a-fA-F0-9]+',
    ]

    # 迅雷网盘链接模式
    XUNLEI_PATTERNS = [
        r'https?://pan\.xunlei\.com/s/[a-zA-Z0-9]+',
        r'https?://www\.xunlei\.com/s/[a-zA-Z0-9_-]+',
    ]

    # 提取码模式
    CODE_PATTERNS = [
        r'提取码[:：]?\s*([a-zA-Z0-9]{4})',
        r'提取密码[:：]?\s*([a-zA-Z0-9]{4})',
        r'密码[:：]?\s*([a-zA-Z0-9]{4})',
        r'密码[:：]\s*([a-zA-Z0-9]{4,8})',
        r'提取码[:：]\s*([a-zA-Z0-9]{4,8})',
        r'访问码[:：]?\s*([a-zA-Z0-9]{4})',
        r'([a-zA-Z0-9]{4})[（(]提取码[)）]',
    ]

    @classmethod
    def extract_all(cls, text: str) -> List[CloudLink]:
        """从文本中提取所有云盘链接"""
        links = []

        # 提取百度网盘链接
        for pattern in cls.BAIDU_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                url = match.group()
                code = cls._find_code(text, match.start())
                links.append(CloudLink(
                    provider="baidu",
                    url=url,
                    extract_code=code,
                    source_text=cls._get_context(text, match.start(), match.end()),
                ))

        # 提取夸克网盘链接
        for pattern in cls.QUARK_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                url = match.group()
                code = cls._find_code(text, match.start())
                links.append(CloudLink(
                    provider="quark",
                    url=url,
                    extract_code=code,
                    source_text=cls._get_context(text, match.start(), match.end()),
                ))

        # 提取迅雷网盘链接
        for pattern in cls.XUNLEI_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                url = match.group()
                code = cls._find_code(text, match.start())
                links.append(CloudLink(
                    provider="xunlei",
                    url=url,
                    extract_code=code,
                    source_text=cls._get_context(text, match.start(), match.end()),
                ))

        # 去重
        seen = set()
        unique_links = []
        for link in links:
            key = f"{link.provider}:{link.url}"
            if key not in seen:
                seen.add(key)
                unique_links.append(link)

        return unique_links

    @classmethod
    def extract_baidu(cls, text: str) -> List[CloudLink]:
        """只提取百度网盘链接"""
        return [l for l in cls.extract_all(text) if l.provider == "baidu"]

    @classmethod
    def extract_quark(cls, text: str) -> List[CloudLink]:
        """只提取夸克网盘链接"""
        return [l for l in cls.extract_all(text) if l.provider == "quark"]

    @classmethod
    def extract_xunlei(cls, text: str) -> List[CloudLink]:
        """只提取迅雷网盘链接"""
        return [l for l in cls.extract_all(text) if l.provider == "xunlei"]

    @classmethod
    def _find_code(cls, text: str, link_pos: int) -> str:
        """在链接附近查找提取码"""
        # 先看链接前后各500字符
        start = max(0, link_pos - 500)
        end = min(len(text), link_pos + 500)
        nearby = text[start:end]

        for pattern in cls.CODE_PATTERNS:
            match = re.search(pattern, nearby)
            if match:
                return match.group(1)
        return ""

    @classmethod
    def _get_context(cls, text: str, start: int, end: int, context_chars: int = 100) -> str:
        """获取链接周围上下文"""
        ctx_start = max(0, start - context_chars)
        ctx_end = min(len(text), end + context_chars)
        context = text[ctx_start:ctx_end]
        return context.strip()
