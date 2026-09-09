"""
像素吃豆人球 删除动画 — 主程序
流程: 右键菜单启动 → 记录按下时刻的鼠标位置(即文件位置) →
      全屏出现像素风确认框(吃掉它?  YES / NO) →
      是: 球从屏幕右侧匀速向左移动(嘴一张一合, 沿途掉粒子) →
          约3秒到达文件位置(嘴对文件) → 短暂悬停 → 嘴闭合粉碎文件 →
          粒子爆发 → 继续向左走出屏幕
      否: 直接向左走出屏幕
整体是"从右到左"的过程

定位: 使用鼠标右键按下时刻的位置 (右键文件时鼠标就在文件附近),
      读鼠标位置是瞬时 API, 不碰系统桌面控件, 绝不卡屏。
"""
import os
import sys
import math
import random
import traceback
import ctypes
from ctypes import wintypes

# 源码测试版由 .venv\Scripts\pythonw.exe 从 Explorer 启动时，PyQt 有时无法
# 自动发现 qwindows.dll。必须在导入 Qt 模块前指定该虚拟环境的插件目录。
if not getattr(sys, "frozen", False):
    try:
        import PyQt5
        _qt_plugins = os.path.join(os.path.dirname(PyQt5.__file__), "Qt5", "plugins")
        _qt_platforms = os.path.join(_qt_plugins, "platforms")
        if os.path.isdir(_qt_platforms):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _qt_platforms
            os.environ["QT_PLUGIN_PATH"] = _qt_plugins
    except Exception:
        pass

from PyQt5.QtCore import Qt, QTimer, QRectF, QDateTime, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QGuiApplication
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QHBoxLayout, QPushButton, QVBoxLayout
)

from desktop_icons import get_desktop_icon_position, is_desktop_item

try:
    import send2trash
    HAVE_SEND2TRASH = True
except ImportError:
    HAVE_SEND2TRASH = False

# ---- 路径: 兼容「源码运行」与「PyInstaller 打包」 ----
if getattr(sys, "frozen", False):
    # 打包后: exe 所在目录即程序根目录 (build.bat 会把 assets 复制到旁边)
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSETS_DIR = os.path.join(APP_DIR, "assets")

# ---- 首次运行: 自动注册右键菜单 (静默, 失败不影响动画) ----
try:
    from menu_registry import ensure_registered
    ensure_registered()
except Exception:
    pass

# ============ 配置 ============
# 球大小 ≈ 桌面文件图标 (32-48px). 精灵 192x192
SPRITE_SCALE = 0.44        # → ~84px 球 (约桌面图标两倍大, 嘴能吞下文件夹)
FLY_IN_TIME = 3000         # 从右到文件 用时 ms (慢速)
FLY_LEFT_SPEED = 0.9       # 吃完后向左出屏速度倍率
FLIGHT_FLAP_MS = 150       # 嘴张合帧间隔 ms
HOVER_FLAP_MS = 160        # 悬停时嘴张合帧间隔
HOVER_BOB = 4              # 悬停上下浮动幅度 px
AUTO_EAT_DELAY = 220       # 对准目标后的短暂停顿；不显示二次确认框
MOUTH_CENTER_X = 0.20      # 精灵内部嘴部视觉中心（相对宽度）
ICON_POSITION_RETRIES = 12 # Explorer 菜单关闭后最多等待约 1.5 秒
TRAIL_INTERVAL = 32        # 高频像素尾焰发射间隔 ms
TRAIL_PARTICLES_PER_EMIT = 3
PARTICLE_COUNT = 32        # 最后一口吞噬时的像素爆裂数量
CHEW_FRAME_MS = 105        # 每一次咬合的帧间隔
# 三次清晰的“张嘴—闭合”咬合，最后闭嘴完成吞噬。
EAT_FRAME_SEQUENCE = (0, 1, 2, 3, 2, 1, 2, 3, 4, 3, 4, 5)

# 粒子配色 (吃豆人风格)
PARTICLE_COLORS = [
    (255, 230, 52), (255, 139, 0), (247, 66, 138),
    (53, 211, 255), (114, 108, 255), (255, 246, 212),
]

# 鼠标位置读取 (Windows) — 右键按下瞬间定位, 瞬时 API 不卡
def get_cursor_pos():
    """获取鼠标当前位置 (屏幕坐标, 物理像素)"""
    try:
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)
    except Exception:
        return None


class Particle:
    """单个粒子: 位置、速度、寿命"""
    def __init__(self, x, y, drift=0.0):
        self.x = x
        self.y = y
        self.vx = abs(random.uniform(0.35, 1.8)) + drift  # 球向左飞，拖尾留在右侧
        self.vy = random.uniform(-1.45, 1.15) - 0.25
        self.life = random.uniform(420, 920)
        self.max_life = self.life
        self.size = random.randint(3, 8)
        self.color = random.choice(PARTICLE_COLORS)
        self.streak = random.random() < 0.42

    def update(self, dt_ms):
        self.life -= dt_ms
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.06

    @property
    def alpha(self):
        return max(0, int(255 * (self.life / self.max_life)))


class DragonWindow(QWidget):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.state = "positioning"  # positioning | fly_in | hover | eat | fly_left
        self.dialog = None

        # ---- 精灵 ----
        self.fly_frames   = [self._load(f"charizard_fly{i}.png") for i in (1, 2, 3, 4, 5, 6, 7, 8)]
        self.hover_frames = [self._load(f"charizard_hover{i}.png") for i in (1, 2, 3, 4)]
        self.eat_frames   = [self._load(f"charizard_eat{i}.png") for i in (1, 2, 3, 4, 5, 6)]
        self.frame_idx = 0
        self.eat_frame = 0
        self.eat_step = 0
        self.flap_ms = FLIGHT_FLAP_MS
        self.flap_timer = 0

        # 位置与运动
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.base_y = 0.0
        self.hover_t = 0.0
        self.file_x = 0.0          # 文件屏幕坐标
        self.file_y = 0.0
        self.start_x = 0.0
        self.start_y = 0.0
        self.flight_start = 0
        self.flight_duration = 0
        self.flying_to_target = False
        self.position_attempts = 0
        self.position_source = ""

        # 粒子
        self.particles = []
        self.trail_timer = 0
        self.eat_timer = 0

        # 窗口设置: 全屏透明置顶 + 点击穿透 (不需要鼠标交互)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.Tool | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

        screen = QGuiApplication.primaryScreen()
        self.SW, self.SH = screen.size().width(), screen.size().height()

        # 精灵尺寸 (球 ≈ 文件图标大小)
        base = self.fly_frames[0]
        self.sp_w = max(1, int(base.width() * SPRITE_SCALE))
        self.sp_h = max(1, int(base.height() * SPRITE_SCALE))

        # 动画时钟
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

        self.last_ms = 0
        # 右键菜单关闭、Explorer 恢复桌面选中态后再读取图标位置，避免竞态。
        QTimer.singleShot(140, self._begin_at_desktop_icon)

    # ---------- 工具 ----------
    def _load(self, name):
        return QPixmap(os.path.join(ASSETS_DIR, name))

    def _start_flight(self, sx, sy, tx, ty, duration):
        self.start_x, self.start_y = sx, sy
        self.target_x, self.target_y = tx, ty
        self.flight_start = self._now()
        self.flight_duration = duration
        self.flying_to_target = True

    def _now(self):
        return QDateTime.currentMSecsSinceEpoch()

    def _begin_at_desktop_icon(self):
        """只接受实际桌面图标坐标；绝不退回到鼠标指针。"""
        position = get_desktop_icon_position(self.file_path)
        if not position:
            self.position_attempts += 1
            if self.position_attempts < ICON_POSITION_RETRIES:
                QTimer.singleShot(120, self._begin_at_desktop_icon)
            else:
                # 不能对齐时直接结束，避免播放看似指向鼠标的错误动画。
                self.close()
            return

        icon_center, self.position_source = position
        self.file_x, self.file_y = map(float, icon_center)
        self.pos_x = float(self.SW + self.sp_w)
        self.pos_y = self.file_y - self.sp_h / 2
        target_x = self.file_x - self.sp_w * MOUTH_CENTER_X
        target_y = self.file_y - self.sp_h / 2
        self.state = "fly_in"
        self._start_flight(self.pos_x, self.pos_y, target_x, target_y, FLY_IN_TIME)

    # ---------- 主循环 ----------
    def _tick(self):
        now = self._now()
        dt = now - self.last_ms if self.last_ms else 16
        self.last_ms = now
        dt = max(1, min(dt, 50))

        # 嘴张合
        self.flap_timer += dt
        if self.flap_timer >= self.flap_ms:
            self.flap_timer = 0
            self.frame_idx += 1

        if self.state == "fly_in":
            self.flap_ms = FLIGHT_FLAP_MS
            self._update_flight_linear()
            # 沿途掉粒子
            self.trail_timer += dt
            if self.trail_timer >= TRAIL_INTERVAL:
                self.trail_timer = 0
                self._drop_trail_particle()
        elif self.state == "fly_left":
            self.flap_ms = FLIGHT_FLAP_MS
            self._update_flight_linear()
        elif self.state == "hover":
            self.flap_ms = HOVER_FLAP_MS
            self.hover_t += dt
            self.pos_y = self.base_y + math.sin(self.hover_t / 260) * HOVER_BOB
        elif self.state == "eat":
            self.flap_ms = 120
            # 连续咬合：每一轮闭嘴都会有文件碎片从嘴边飞出。
            self.eat_timer += dt
            if self.eat_timer >= CHEW_FRAME_MS:
                self.eat_timer = 0
                self.eat_step += 1
                if self.eat_step < len(EAT_FRAME_SEQUENCE):
                    self.eat_frame = EAT_FRAME_SEQUENCE[self.eat_step]
                    if self.eat_frame >= 3:
                        self._spawn_bite_fragments()
                else:
                    # 最后一口完成，再进行一次更大的像素爆裂并离场。
                    self._burst_particles()
                    self._fly_left()
            # 更新粒子
            for p in self.particles:
                p.update(dt)
            self.particles = [p for p in self.particles if p.life > 0]

        # 更新所有粒子
        if self.state in ("fly_in", "fly_left"):
            for p in self.particles:
                p.update(dt)
            self.particles = [p for p in self.particles if p.life > 0]

        self.update()

    def _update_flight_linear(self):
        """匀速直线运动"""
        if not self.flying_to_target:
            return
        now = self._now()
        t = (now - self.flight_start) / self.flight_duration
        if t >= 1.0:
            self.pos_x, self.pos_y = self.target_x, self.target_y
            self.flying_to_target = False
            if self.state == "fly_in":
                self._enter_hover()
            elif self.state == "fly_left":
                self.close()
        else:
            self.pos_x = self.start_x + (self.target_x - self.start_x) * t
            self.pos_y = self.start_y + (self.target_y - self.start_y) * t

    def _speed(self):
        """像素/ms 移动速度"""
        return (self.SW + self.sp_w) / FLY_IN_TIME

    def _drop_trail_particle(self):
        """移动时在身后(左侧)掉粒子"""
        # 核心、彩色碎片与偶发的大亮块组成三层像素尾焰。
        for index in range(TRAIL_PARTICLES_PER_EMIT):
            x = self.pos_x + self.sp_w * random.uniform(0.76, 0.95)
            y = self.pos_y + self.sp_h * random.uniform(0.20, 0.80)
            p = Particle(x, y, drift=random.uniform(0.05, 0.65))
            p.vx += index * 0.22
            if index == 0:
                p.size = random.randint(6, 10)
                p.life = p.max_life = random.uniform(500, 980)
            self.particles.append(p)

    # ---------- 流程 ----------
    def _enter_hover(self):
        self.state = "hover"
        self.base_y = self.file_y - self.sp_h / 2
        self.hover_t = 0
        # 右键菜单本身即为删除确认：仅保留一个短暂停顿来强调瞄准动作。
        QTimer.singleShot(AUTO_EAT_DELAY, self._eat_file)

    def _eat_file(self):
        """点 YES 即判定文件消失 (立即删除, 不等吃动画播完)"""
        # 先删文件: 确认的一瞬间文件夹就从桌面消失
        self._delete_file()
        self.state = "eat"
        self.eat_frame = 0
        self.eat_step = 0
        self.eat_timer = 0
        # 球嘴对准文件 (球左缘在文件位置)
        self.pos_x = self.file_x - self.sp_w * MOUTH_CENTER_X
        self.pos_y = self.file_y - self.sp_h / 2

    def _burst_particles(self):
        """粉碎完成, 粒子爆发 (文件已在 _eat_file 时删除)"""
        mouth_x = self.pos_x + self.sp_w * 0.02
        mouth_y = self.pos_y + self.sp_h * 0.5
        for _ in range(PARTICLE_COUNT):
            p = Particle(mouth_x, mouth_y)
            p.vx = random.uniform(-2.6, 2.2)
            p.vy = random.uniform(-2.8, 1.8)
            p.life = p.max_life = random.uniform(420, 900)
            self.particles.append(p)

    def _spawn_bite_fragments(self):
        """每次咬合落下少量、方向各异的文件像素碎片。"""
        mouth_x = self.pos_x + self.sp_w * 0.04
        mouth_y = self.pos_y + self.sp_h * random.uniform(0.34, 0.66)
        for _ in range(random.randint(3, 5)):
            p = Particle(mouth_x, mouth_y)
            p.vx = random.uniform(-1.4, 1.7)
            p.vy = random.uniform(-2.0, 0.8)
            p.life = p.max_life = random.uniform(220, 480)
            p.size = random.randint(2, 5)
            self.particles.append(p)

    def _fly_left(self):
        """继续向左, 走出屏幕"""
        self.state = "fly_left"
        # 从当前位置向左, 直到完全出屏
        target_x = -self.sp_w * 2
        dist = self.pos_x - target_x
        duration = int(dist / self._speed() / FLY_LEFT_SPEED)
        self._start_flight(self.pos_x, self.pos_y, target_x, self.pos_y, duration)

    def _delete_file(self):
        """把目标删除到回收站 — 支持文件 / 文件夹 / 快捷方式。

        优先 send2trash (回收站, 可恢复); 若失败:
          - 文件夹: 用 shutil.rmtree 递归删除
          - 文件/快捷方式: 用 os.remove
        """
        target = self.file_path
        if not os.path.lexists(target):
            return  # 已不存在 (如无效的 .lnk)
        if HAVE_SEND2TRASH:
            try:
                send2trash.send2trash(target)
                return
            except Exception:
                pass
        try:
            if os.path.isdir(target) and not os.path.islink(target):
                import shutil
                shutil.rmtree(target)     # 文件夹 (非符号链接) 递归删除
            else:
                os.remove(target)          # 文件 / 快捷方式 / 符号链接
        except Exception:
            pass

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        painter = QPainter(self)

        # 粒子
        for p in self.particles:
            # 每颗粒子都有一格深色像素阴影，避免在浅色桌面上丢失轮廓。
            painter.setBrush(QColor(28, 25, 38, max(0, p.alpha - 35)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(p.x + 2, p.y + 2, p.size, p.size))
            if p.streak:
                painter.drawRect(QRectF(p.x - p.size * 1.4, p.y + p.size * 0.25,
                                        p.size * 1.4, max(2, p.size * 0.5)))
            painter.setBrush(QColor(*p.color, p.alpha))
            painter.drawRect(QRectF(p.x, p.y, p.size, p.size))
            if p.streak:
                painter.setBrush(QColor(255, 255, 238, max(0, p.alpha - 55)))
                painter.drawRect(QRectF(p.x + p.size * 0.25, p.y + p.size * 0.25,
                                        max(1, p.size * 0.35), max(1, p.size * 0.35)))

        # 文件图标 (悬停时在嘴前; 吃时被嘴覆盖粉碎)
        if self.state in ("hover", "eat"):
            self._draw_file_icon(painter)

        # 球
        if self.state in ("fly_in", "fly_left", "hover", "eat"):
            self._draw_ball(painter)

        painter.end()

    def _draw_ball(self, painter):
        if self.state == "eat":
            pix = self.eat_frames[self.eat_frame]
        elif self.state == "hover":
            pix = self.hover_frames[self.frame_idx % len(self.hover_frames)]
        else:
            pix = self.fly_frames[self.frame_idx % len(self.fly_frames)]

        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.drawPixmap(int(self.pos_x), int(self.pos_y), self.sp_w, self.sp_h, pix)

    def _draw_file_icon(self, painter):
        """文件方块: 悬停时在嘴前, 吃时被嘴覆盖缩小消失"""
        if not os.path.exists(self.file_path):
            return
        # 文件图标大小 (与球嘴匹配)
        size = self.sp_w // 2
        x = self.file_x - size / 2
        y = self.file_y - size / 2

        if self.state == "eat":
            # 文件从靠近嘴的一侧被逐段啃掉，而非整体等比缩小。
            progress = min(1.0, self.eat_step / (len(EAT_FRAME_SEQUENCE) - 1))
            visible_w = max(2, int(size * (1 - progress * 0.96)))
            if visible_w < 3:
                return
        else:
            visible_w = size

        painter.setBrush(QColor(230, 230, 235))
        painter.setPen(QColor(90, 90, 100))
        painter.drawRect(int(x), int(y), visible_w, int(size * 1.25))
        line_y = y + size * 0.2
        for i in range(3):
            painter.drawLine(int(x + size * 0.15), int(line_y + i * size * 0.3),
                             int(x + visible_w * 0.85), int(line_y + i * size * 0.3))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class AskDialog(QWidget):
    """像素风确认对话框"""
    response = pyqtSignal(bool)

    def __init__(self, file_path, position_source, x, y):
        super().__init__(None)
        self.file_path = file_path
        self.selected = 0  # 0=NO, 1=YES

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(self._css())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)

        msg = QLabel(
            f"吃 掉 它 ?\n\n{os.path.basename(file_path)}"
            f"\n\n定位：{position_source}  ·  ({int(x)}, {int(y)})"
        )
        msg.setObjectName("msg")
        msg.setAlignment(Qt.AlignCenter)
        outer.addWidget(msg)

        btn_row = QHBoxLayout()
        self.btn_no = QPushButton("NO")
        self.btn_yes = QPushButton("YES")
        for b in (self.btn_no, self.btn_yes):
            b.setFixedSize(90, 44)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            btn_row.addWidget(b)
        self.btn_no.clicked.connect(lambda: self._respond(False))
        self.btn_yes.clicked.connect(lambda: self._respond(True))
        outer.addLayout(btn_row)

        self._update_style()

    def _css(self):
        return """
            QWidget { background: rgba(20, 20, 30, 210); color: #fff; }
            QLabel#msg { font-size: 16px; font-weight: bold; padding: 6px; color: #ffe9a8; }
            QPushButton {
                background: #3a3a50; color: #ddd; border: 2px solid #666;
                font-size: 15px; font-weight: bold; border-radius: 0;
            }
            QPushButton:hover { background: #4a4a66; }
            QPushButton[sel="1"] { background: #ff8c3a; color: #000; border: 2px solid #ffd070; }
        """

    def _update_style(self):
        self.btn_no.setProperty("sel", "1" if self.selected == 0 else "0")
        self.btn_yes.setProperty("sel", "1" if self.selected == 1 else "0")
        self.btn_no.style().unpolish(self.btn_no)
        self.btn_no.style().polish(self.btn_no)
        self.btn_yes.style().unpolish(self.btn_yes)
        self.btn_yes.style().polish(self.btn_yes)

    def showEvent(self, event):
        super().showEvent(event)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )
        self.setFocus()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Tab):
            self.selected = 1 - self.selected
            self._update_style()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._respond(self.selected == 1)
        elif event.key() == Qt.Key_Escape:
            self._respond(False)

    def _respond(self, yes):
        self.response.emit(yes)


def main():
    app = QApplication(sys.argv)

    # 解析右键菜单传入的目标 (文件 / 文件夹 / 文件夹背景)
    file_path = None
    try:
        from menu_registry import resolve_target
        target = resolve_target()
        if target:
            _kind, _path = target
            file_path = _path
    except Exception:
        pass

    # 兜底: 兼容旧式直接传路径 / 演示模式
    if file_path is None:
        for a in sys.argv[1:]:
            if a.startswith("--"):
                continue
            if os.path.exists(a):
                file_path = os.path.abspath(a)
                break

    if file_path is None:
        # 演示模式: 在应用目录下建一个临时 demo 文件, 不删真文件
        file_path = os.path.join(APP_DIR, "demo.txt")
        with open(file_path, "w") as f:
            f.write("demo")

    # 正式右键调用只在桌面项目生效；演示模式仍可运行。
    if len(sys.argv) > 1 and not is_desktop_item(file_path):
        sys.exit(0)

    w = DragonWindow(file_path)
    w.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_path = os.path.join(APP_DIR, "dragon_delete_error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 50 + "\n")
            f.write(traceback.format_exc())
            f.write("\n")
        raise
