"""安全演示入口：播放完整动画，但不写入右键菜单注册表。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

# dragon_delete 导入时会请求注册右键菜单；演示模式明确禁用该副作用。
import menu_registry
menu_registry.ensure_registered = lambda: None

import dragon_delete


if __name__ == "__main__":
    dragon_delete.main()
