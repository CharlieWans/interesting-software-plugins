"""
右键菜单卸载脚本 (Windows)
运行: python uninstall_context_menu.py
作用: 移除 "吃豆人删除" 右键菜单项。
      卸载逻辑统一复用 src/menu_registry.py。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from menu_registry import unregister


def main():
    ok = unregister()
    print("[成功] 右键菜单已移除" if ok else "[失败] 移除右键菜单出错")


if __name__ == "__main__":
    main()
