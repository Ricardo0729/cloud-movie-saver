#!/usr/bin/env python3
"""CloudMovieSaver GUI - 云盘电影搜索保存图形界面"""

import os
import sys
import threading
import webbrowser
from typing import List, Dict
from pathlib import Path

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter.font import Font


class CloudMovieSaverGUI:
    """CloudMovieSaver 图形界面"""

    # 颜色方案
    COLORS = {
        'bg': '#1a1a2e',
        'bg2': '#16213e',
        'accent': '#0f3460',
        'highlight': '#e94560',
        'text': '#ffffff',
        'text2': '#a0a0b0',
        'success': '#4caf50',
        'warning': '#ff9800',
        'card': '#1e2746',
        'card_hover': '#253255',
        'input_bg': '#0d1b2a',
        'border': '#2a3a5c',
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CloudMovieSaver - 云盘电影搜索")
        self.root.geometry("960x720")
        self.root.minsize(800, 600)
        self.root.configure(bg=self.COLORS['bg'])

        # 设置图标
        try:
            self.root.iconbitmap(default='')
        except:
            pass

        # 搜索结果存储
        self.search_results: List[Dict] = []
        self.search_engine = None
        self.baidu_cloud = None

        # 构建UI
        self._build_ui()

        # 居中显示
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _build_ui(self):
        """构建界面"""
        # 自定义样式
        style = ttk.Style()
        style.theme_use('clam')

        # 配置ttk样式
        style.configure('Title.TLabel', foreground=self.COLORS['highlight'],
                        font=('Microsoft YaHei UI', 16, 'bold'), background=self.COLORS['bg'])
        style.configure('Subtitle.TLabel', foreground=self.COLORS['text2'],
                        font=('Microsoft YaHei UI', 9), background=self.COLORS['bg'])
        style.configure('Search.TButton', foreground='#ffffff', background=self.COLORS['highlight'],
                        font=('Microsoft YaHei UI', 10), borderwidth=0, padding=(15, 8))
        style.map('Search.TButton',
                  background=[('active', '#d63850'), ('pressed', '#c03048')])
        style.configure('Cloud.TButton', foreground='#ffffff', background=self.COLORS['accent'],
                        font=('Microsoft YaHei UI', 9), padding=(10, 5))
        style.map('Cloud.TButton',
                  background=[('active', '#154580'), ('pressed', '#103a70')])
        style.configure('Status.TLabel', foreground=self.COLORS['text2'],
                        font=('Microsoft YaHei UI', 9), background=self.COLORS['bg'])
        style.configure('Result.TFrame', background=self.COLORS['card'])
        style.configure('Header.TLabelframe', background=self.COLORS['bg2'], foreground=self.COLORS['text'])
        style.configure('Header.TLabelframe.Label', foreground=self.COLORS['text'],
                        font=('Microsoft YaHei UI', 11))

        # 主容器
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # ========== 顶部标题 ==========
        title_frame = tk.Frame(main_frame, bg=self.COLORS['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = tk.Label(title_frame, text="🎬 CloudMovieSaver",
                               font=('Microsoft YaHei UI', 20, 'bold'),
                               fg=self.COLORS['highlight'], bg=self.COLORS['bg'])
        title_label.pack(anchor=tk.W)

        subtitle_label = tk.Label(title_frame, text="搜索电影 → 自动保存到云盘 → 按类别整理",
                                  font=('Microsoft YaHei UI', 9),
                                  fg=self.COLORS['text2'], bg=self.COLORS['bg'])
        subtitle_label.pack(anchor=tk.W)

        # ========== 搜索栏 ==========
        search_frame = tk.Frame(main_frame, bg=self.COLORS['bg2'],
                               highlightbackground=self.COLORS['border'],
                               highlightthickness=1, padx=5, pady=5)
        search_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(search_frame, text="🔍", font=('Segoe UI', 16),
                bg=self.COLORS['bg2'], fg=self.COLORS['text2']).pack(side=tk.LEFT, padx=(10, 5))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                     font=('Microsoft YaHei UI', 13),
                                     bg=self.COLORS['input_bg'], fg=self.COLORS['text'],
                                     insertbackground=self.COLORS['text'],
                                     relief=tk.FLAT, bd=0, highlightthickness=0)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=5)
        self.search_entry.insert(0, "输入电影名称，例如：流浪地球")
        self.search_entry.bind('<FocusIn>', self._on_entry_focus)
        self.search_entry.bind('<FocusOut>', self._on_entry_blur)
        self.search_entry.bind('<Return>', lambda e: self.do_search())

        self.search_btn = tk.Button(search_frame, text="搜索",
                                    command=self.do_search,
                                    bg=self.COLORS['highlight'], fg='#ffffff',
                                    font=('Microsoft YaHei UI', 10, 'bold'),
                                    relief=tk.FLAT, padx=20, pady=6,
                                    cursor='hand2', activebackground='#d63850',
                                    activeforeground='#ffffff')
        self.search_btn.pack(side=tk.RIGHT, padx=(5, 10))

        # ========== 状态栏 ==========
        status_frame = tk.Frame(main_frame, bg=self.COLORS['bg'])
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_label = tk.Label(status_frame, text="准备就绪，输入电影名称开始搜索",
                                     font=('Microsoft YaHei UI', 9),
                                     fg=self.COLORS['text2'], bg=self.COLORS['bg'],
                                     anchor=tk.W)
        self.status_label.pack(side=tk.LEFT)

        self.cloud_status = tk.Label(status_frame, text="☁️ 百度网盘",
                                     font=('Microsoft YaHei UI', 9),
                                     fg=self.COLORS['text2'], bg=self.COLORS['bg'])
        self.cloud_status.pack(side=tk.RIGHT, padx=(10, 0))

        # ========== 进度条 ==========
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate',
                                        length=200, style='TProgressbar')
        style.layout('TProgressbar', [
            ('Horizontal.Progressbar.trough', {'children': [('Horizontal.Progressbar.pbar', {
                'side': 'left', 'sticky': 'ns'})], 'sticky': 'ns'}),
            ('Horizontal.Progressbar.label', {'sticky': ''})])

        # ========== 结果显示区 ==========
        result_container = tk.Frame(main_frame, bg=self.COLORS['bg'])
        result_container.pack(fill=tk.BOTH, expand=True)

        # Canvas + Scrollbar 实现滚动
        self.canvas = tk.Canvas(result_container, bg=self.COLORS['bg'],
                                highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(result_container, orient=tk.VERTICAL,
                                  command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.COLORS['bg'])

        self.scrollable_frame.bind('<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw',
                                  width=self.canvas.winfo_reqwidth)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定鼠标滚轮
        self.canvas.bind('<Enter>', lambda e: self.canvas.bind_all('<MouseWheel>',
                         lambda event: self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')))
        self.canvas.bind('<Leave>', lambda e: self.canvas.unbind_all('<MouseWheel>'))

        # 结果数量标签
        self.result_count_label = tk.Label(self.scrollable_frame, text="",
                                           font=('Microsoft YaHei UI', 10, 'bold'),
                                           fg=self.COLORS['text'], bg=self.COLORS['bg'])
        self.result_count_label.pack(anchor=tk.W, pady=(0, 10))

        # 占位提示
        self.placeholder = tk.Label(self.scrollable_frame,
                                     text="✨ 输入电影名称，点击搜索\n\n支持：流浪地球 / 星际穿越 / 让子弹飞 ...",
                                     font=('Microsoft YaHei UI', 14),
                                     fg=self.COLORS['text2'], bg=self.COLORS['bg'],
                                     justify=tk.CENTER)
        self.placeholder.pack(expand=True, pady=100)

    def _on_entry_focus(self, event):
        """搜索框聚焦"""
        if self.search_var.get() == "输入电影名称，例如：流浪地球":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=self.COLORS['text'])

    def _on_entry_blur(self, event):
        """搜索框失焦"""
        if not self.search_var.get().strip():
            self.search_entry.insert(0, "输入电影名称，例如：流浪地球")
            self.search_entry.config(fg=self.COLORS['text2'])

    def set_status(self, text: str, is_error: bool = False):
        """设置状态文字"""
        self.status_label.config(text=text,
                                 fg=self.COLORS['highlight'] if is_error else self.COLORS['text2'])
        self.root.update_idletasks()

    def do_search(self):
        """执行搜索"""
        keyword = self.search_var.get().strip()
        if not keyword or keyword == "输入电影名称，例如：流浪地球":
            messagebox.showinfo("提示", "请输入电影名称")
            return

        # 清空旧结果
        self._clear_results()

        # 显示进度
        self.search_btn.config(state=tk.DISABLED, text="搜索中...")
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.start(10)
        self.set_status(f"🔍 正在搜索「{keyword}」...")

        # 异步搜索
        thread = threading.Thread(target=self._search_thread, args=(keyword,), daemon=True)
        thread.start()

    def _search_thread(self, keyword: str):
        """搜索线程"""
        try:
            from cloud_movie_saver.search.engine import SearchEngine
            from cloud_movie_saver.organizer import MovieManager

            engine = SearchEngine()
            manager = MovieManager()

            result_set = engine.search(keyword)
            sorted_results = result_set.sort_by_quality()[:30]

            # 整理结果
            results = []
            for r in sorted_results:
                organized = manager.organize_result(r)
                results.append(organized)

            # 更新UI
            self.root.after(0, self._display_results, results, keyword)

        except Exception as e:
            self.root.after(0, self._search_error, str(e))

    def _search_error(self, error_msg: str):
        """搜索错误处理"""
        self.progress.stop()
        self.progress.pack_forget()
        self.search_btn.config(state=tk.NORMAL, text="搜索")
        self.set_status(f"❌ 搜索失败: {error_msg}", is_error=True)

    def _clear_results(self):
        """清空结果"""
        for widget in self.scrollable_frame.winfo_children():
            if widget not in (self.placeholder, self.result_count_label):
                widget.destroy()
        self.placeholder.pack_forget()

    def _display_results(self, results: List[Dict], keyword: str):
        """显示结果"""
        self.progress.stop()
        self.progress.pack_forget()
        self.search_btn.config(state=tk.NORMAL, text="搜索")

        self.search_results = results

        if not results:
            self.placeholder.config(text=f"😕 未找到「{keyword}」的资源\n\n试试其他关键词，或检查网络连接")
            self.placeholder.pack(expand=True, pady=100)
            self.set_status(f"未找到「{keyword}」的相关资源")
            return

        self.placeholder.pack_forget()
        self.result_count_label.config(text=f"📀 找到 {len(results)} 部电影")

        # 更新云盘状态
        self._update_cloud_status()

        # 显示每个结果
        for idx, item in enumerate(results):
            card = self._create_result_card(self.scrollable_frame, idx, item)
            card.pack(fill=tk.X, pady=(0, 8), padx=2)

        self.set_status(f"✅ 搜索完成，共 {len(results)} 部电影")

    def _create_result_card(self, parent, idx: int, item: Dict) -> tk.Frame:
        """创建结果卡片"""
        card = tk.Frame(parent, bg=self.COLORS['card'],
                       highlightbackground=self.COLORS['border'],
                       highlightthickness=1, padx=15, pady=12)

        # 标题行
        title_frame = tk.Frame(card, bg=self.COLORS['card'])
        title_frame.pack(fill=tk.X)

        num_label = tk.Label(title_frame, text=f"#{idx+1}", font=('Segoe UI', 9),
                            fg=self.COLORS['highlight'], bg=self.COLORS['card'])
        num_label.pack(side=tk.LEFT, padx=(0, 8))

        movie_name = item.get('name', '未知')
        year = item.get('year', '')
        year_str = f" ({year})" if year else ""
        name_label = tk.Label(title_frame, text=f"{movie_name}{year_str}",
                              font=('Microsoft YaHei UI', 12, 'bold'),
                              fg=self.COLORS['text'], bg=self.COLORS['card'],
                              anchor=tk.W)
        name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 分类标签
        categories = item.get('categories', ['未分类'])
        cat_text = ' / '.join(categories)
        cat_label = tk.Label(title_frame, text=f"[{cat_text}]",
                            font=('Microsoft YaHei UI', 9),
                            fg='#64b5f6', bg=self.COLORS['card'])
        cat_label.pack(side=tk.RIGHT, padx=(10, 0))

        # 资源信息
        resources = item.get('all_resources', [])
        resources_by_quality = item.get('resources_by_quality', {})

        if resources_by_quality:
            quality_frame = tk.Frame(card, bg=self.COLORS['card'])
            quality_frame.pack(fill=tk.X, pady=(6, 4))

            tk.Label(quality_frame, text="画质: ", font=('Microsoft YaHei UI', 9),
                    fg=self.COLORS['text2'], bg=self.COLORS['card']).pack(side=tk.LEFT)

            for quality, res_list in resources_by_quality.items():
                count = len(res_list)
                q_colors = {
                    '4K': '#ff5252', 'BluRay': '#ff6d00', 'Remux': '#ff1744',
                    '1080p': '#4caf50', '720p': '#2196f3', 'HDR': '#ff9800',
                    'Web-DL': '#9c27b0', '2K': '#00bcd4', '未知': '#888888',
                }
                q_color = '#' + (''.join(c for c in quality if c.isdigit() or c.isalpha())[:6] if not any(k in quality for k in q_colors) else '')
                # 用默认颜色
                for key, color in q_colors.items():
                    if key.lower() in quality.lower():
                        q_color = color
                        break
                else:
                    q_color = self.COLORS['text2']

                q_btn = tk.Label(quality_frame, text=f" {quality}({count}) ",
                                font=('Microsoft YaHei UI', 9),
                                fg=q_color, bg=self.COLORS['bg'], padx=4)
                q_btn.pack(side=tk.LEFT, padx=2)

        # 资源按钮
        if resources:
            btn_frame = tk.Frame(card, bg=self.COLORS['card'])
            btn_frame.pack(fill=tk.X, pady=(4, 0))

            # 只显示前3个资源
            for res in resources[:3]:
                res_type = res.get('type', '')
                res_url = res.get('url', '')
                res_quality = res.get('quality', '')
                code = res.get('extract_code', '')

                # 图标
                icons = {'magnet': '🧲', 'baidu': '☁️', 'quark': '☁️', 'xunlei': '⚡',
                        'ed2k': '🔗', 'direct': '🔗', 'torrent': '📦', 'thunder': '⚡'}
                icon = icons.get(res_type, '🔗')
                label_text = f"{icon} {res_quality} {res_type}"

                if code:
                    label_text += f" (密码: {code})"

                url_short = res_url[:50] + '...' if len(res_url) > 50 else res_url
                label_text += f"\n    {url_short}"

                res_label = tk.Label(btn_frame, text=label_text,
                                     font=('Consolas', 8),
                                     fg=self.COLORS['text2'], bg=self.COLORS['card'],
                                     anchor=tk.W, justify=tk.LEFT, cursor='hand2')
                res_label.pack(fill=tk.X, pady=1)
                res_label.bind('<Button-1>', lambda e, u=res_url: self._open_url(u))

            if len(resources) > 3:
                tk.Label(btn_frame, text=f"    ... 还有 {len(resources)-3} 个资源",
                        font=('Microsoft YaHei UI', 8),
                        fg=self.COLORS['text2'], bg=self.COLORS['card']).pack(anchor=tk.W)

        # 底部操作按钮
        action_frame = tk.Frame(card, bg=self.COLORS['card'])
        action_frame.pack(fill=tk.X, pady=(8, 0))

        # 保存到云盘按钮
        baidu_links = [r for r in resources if r.get('type') == 'baidu' or 'pan.baidu.com' in r.get('url', '')]
        if baidu_links:
            save_btn = tk.Button(action_frame, text="☁️ 保存到百度网盘",
                                 command=lambda r=baidu_links, n=movie_name: self._save_to_baidu(r, n),
                                 bg=self.COLORS['accent'], fg='#ffffff',
                                 font=('Microsoft YaHei UI', 9),
                                 relief=tk.FLAT, padx=12, pady=4,
                                 cursor='hand2', activebackground='#154580')
            save_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 复制磁力链接
        magnets = [r for r in resources if r.get('type') == 'magnet']
        if magnets:
            magnet_btn = tk.Button(action_frame, text="🧲 复制磁力链接",
                                   command=lambda m=magnets: self._copy_magnet(m),
                                   bg=self.COLORS['bg2'], fg=self.COLORS['text'],
                                   font=('Microsoft YaHei UI', 9),
                                   relief=tk.FLAT, padx=12, pady=4,
                                   cursor='hand2', activebackground=self.COLORS['accent'])
            magnet_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 在浏览器打开
        open_btn = tk.Button(action_frame, text="🌐 在浏览器打开",
                             command=lambda r=resources: self._open_first_link(r),
                             bg=self.COLORS['bg2'], fg=self.COLORS['text'],
                             font=('Microsoft YaHei UI', 9),
                             relief=tk.FLAT, padx=12, pady=4,
                             cursor='hand2', activebackground=self.COLORS['accent'])
        open_btn.pack(side=tk.LEFT)

        return card

    def _update_cloud_status(self):
        """更新云盘状态"""
        from cloud_movie_saver.cloud.baidu import BaiduCloud
        bd = BaiduCloud()
        if bd.is_configured:
            self.cloud_status.config(text="☁️ 百度网盘 ✅", fg=self.COLORS['success'])
        else:
            self.cloud_status.config(text="☁️ 百度网盘 ⚠️ 未配置", fg=self.COLORS['warning'])

    def _open_url(self, url: str):
        """打开链接"""
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def _open_first_link(self, resources: List[Dict]):
        """打开第一个链接"""
        if resources:
            self._open_url(resources[0].get('url', ''))

    def _copy_magnet(self, magnets: List[Dict]):
        """复制磁力链接"""
        if not magnets:
            return
        try:
            import pyperclip
            pyperclip.copy(magnets[0].get('url', ''))
            messagebox.showinfo("已复制", "磁力链接已复制到剪贴板!")
        except ImportError:
            # 降级: 显示在状态栏
            url = magnets[0].get('url', '')
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("已复制", "磁力链接已复制到剪贴板!")

    def _save_to_baidu(self, baidu_links: List[Dict], movie_name: str):
        """保存到百度网盘"""
        from cloud_movie_saver.cloud.baidu import BaiduCloud

        bd = BaiduCloud()
        if not bd.is_configured:
            messagebox.showwarning("未配置", "请先配置百度网盘的 BDUSS 和 STOKEN\n运行: python setup.py")
            return

        if not bd.login():
            messagebox.showerror("登录失败", "百度网盘登录失败，Cookie可能已过期")
            return

        def save_thread():
            saved = 0
            for link in baidu_links:
                url = link.get('url', '')
                code = link.get('extract_code', '')
                save_dir = f"/已保存电影/{movie_name}"

                self.root.after(0, self.set_status, f"正在保存 {movie_name} 到百度网盘...")
                success, msg = bd.save_share_link(url, code, save_dir)
                if success:
                    saved += 1
                    self.root.after(0, messagebox.showinfo, "保存成功",
                                    f"✓ {movie_name} 已保存到百度网盘!")
                else:
                    self.root.after(0, self.set_status, f"保存失败: {msg}", True)

            if saved == 0:
                self.root.after(0, self.set_status, "❌ 保存失败，链接可能已失效", True)

        thread = threading.Thread(target=save_thread, daemon=True)
        thread.start()
        self.set_status(f"☁️ 正在保存到百度网盘...")

    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """启动GUI"""
    app = CloudMovieSaverGUI()
    app.run()


if __name__ == '__main__':
    main()
