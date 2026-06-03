"""创建桌面快捷方式"""
import os, sys, win32com.client

desktop = os.path.expanduser('~/Desktop')
project_dir = os.path.dirname(os.path.abspath(__file__))
shortcut_path = os.path.join(desktop, 'CloudMovieSaver.lnk')

# 删除旧的
for f in os.listdir(desktop):
    if 'CloudMovieSaver' in f:
        os.remove(os.path.join(desktop, f))

shell = win32com.client.Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(shortcut_path)
shortcut.Targetpath = sys.executable
shortcut.Arguments = 'launch_gui.py'
shortcut.WorkingDirectory = project_dir
shortcut.WindowStyle = 1
shortcut.Description = 'CloudMovieSaver - 云盘电影搜索保存工具'
shortcut.IconLocation = 'shell32.dll, 14'
shortcut.save()

print(f'✅ 桌面快捷方式已创建!')
print(f'   → {shortcut_path}')
print(f'\n双击桌面「🎬 CloudMovieSaver」图标启动 🎉')
