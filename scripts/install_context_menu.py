"""
右键菜单注册脚本 (Windows)
运行: python install_context_menu.py
作用: 注册 "吃豆人删除" 右键菜单项 (文件 / 文件夹 / 文件夹背景)。
      注册逻辑统一复用 src/menu_registry.py, 确保与程序首次运行自动注册一致。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from menu_registry import register, build_command


def main():
    result = register()
    if result == "error":
        print("[失败] 写入注册表出错")
        sys.exit(1)
    elif result == "registered":
        print("[成功] 右键菜单已注册: '吃豆人删除'")
    else:
        print("[提示] 右键菜单已存在且无需更新")
    print("       执行命令:", build_command())


if __name__ == "__main__":
    main()
