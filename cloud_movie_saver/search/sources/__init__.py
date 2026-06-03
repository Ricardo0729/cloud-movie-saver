"""搜索源注册模块"""

from typing import Dict, List, Type
from ..base import BaseSource


# 源注册表
_source_registry: Dict[str, Type[BaseSource]] = {}


def register_source(name: str):
    """注册搜索源装饰器"""
    def decorator(cls):
        cls.name = name
        _source_registry[name] = cls
        return cls
    return decorator


def get_source(name: str) -> BaseSource:
    """获取搜索源实例"""
    if name not in _source_registry:
        raise ValueError(f"未知的搜索源: {name}，可用: {list(_source_registry.keys())}")
    return _source_registry[name]()


def get_all_sources() -> Dict[str, Type[BaseSource]]:
    """获取所有注册的搜索源"""
    return _source_registry.copy()


def get_source_names() -> List[str]:
    return list(_source_registry.keys())


# 导入所有源以触发注册
from . import dytt, bttiantang, movie_sites, magnet_search, web_search
