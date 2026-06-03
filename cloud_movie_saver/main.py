#!/usr/bin/env python3
"""
CloudMovieSaver - 云盘电影资源搜索保存工具
============================================
搜索电影资源，自动保存到云盘，按类别整理。

使用方式:
  python -m cloud_movie_saver.main search [关键词]
  python -m cloud_movie_saver.main config [key] [value]
  python -m cloud_movie_saver.main sources
  python -m cloud_movie_saver.main login [baidu|quark|xunlei]
"""

import sys
import os
import json
import webbrowser
from typing import List, Optional, Dict
from datetime import datetime

import click

from . import __version__
from .utils.config import config
from .utils.anti_crawl import anti_crawl
from .search import SearchResult, SearchResultSet, MovieQuality, MovieResourceType
from .search.engine import SearchEngine
from .search.sources import get_source_names
from .cloud.baidu import BaiduCloud
from .cloud.quark import QuarkCloud
from .cloud.xunlei import XunleiCloud
from .cloud.extractor import CloudLinkExtractor
from .organizer import MovieCategorizer, MovieManager

# 尝试导入rich（美化输出用）
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.markdown import Markdown
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich import box
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ============================================================
# CLI 入口
# ============================================================

class RichConsole:
    """Rich 控制台封装，带降级支持"""

    def __init__(self):
        self._rich = RICH_AVAILABLE
        if self._rich:
            self.console = Console()
        self._progress = None

    def print(self, *args, **kwargs):
        if self._rich:
            self.console.print(*args, **kwargs)
        else:
            print(*args)

    def info(self, msg: str):
        self.print(f"[bold cyan]ℹ[/] {msg}") if self._rich else print(f"ℹ {msg}")

    def success(self, msg: str):
        self.print(f"[bold green]✓[/] {msg}") if self._rich else print(f"✓ {msg}")

    def warning(self, msg: str):
        self.print(f"[bold yellow]⚠[/] {msg}") if self._rich else print(f"⚠ {msg}")

    def error(self, msg: str):
        self.print(f"[bold red]✗[/] {msg}") if self._rich else print(f"✗ {msg}")

    def header(self, text: str):
        if self._rich:
            self.print(Panel(f"[bold cyan]{text}[/]", box=box.HEAVY))
        else:
            print(f"\n{'=' * 60}\n{text}\n{'=' * 60}")

    def section(self, text: str):
        if self._rich:
            self.print(f"\n[bold yellow]▶ {text}[/]")
        else:
            print(f"\n▶ {text}")

    def divider(self):
        self.print("[dim]─" * 50 + "[/]") if self._rich else print("─" * 50)

    def show_progress(self, description: str = "处理中..."):
        if self._rich:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            )
            self._progress.start()
            self._progress_task = self._progress.add_task(description)
        else:
            print(f"  {description}...", end="", flush=True)

    def stop_progress(self, success: bool = True):
        if self._rich and self._progress:
            self._progress.stop()
            self._progress = None
        else:
            if success:
                print(" ✓")
            else:
                print(" ✗")

    def progress_iter(self, items, description: str = "处理中"):
        """带进度的迭代器"""
        if self._rich:
            from rich.progress import track
            yield from track(items, description=description)
        else:
            total = len(items) if hasattr(items, "__len__") else 0
            for i, item in enumerate(items):
                if total > 0:
                    print(f"\r  {description}: {i+1}/{total}", end="", flush=True)
                yield item
            if total > 0:
                print()


console = RichConsole()


# ============================================================
# Click CLI 定义
# ============================================================

@click.group(invoke_without_command=True)
@click.version_option(__version__, "-v", "--version", message="CloudMovieSaver v%(version)s")
@click.option("--cfg", "-c", help="指定配置文件路径")
@click.pass_context
def cli(ctx, cfg):
    """🎬 CloudMovieSaver - 云盘电影资源搜索保存工具"""
    if cfg:
        config.reload(cfg)
    if ctx.invoked_subcommand is None:
        # 显示欢迎信息
        if RICH_AVAILABLE:
            from rich.panel import Panel
            from rich.box import HEAVY
            console.print(Panel.fit(
                "[bold cyan]🎬 CloudMovieSaver[/] [dim]v" + __version__ + "[/]\n"
                "[green]云盘电影资源搜索保存工具[/]\n"
                "[dim]搜索电影 → 自动保存到云盘 → 按类别整理[/]",
                box=HEAVY,
            ))
        else:
            console.print("CloudMovieSaver v" + __version__)
            console.print("云盘电影资源搜索保存工具")
        console.print()
        click.echo(ctx.get_help())


@cli.command()
@click.argument("keyword")
@click.option("--quality", "-q", default=None,
              help="筛选画质: 720p, 1080p, 4k, bluray")
@click.option("--sources", "-s", default=None,
              help="指定搜索源，逗号分隔 (默认使用全部)")
@click.option("--save", "-S", is_flag=True,
              help="搜索后自动保存到云盘")
@click.option("--cloud", "-C", default=None,
              help="指定云盘: baidu, quark, xunlei (默认自动)")
@click.option("--output", "-o", default=None,
              help="输出结果到文件 (JSON格式)")
@click.option("--limit", "-l", default=30, type=int,
              help="最大结果数")
@click.option("--no-browser", is_flag=True,
              help="不自动打开浏览器")
@click.option("--interactive", "-i", is_flag=True,
              help="交互模式 - 选择要保存的资源")
def search(keyword: str, quality: Optional[str], sources: Optional[str],
           save: bool, cloud: Optional[str], output: Optional[str],
           limit: int, no_browser: bool, interactive: bool):
    """🔍 搜索电影资源"""
    console.header(f"🎬 搜索电影: {keyword}")

    # 解析源列表
    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",")]

    # 创建搜索引擎
    engine = SearchEngine()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=Console() if RICH_AVAILABLE else None,
        transient=True,
    ) as progress:
        task = progress.add_task(f"[cyan]正在从多个来源搜索「{keyword}」...", total=None)
        result_set = engine.search(keyword, quality, source_list)
        progress.update(task, completed=True)

    if result_set.count == 0:
        console.warning(f"未找到「{keyword}」的相关资源")
        console.info("建议:")
        console.info("  1. 检查网络连接和代理设置")
        console.info("  2. 尝试不同的关键词")
        console.info("  3. 使用 --sources 指定更多搜索源")
        return

    console.success(f"找到 {result_set.count} 部相关电影资源!\n")

    # 整理结果
    manager = MovieManager()
    organized_results = []

    sorted_results = result_set.sort_by_quality()[:limit]

    for idx, result in enumerate(sorted_results, 1):
        organized = manager.organize_result(result)
        organized_results.append(organized)

        # 显示结果
        display_result(idx, organized)

    # 汇总统计
    show_summary(organized_results)

    # 输出到文件
    if output:
        save_results_to_file(organized_results, output)

    # 交互模式 - 选择要保存的资源
    if interactive:
        interactive_save(organized_results, cloud)

    # 自动保存
    elif save:
        auto_save_results(organized_results, cloud)

    # 询问是否打开浏览器查看
    if not no_browser and config.get("output.auto_open_browser", True):
        open_links_in_browser(organized_results)


@cli.command()
def sources():
    """📡 显示所有可用的搜索源"""
    console.header("📡 可用搜索源")

    from .search.sources import get_all_sources, get_source_names

    names = get_source_names()
    if RICH_AVAILABLE:
        table = Table(title="搜索源列表", box=box.ROUNDED)
        table.add_column("#", style="dim")
        table.add_column("源名称", style="cyan")
        table.add_column("显示名", style="green")
        table.add_column("状态")

        for i, name in enumerate(names, 1):
            try:
                from .search.sources import get_source
                source = get_source(name)
                accessible = source.is_accessible()
                status = "✅ 可用" if accessible else "⚠️ 可能不可用"
                table.add_row(str(i), name, source.display_name, status)
            except Exception:
                table.add_row(str(i), name, "?", "❓ 加载失败")

        console.print(table)
    else:
        for i, name in enumerate(names, 1):
            try:
                from .search.sources import get_source
                source = get_source(name)
                console.print(f"  {i}. {name} - {source.display_name}")
            except Exception:
                console.print(f"  {i}. {name} - ?")

    console.info(f"\n共 {len(names)} 个搜索源")

    # 显示当前优先级配置
    priority = config.get("search.source_priority", names)
    console.section("当前搜索优先级")
    for i, name in enumerate(priority, 1):
        console.print(f"  {i}. {name}")


@cli.command()
@click.argument("action", type=click.Choice(["baidu", "quark", "xunlei"]))
def login(action: str):
    """🔑 验证云盘登录状态"""
    console.header(f"🔑 验证 {action} 网盘登录")

    providers = {
        "baidu": (BaiduCloud, "BDUSS"),
        "quark": (QuarkCloud, "Cookie"),
        "xunlei": (XunleiCloud, "Cookie"),
    }

    provider_cls, cred_name = providers[action]
    provider = provider_cls()

    if not provider.is_configured:
        console.warning(f"未配置{action}网盘的{cred_name}")
        if action == "baidu":
            console.info("配置方式:")
            console.info("  1. 打开浏览器登录 https://pan.baidu.com")
            console.info("  2. 按F12打开开发者工具 -> Application -> Cookies")
            console.info("  3. 找到 BDUSS 和 STOKEN 的值")
            console.info(f"  4. 在 config.yaml 中设置或运行:")
            console.info(f"     python main.py config baidu.bduss <你的BDUSS>")
            console.info(f"     python main.py config baidu.stoken <你的STOKEN>")
        else:
            console.info(f"配置方式:")
            console.info(f"  1. 登录 {action} 网盘网页版")
            console.info(f"  2. 按F12获取Cookie")
            console.info(f"  3. 在 config.yaml 中设置 cookie 字段")
        return

    console.show_progress("验证中...")
    ok = provider.login()
    console.stop_progress(ok)

    if ok:
        console.success(f"{action}网盘 登录成功 ✅")
    else:
        console.error(f"{action}网盘 登录失败 ❌")
        console.info("请检查Cookie是否过期，或重新获取后重试")


@cli.command()
@click.argument("key")
@click.argument("value", required=False)
def config_cmd(key: str, value: Optional[str]):
    """⚙️ 查看或设置配置"""
    if value:
        config.set(key, value)
        config.save()
        console.success(f"已设置 {key} = {value}")
    else:
        current = config.get(key)
        console.print(f"[bold]{key}[/] = {current}")
        console.info(f"类型: {type(current).__name__}")


@cli.command()
@click.argument("url")
@click.option("--provider", "-p", default=None,
              help="指定网盘: baidu, quark, xunlei")
@click.option("--code", "-c", default="", help="提取码")
@click.option("--dir", "-d", default="", help="保存目录")
def save(url: str, provider: Optional[str], code: str, dir: str):
    """💾 直接保存云盘分享链接"""
    console.header("💾 保存分享链接")
    console.print(f"链接: {url}")
    if code:
        console.print(f"提取码: {code}")

    # 自动检测网盘类型
    if not provider:
        if "pan.baidu.com" in url:
            provider = "baidu"
        elif "quark.cn" in url:
            provider = "quark"
        elif "xunlei.com" in url:
            provider = "xunlei"
        else:
            console.error("无法检测网盘类型，请用 --provider 指定")
            return

    providers = {
        "baidu": BaiduCloud,
        "quark": QuarkCloud,
        "xunlei": XunleiCloud,
    }

    cloud = providers[provider]()
    if not cloud.login():
        console.error(f"{provider}网盘 登录失败")
        return

    console.show_progress(f"正在保存到{provider}网盘...")
    success, msg = cloud.save_share_link(url, code, dir)
    console.stop_progress(success)

    if success:
        console.success(msg)
    else:
        console.error(f"保存失败: {msg}")


@cli.command()
@click.argument("keyword", nargs=-1, required=True)
@click.option("--min-size", default="1GB", help="最小文件大小")
@click.option("--max-results", default=10, type=int)
def magnet(keyword: List[str], min_size: str, max_results: int):
    """🧲 磁力链接搜索（快速模式）"""
    query = " ".join(keyword)
    console.header(f"🧲 磁力搜索: {query}")

    # 只使用磁力搜索源
    engine = SearchEngine()
    result_set = engine.search(query)

    if result_set.count == 0:
        console.warning("未找到磁力链接")
        return

    # 显示结果
    sorted_results = result_set.sort_by_quality()[:max_results]
    all_magnets = []

    if RICH_AVAILABLE:
        table = Table(title=f"磁力链接搜索结果 - {query}", box=box.ROUNDED)
        table.add_column("#", style="dim")
        table.add_column("标题", style="cyan", no_wrap=False)
        table.add_column("画质", style="green")
        table.add_column("来源")
        table.add_column("磁力链接", style="dim", max_width=50)

        for idx, result in enumerate(sorted_results, 1):
            for res in result.resources[:3]:  # 最多显示3个磁力链接
                if res.resource_type == MovieResourceType.MAGNET:
                    magnet_url = res.url[:50] + "..." if len(res.url) > 50 else res.url
                    table.add_row(
                        str(idx),
                        result.movie_name[:40],
                        res.quality.value,
                        result.source,
                        magnet_url,
                    )
                    all_magnets.append(res.url)
                    break

        console.print(table)
    else:
        for idx, result in enumerate(sorted_results, 1):
            for res in result.resources:
                if res.resource_type == MovieResourceType.MAGNET:
                    console.print(f"\n{idx}. {result.movie_name}")
                    console.print(f"   画质: {res.quality.value}")
                    console.print(f"   来源: {result.source}")
                    console.print(f"   链接: {res.url}")
                    all_magnets.append(res.url)
                    break

    if all_magnets:
        console.info(f"\n共 {len(all_magnets)} 个磁力链接")
        # 复制第一个到剪贴板
        try:
            import pyperclip
            pyperclip.copy(all_magnets[0])
            console.success("第一个磁力链接已复制到剪贴板!")
        except ImportError:
            pass


@cli.command()
def setup():
    """🔧 初始化设置向导"""
    console.header("🔧 CloudMovieSaver 设置向导")

    console.section("百度网盘配置")
    if not config.get("baidu.bduss"):
        console.info("BDUSS 是百度网盘的登录凭证，获取方式：")
        console.info("1. 在浏览器打开 https://pan.baidu.com 并登录")
        console.info("2. 按 F12 打开开发者工具")
        console.info("3. 点击 Application/存储 -> Cookies")
        console.info("4. 找到 BDUSS 和 STOKEN")
        if RICH_AVAILABLE:
            bduss = Prompt.ask("请输入 BDUSS", default="")
            stoken = Prompt.ask("请输入 STOKEN", default="")
        else:
            bduss = input("  请输入 BDUSS: ").strip()
            stoken = input("  请输入 STOKEN: ").strip()

        if bduss:
            config.set("baidu.bduss", bduss)
            config.set("baidu.stoken", stoken)
            config.set("baidu.enabled", True)
            console.success("百度网盘配置已保存!")
    else:
        console.success("百度网盘已配置")

    console.section("TMDB API 配置（用于电影分类）")
    if RICH_AVAILABLE:
        tmdb_key = Prompt.ask("请输入TMDB API Key (可选，留空跳过)", default="")
    else:
        tmdb_key = input("  请输入TMDB API Key (可选，留空跳过): ").strip()

    if tmdb_key:
        config.set("tmdb.api_key", tmdb_key)
        config.set("tmdb.enabled", True)
        config.set("tmdb.language", "zh-CN")
        console.success("TMDB API 已配置!")

    # 保存配置
    config.save()
    console.success("配置已保存到 config.yaml!")
    console.info("你也可以直接编辑 config.yaml 文件来修改配置")


@cli.command()
@click.argument("url")
@click.option("--format", "-f", default="markdown", help="输出格式")
def analyze(url: str, format: str):
    """🔬 分析页面中的云盘链接"""
    console.header(f"🔬 分析页面: {url}")

    import httpx
    try:
        headers = anti_crawl.get_headers(referer=url)
        resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        resp.encoding = "utf-8"

        # 提取云盘链接
        links = CloudLinkExtractor.extract_all(resp.text)
        if not links:
            console.warning("未找到云盘链接")
            return

        console.success(f"找到 {len(links)} 个云盘链接:")

        if RICH_AVAILABLE:
            table = Table(box=box.ROUNDED)
            table.add_column("类型", style="cyan")
            table.add_column("链接", no_wrap=False)
            table.add_column("提取码")
            for link in links:
                code_display = link.extract_code or "-"
                table.add_row(
                    {"baidu": "百度网盘", "quark": "夸克网盘", "xunlei": "迅雷网盘"}.get(link.provider, link.provider),
                    link.url,
                    code_display,
                )
            console.print(table)
        else:
            for link in links:
                code_display = f" 提取码: {link.extract_code}" if link.extract_code else ""
                console.print(f"  [{link.provider}] {link.url}{code_display}")

    except Exception as e:
        console.error(f"分析失败: {e}")


# ============================================================
# 辅助函数
# ============================================================

def display_result(idx: int, organized: Dict):
    """显示单个搜索结果"""
    name = organized["name"]
    year = organized.get("year", "")
    categories = organized.get("categories", ["未分类"])
    source = organized.get("source", "未知")
    resources = organized.get("all_resources", [])
    resources_by_quality = organized.get("resources_by_quality", {})

    year_str = f" ({year})" if year else ""
    cat_str = f"[{'/'.join(categories)}]"

    if RICH_AVAILABLE:
        # Rich 美化输出
        title_text = Text()
        title_text.append(f"{idx}. ", style="bold dim")
        title_text.append(f"{name}", style="bold white")
        title_text.append(f"{year_str}", style="yellow")
        title_text.append(f"  {cat_str}", style="green")

        console.print(title_text)

        # 信息行
        info_text = Text()
        info_text.append(f"    来源: ", style="dim")
        info_text.append(f"{source}", style="cyan")
        if organized.get("rating"):
            info_text.append(f" | 评分: ", style="dim")
            info_text.append(f"{organized['rating']}", style="yellow")
        console.print(info_text)

        # 资源列表
        if resources_by_quality:
            quality_str = " | ".join(
                f"[{q}]({len(items)})" for q, items in resources_by_quality.items()
            )
            console.print(f"    画质: {quality_str}")

        # 显示最佳资源
        if resources:
            best = resources[0]
            url_display = best["url"][:70] + "..." if len(best["url"]) > 70 else best["url"]
            type_icons = {
                "magnet": "🧲", "ed2k": "🔗", "baidu": "☁️", "quark": "☁️",
                "xunlei": "⚡", "torrent": "📦", "direct": "🔗",
            }
            icon = type_icons.get(best["type"], "🔗")
            code_str = f" (提取码: {best.get('extract_code', '')})" if best.get("extract_code") else ""
            console.print(f"    {icon} [{best['quality']}] {url_display}{code_str}")

    else:
        # 无 Rich 降级输出
        console.print(f"\n{idx}. {name}{year_str} [{cat_str}]")
        console.print(f"    来源: {source}")
        if resources:
            for res in resources[:3]:
                console.print(f"    [{res['quality']}] {res['type']}: {res['url'][:80]}")

    console.divider()


def show_summary(results: List[Dict]):
    """显示汇总信息"""
    if not results:
        return

    # 统计分类
    from collections import Counter
    cat_counter = Counter()
    quality_counter = Counter()
    source_counter = Counter()
    total_resources = 0

    for r in results:
        for cat in r.get("categories", []):
            cat_counter[cat] += 1
        source_counter[r.get("source", "未知")] += 1

        for quality, items in r.get("resources_by_quality", {}).items():
            quality_counter[quality] += len(items)
            total_resources += len(items)

    console.section("📊 搜索统计")
    if RICH_AVAILABLE:
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("项目", style="dim")
        table.add_column("数值")

        table.add_row("电影数", str(len(results)))
        table.add_row("资源总数", str(total_resources))
        table.add_row("分类分布", ", ".join(f"{k}({v})" for k, v in cat_counter.most_common(5)))
        table.add_row("画质分布", ", ".join(f"{k}({v})" for k, v in quality_counter.most_common(5)))
        table.add_row("来源分布", ", ".join(f"{k}({v})" for k, v in source_counter.most_common(5)))

        console.print(table)
    else:
        console.print(f"  电影数: {len(results)}")
        console.print(f"  资源总数: {total_resources}")
        console.print(f"  分类: {dict(cat_counter.most_common(5))}")


def save_results_to_file(results: List[Dict], output_path: str):
    """保存结果到文件"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        console.success(f"结果已保存到: {output_path}")
    except Exception as e:
        console.error(f"保存文件失败: {e}")


def interactive_save(results: List[Dict], cloud_type: Optional[str] = None):
    """交互式选择要保存的资源"""
    console.section("💾 选择要保存的资源")

    if not RICH_AVAILABLE:
        console.warning("交互模式需要 rich 库")
        return

    selected = []
    for i, r in enumerate(results, 1):
        if Confirm.ask(f"  是否保存「{r['name']}」?", default=False):
            selected.append(r)

    if not selected:
        console.info("未选择任何资源")
        return

    auto_save_results(selected, cloud_type)


def auto_save_results(results: List[Dict], cloud_type: Optional[str] = None):
    """自动保存结果到云盘"""
    if not results:
        return

    # 确定要使用的云盘
    if cloud_type:
        cloud_providers = [cloud_type]
    else:
        # 按优先级检测可用的云盘
        cloud_providers = []
        for name, cls in [("baidu", BaiduCloud), ("quark", QuarkCloud), ("xunlei", XunleiCloud)]:
            instance = cls()
            if instance.is_configured:
                cloud_providers.append(name)

        if not cloud_providers:
            console.warning("未配置任何云盘")
            console.info("请先运行 setup 命令配置云盘，或使用 --cloud 指定")
            return

    for provider_name in cloud_providers:
        cls_map = {"baidu": BaiduCloud, "quark": QuarkCloud, "xunlei": XunleiCloud}
        provider = cls_map[provider_name]()

        console.section(f"💾 保存到 {provider_name} 网盘")

        if not provider.login():
            continue

        save_count = 0
        for r in results:
            movie_name = r["name"]
            category = r.get("primary_category", "未分类")

            # 查找云盘链接
            cloud_links = [
                res for res in r.get("all_resources", [])
                if res["type"] == provider_name or
                   (provider_name == "baidu" and "pan.baidu.com" in res["url"])
            ]

            for link in cloud_links:
                save_dir = f"/已保存电影/{category}/{movie_name}"
                code = link.get("extract_code", "")

                console.show_progress(f"正在保存 {movie_name}...")
                success, msg = provider.save_share_link(link["url"], code, save_dir)
                console.stop_progress(success)

                if success:
                    console.success(f"✓ {movie_name} -> {save_dir}")
                    save_count += 1
                else:
                    console.warning(f"  {msg}")

        console.success(f"共保存 {save_count}/{len(results)} 部电影到 {provider_name}")


def open_links_in_browser(results: List[Dict]):
    """在浏览器中打开资源链接"""
    if not RICH_AVAILABLE:
        return

    if not Confirm.ask("是否打开浏览器查看资源?", default=False):
        return

    for r in results[:5]:  # 最多打开5个
        for res in r.get("all_resources", [])[:2]:  # 每个电影打开2个链接
            if res["type"] in ("magnet", "baidu", "quark"):
                try:
                    webbrowser.open(res["url"])
                except Exception:
                    pass


# ============================================================
# 程序入口
# ============================================================

def main():
    """程序入口"""
    cli()


if __name__ == "__main__":
    main()
