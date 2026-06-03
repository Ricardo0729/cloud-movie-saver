"""创建桌面快捷方式"""
import os, sys, win32com.client

desktop = os.path.expanduser('~/Desktop')
project_dir = os.path.dirname(os.path.abspath(__file__))
shortcut_path = os.path.join(desktop, 'CloudMovieSaver.lnk')

shell = win32com.client.Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(shortcut_path)
shortcut.Targetpath = sys.executable  # python.exe路径
shortcut.Arguments = '-m cloud_movie_saver.main gui'
shortcut.WorkingDirectory = project_dir
shortcut.WindowStyle = 4  # 不显示窗口
shortcut.Description = 'CloudMovieSaver - 云盘电影搜索保存工具'
shortcut.IconLocation = sys.executable + ', 0'
shortcut.save()

print(f'✅ 桌面快捷方式已创建: {shortcut_path}')
print('双击桌面 CloudMovieSaver 图标启动 🎬')
