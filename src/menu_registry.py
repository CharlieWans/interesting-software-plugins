"""
右键菜单注册/卸载模块 — 同时支持「源码运行」与「打包 exe」两种模式。

菜单项: "吃豆人删除"
作用对象:
  - 文件右键 (HKCU\\Software\\Classes\\*\\shell\\PacManDelete)
  - 文件夹右键 (HKCU\\Software\\Classes\\Directory\\shell\\PacManDelete)


命令解析优先级 (打包后 exe 就是自身, 直接传给子进程):
  - 文件/文件夹: "exe" "%1"
  - 源码模式:    pythonw.exe dragon_delete.py "%1"

首次运行自动注册 (见 ensure_registered):
  - 读取注册表当前命令, 若与期望命令不一致则重新写入。
  - 用 SendMessageTimeoutW 广播刷新资源管理器。
"""
import os
import sys
import ctypes
from ctypes import wintypes

import winreg


MENU_NAME = "吃豆人删除"
REG_KEY_NAME = "PacManDelete"

# 返回码, 供 uninstall 判断
REGISTERED = "registered"        # 本次写入成功
ALREADY_OK = "already_ok"        # 无需改动
ERROR = "error"                  # 失败


# ---------------------------------------------------------------- 命令解析
def _frozen_exe():
    """打包后返回 exe 绝对路径; 未打包返回 None。"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return None


def _repo_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pythonw():
    exe = sys.executable
    d = os.path.dirname(exe)
    pythonw = os.path.join(d, "pythonw.exe")
    return pythonw if os.path.exists(pythonw) else exe


def resolve_target():
    """返回 (kind, path): kind in {"file","dir","dir_bg"}"""
    args = sys.argv[1:]
    if not args:
        return None
    first = args[0]
    if first.startswith('"') and first.endswith('"') and len(first) > 1:
        first = first[1:-1]  # 去掉可能的外层引号 (Windows 有时带引号传参)
    if first in ("--uninstall",):
        return None
    if first.startswith("--"):
        # --file=xxx / --dir=xxx / --dir-bg=xxx
        for prefix, kind in (("--file=", "file"), ("--dir=", "dir"), ("--dir-bg=", "dir_bg")):
            if first.startswith(prefix):
                return (kind, first[len(prefix):])
    if os.path.isdir(first):
        return ("dir", first)
    if os.path.exists(first):
        return ("file", first)
    return None


def build_command():
    """生成注册表里的命令字符串。"""
    exe = _frozen_exe()
    if exe:
        return f'"{exe}" "%1"'
    script = os.path.join(_repo_root(), "src", "dragon_delete.py")
    return f'"{_pythonw()}" "{script}" "%1"'


def _icon_path():
    return os.path.join(_repo_root(), "assets", "icon.ico")


def _keys():
    return [
        fr"Software\Classes\*\shell\{REG_KEY_NAME}",
        fr"Software\Classes\Directory\shell\{REG_KEY_NAME}",
    ]


def _legacy_keys():
    """清理旧测试版曾注册的文件夹空白处菜单。"""
    return [r"Software\Classes\Directory\Background\shell\PacManDelete"]


def _remove_key(base):
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, base + r"\command")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, base)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------- 注册/卸载
def register():
    """写入/更新右键菜单。返回 REGISTERED / ALREADY_OK / ERROR"""
    command = build_command()
    icon = _icon_path()
    changed = False
    try:
        for base in _legacy_keys():
            _remove_key(base)
        for base in _keys():
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, base, 0, winreg.KEY_WRITE) as key:
                existing = ""
                try:
                    existing, _ = winreg.QueryValueEx(key, "")
                except OSError:
                    pass
                if existing != MENU_NAME:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, MENU_NAME)
                    changed = True
                # Icon (存在且一致就不重复写, 减少 explorer 刷新负担)
                try:
                    ico, _ = winreg.QueryValueEx(key, "Icon")
                except OSError:
                    ico = None
                if ico != icon:
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon)
                    changed = True
                # 旧测试版的 AppliesTo 筛选在部分 Explorer 版本会错误地隐藏菜单。
                try:
                    winreg.DeleteValue(key, "AppliesTo")
                    changed = True
                except FileNotFoundError:
                    pass

            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, base + r"\command", 0, winreg.KEY_WRITE) as key:
                try:
                    cur, _ = winreg.QueryValueEx(key, "")
                except OSError:
                    cur = None
                if cur != command:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
                    changed = True
    except Exception:
        return ERROR

    if changed:
        _refresh_explorer()
        return REGISTERED
    return ALREADY_OK


def unregister():
    """删除右键菜单项。返回 True/False"""
    try:
        for base in _keys() + _legacy_keys():
            _remove_key(base)
        _refresh_explorer()
        return True
    except Exception:
        return False


def ensure_registered():
    """首次运行自动注册。异常时静默失败 (不打扰动画)。"""
    try:
        r = register()
        if r == ERROR:
            pass
    except Exception:
        pass


def _refresh_explorer():
    """广播 WM_SETTINGCHANGE, 让资源管理器立即刷新右键菜单。"""
    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x001A, 0, 0,
            0x0002, 1000, None,
        )
    except Exception:
        pass


# ---------------------------------------------------------------- CLI
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--uninstall",):
        print("移除右键菜单: ", "成功" if unregister() else "失败")
    else:
        r = register()
        if r == ERROR:
            print("[失败] 写入注册表出错")
        elif r == REGISTERED:
            print("[成功] 右键菜单已注册: '吃豆人删除'")
        else:
            print("[提示] 右键菜单已存在且无需更新")
        print("命令:", build_command())
