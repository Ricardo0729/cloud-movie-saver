#!/usr/bin/env python3
"""CloudMovieSaver 基础测试"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    from cloud_movie_saver.utils.config import Config, config
    from cloud_movie_saver.utils.anti_crawl import AntiCrawlManager, anti_crawl
    from cloud_movie_saver.search import SearchResult, MovieResource, SearchResultSet
    from cloud_movie_saver.search.sources import get_source_names, get_source
    from cloud_movie_saver.cloud.extractor import CloudLinkExtractor
    from cloud_movie_saver.organizer import MovieCategorizer, MovieManager
    from cloud_movie_saver.search.engine import SearchEngine
    print(f"  ✓ 所有模块导入成功")
    print(f"  ✓ 搜索源: {len(get_source_names())} 个")
    return True


def test_config():
    """测试配置加载"""
    print("测试配置加载...")
    from cloud_movie_saver.utils.config import config
    assert config.get("search.timeout") == 30
    assert config.get("search.source_priority") is not None
    assert len(config.get("search.source_priority")) > 0
    print(f"  ✓ 配置加载成功")
    print(f"  ✓ 搜索优先级: {config.get('search.source_priority')[:5]}...")
    return True


def test_search_result():
    """测试搜索结果数据结构"""
    print("测试搜索结果数据结构...")
    from cloud_movie_saver.search import SearchResult, MovieResource, MovieResourceType, MovieQuality, SearchResultSet, parse_quality_from_title

    # 测试画质解析
    assert parse_quality_from_title("电影 1080p.mkv") == MovieQuality.FULL_HD_1080P
    assert parse_quality_from_title("电影 4K X265") == MovieQuality.UHD_4K, f"Expected UHD_4K but got {parse_quality_from_title('电影 4K X265')}"
    assert parse_quality_from_title("电影 4K.HDR") == MovieQuality.HDR   # HDR matched before 4K
    assert parse_quality_from_title("电影 BluRay") == MovieQuality.BLURAY
    print("  ✓ 画质解析正确")

    # 测试资源创建
    res = MovieResource(
        title="测试资源",
        url="magnet:?xt=urn:btih:test",
        resource_type=MovieResourceType.MAGNET,
        quality=MovieQuality.FULL_HD_1080P,
    )
    assert res.title == "测试资源"
    assert res.resource_type == MovieResourceType.MAGNET

    result = SearchResult(
        movie_name="测试电影",
        resources=[res],
        source="测试源",
    )
    assert result.movie_name == "测试电影"
    assert len(result.resources) == 1

    # 测试结果集
    rs = SearchResultSet()
    rs.add(result)
    assert rs.count == 1
    print("  ✓ 搜索结果数据结构正确")
    return True


def test_anti_crawl():
    """测试反爬模块"""
    print("测试反爬模块...")
    from cloud_movie_saver.utils.anti_crawl import anti_crawl

    # 测试UA生成
    ua = anti_crawl.get_random_ua()
    assert ua is not None
    assert len(ua) > 20
    print(f"  ✓ User-Agent生成正常: {ua[:40]}...")

    # 测试请求头
    headers = anti_crawl.get_headers(referer="https://example.com")
    assert "User-Agent" in headers
    assert "Referer" in headers
    assert "Accept-Language" in headers
    print(f"  ✓ 请求头生成正常 ({len(headers)} 个字段)")
    return True


def test_cloud_extractor():
    """测试云盘链接提取"""
    print("测试云盘链接提取...")
    from cloud_movie_saver.cloud.extractor import CloudLinkExtractor

    test_html = """
    百度网盘链接: https://pan.baidu.com/s/abc123def 提取码: abcd
    夸克网盘链接: https://pan.quark.cn/s/xyz789
    磁力链接: magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=test
    """

    links = CloudLinkExtractor.extract_all(test_html)
    assert len(links) >= 2
    providers = [l.provider for l in links]
    assert "baidu" in providers
    assert "quark" in providers

    # 测试提取码
    baidu_links = [l for l in links if l.provider == "baidu"]
    if baidu_links:
        assert baidu_links[0].extract_code == "abcd"
        print(f"  ✓ 提取码提取正确: {baidu_links[0].extract_code}")

    print(f"  ✓ 云盘链接提取正常 (共 {len(links)} 个链接)")
    return True


def test_organizer():
    """测试分类器"""
    print("测试电影分类器...")
    from cloud_movie_saver.organizer import MovieCategorizer

    categorizer = MovieCategorizer()

    # 测试分类
    cats = categorizer.categorize("流浪地球 2019")
    assert len(cats) > 0
    print(f"  ✓ 分类结果: {cats}")

    cats2 = categorizer.categorize("整蛊专家 周星驰")
    print(f"  ✓ 分类结果2: {cats2}")

    print("  ✓ 分类器工作正常")
    return True


def test_search_engine():
    """测试搜索引擎初始化"""
    print("测试搜索引擎...")
    from cloud_movie_saver.search.engine import SearchEngine

    engine = SearchEngine()
    assert engine is not None
    sources = engine.get_available_sources()
    print(f"  ✓ 搜索引擎初始化成功 ({len(sources)} 个可用源)")
    return True


def main():
    """运行所有测试"""
    print("=" * 50)
    print("  CloudMovieSaver 功能测试")
    print("=" * 50)

    tests = [
        ("模块导入", test_imports),
        ("配置加载", test_config),
        ("搜索数据结构", test_search_result),
        ("反爬模块", test_anti_crawl),
        ("云盘链接提取", test_cloud_extractor),
        ("电影分类器", test_organizer),
        ("搜索引擎", test_search_engine),
    ]

    passed = 0
    failed = 0

    for name, func in tests:
        print(f"\n[{name}]")
        try:
            result = func()
            if result:
                print(f"  ✅ {name} 通过")
                passed += 1
            else:
                print(f"  ❌ {name} 失败")
                failed += 1
        except Exception as e:
            print(f"  ❌ {name} 异常: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"  测试完成: {passed}/{passed + failed} 通过")
    if failed == 0:
        print("  🎉 全部测试通过!")
    print("=" * 50)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
