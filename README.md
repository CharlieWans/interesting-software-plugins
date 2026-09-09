# 🟡 吃豆人删除动画

给"删除文件"配上一个像素风吃豆人动画：吃豆人球从屏幕右侧匀速飞来（约 3 秒，嘴一张一合、沿途掉像素粒子），对准文件后直接一口吞下文件（文件瞬间进回收站）并炸出粒子，随后向左飞出屏幕。

> 像素风形象致敬电影《像素大战》(Pixels)。素材为代码生成的像素画，非官方素材。

## 功能

- 右键任意文件 / 文件夹 → 选择 **"吃豆人删除"** → 触发动画
- 吃豆人球从右侧匀速飞来，嘴对准文件位置，沿途掉落像素粒子
- 选择右键菜单后，文件**立即**删除到回收站（不等动画播完），随后球表演"连续啃食 + 粒子爆发 + 向左出屏"
- 首次运行 exe 会自动注册右键菜单（无需手动操作）

## 运行环境

- Windows 10 / 11（64 位）
- Python 3.8+（源码运行方式）

## 源码运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 注册右键菜单 (写入当前用户注册表)
python scripts\install_context_menu.py
```

完成以上两步后，右键任意文件即可看到 **"吃豆人删除"**。

命令行直跑：

```bash
python src\dragon_delete.py "C:\path\to\file.txt"   # 指定文件
python src\dragon_delete.py                          # 演示模式 (应用目录建 demo.txt)
```

## 打包成桌面应用

> 打包必须在 Windows 上执行（PyInstaller / Inno Setup 均为 Windows 工具）。

**方式一：绿色版（文件夹）**

```bat
scripts\build.bat
```

产物：`dist\吃豆人删除\`（内含 `PacManDelete.exe` + `assets\`）。把整个文件夹复制给别人即可用，首次双击 exe 自动注册右键菜单。

**方式二：专业安装包**

```text
1. 先运行 scripts\build.bat 生成 dist\吃豆人删除\
2. 安装 Inno Setup 6+  (https://jrsoftware.org/isinfo.php)
3. 运行 scripts\build_installer.bat (自动打包绿色版 + 编译安装包)
   ── 或手动: 右键 scripts\installer.iss → Compile
```

产物：`scripts\Output\吃豆人删除安装程序.exe`。双击安装后：

- **桌面自动生成吃豆人快捷图标**（默认创建，安装时可不勾选跳过）
- 开始菜单生成"吃豆人删除"与"卸载"快捷方式
- 右键菜单自动写入（文件 / 文件夹 / 文件夹空白处），卸载时自动清理

## 卸载

```bash
# 源码方式卸载右键菜单
python scripts\uninstall_context_menu.py
# 安装包方式 → 控制面板卸载即可 (会自动移除右键菜单)
```

## 项目结构

```
├── assets/                        # 像素吃豆人精灵图 + 应用图标
│   ├── charizard_fly1-8.png       # 飞行嘴张合帧
│   ├── charizard_hover1-4.png     # 悬停张合帧
│   ├── charizard_eat1-6.png       # 闭嘴粉碎帧
│   ├── icon.ico / icon.png        # 应用图标 (exe / 右键菜单)
├── src/
│   ├── dragon_delete.py           # 主程序 (动画 + 确认 + 删除)
│   └── menu_registry.py           # 右键菜单注册/卸载 (源码 & 打包共用)
├── scripts/
│   ├── generate_sprites.py        # 生成吃豆人精灵图
│   ├── make_icon.py               # 生成应用图标
│   ├── install_context_menu.py    # 注册右键菜单 (复用 menu_registry)
│   ├── uninstall_context_menu.py  # 移除右键菜单 (复用 menu_registry)
│   ├── build.bat                  # PyInstaller 打包 (绿色版)
│   ├── build_installer.bat        # 一键: 打包绿色版 + 编译安装包
│   └── installer.iss              # Inno Setup 安装包脚本
└── requirements.txt
```

## 自定义

想换形象 / 颜色？改 `scripts/generate_sprites.py` 里的调色板和绘制参数，重新运行：

```bash
python scripts\generate_sprites.py
```

> 注意：重新生成后需保持文件名不变（`charizard_fly1.png` 等），或同步修改主程序。

## 已知说明

- 删除走系统回收站（优先 `send2trash`，失败则 `os.remove` 永久删除）。
- 文件定位：读取**右键按下时刻的鼠标位置**（右键时鼠标就在文件附近）。若鼠标离文件较远，球会飞到鼠标位置而非文件图标，属正常现象。
- 主窗口全屏透明且点击穿透，不影响动画期间操作其他窗口；确认框是独立可点击的置顶窗口。
- 右键文件夹空白处 → 同样有 **"吃豆人删除"**（删除该文件夹本身）
