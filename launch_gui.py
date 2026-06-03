#!/usr/bin/env python3
"""CloudMovieSaver GUI launcher - 直接启动图形界面，不经过CLI"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from cloud_movie_saver.gui_app import main as gui_main
    gui_main()
except Exception as e:
    import traceback
    # 如果GUI失败，回退到命令行
    print(f"GUI启动失败: {e}")
    traceback.print_exc()
    print("\n按Enter键退出...")
    input()
