"""
生成像素吃豆人球精灵 v3
  - 单眼 (侧面视角, 一只黑眼睛)
  - 32x32 像素网格 (更细腻)
  - 8帧张合循环 (fly1-8, 更平滑)
  - eat 闭合粉碎序列 (eat1-6)
  - 嘴朝左
"""
from PIL import Image
import os
import math

PIXEL = 6
COLS, ROWS = 32, 32

BALL_Y = (255, 220, 0)
BALL_Y_D = (240, 142, 0)
BALL_Y_L = (255, 248, 146)
OUTLINE = (30, 20, 28)
MOUTH_DARK = (104, 22, 30)
MOUTH_LIGHT = (238, 66, 31)
EYE_WHITE = (255, 251, 224)
EYE_DARK = (18, 22, 38)
EYE_SHINE = (91, 227, 255)


def new_canvas():
    return [[None]*COLS for _ in range(ROWS)]

def paint(c, x, y, col):
    xi, yi = int(x), int(y)
    if 0 <= xi < COLS and 0 <= yi < ROWS:
        c[yi][xi] = col

def ellipse_px(c, cx, cy, rx, ry, col):
    for y in range(int(cy-ry)-1, int(cy+ry)+2):
        for x in range(int(cx-rx)-1, int(cx+rx)+2):
            if ((x-cx)/rx)**2 + ((y-cy)/ry)**2 <= 1.0:
                paint(c, x, y, col)

def render(c, path):
    img = Image.new("RGBA", (COLS*PIXEL, ROWS*PIXEL), (0,0,0,0))
    px = img.load()
    for y in range(ROWS):
        for x in range(COLS):
            col = c[y][x]
            if col is None: continue
            for yy in range(PIXEL):
                for xx in range(PIXEL):
                    px[x*PIXEL+xx, y*PIXEL+yy] = col + (255,)
    img.save(path)
    print("saved", path)


def draw_ball(c, mouth_deg, draw_eye=True):
    """带粗轮廓、口腔和单眼高光的原创像素吃豆人球，嘴朝左。"""
    cx, cy = COLS/2, ROWS/2
    R = COLS/2 - 1.3
    half = mouth_deg / 2
    mouth_center = 180.0  # 朝左

    # 先铺一圈深色轮廓，让小尺寸下的轮廓更利落。
    for y in range(ROWS):
        for x in range(COLS):
            dx, dy = x - cx, y - cy
            if math.sqrt(dx * dx + dy * dy) <= R + 0.75:
                paint(c, x, y, OUTLINE)

    for y in range(ROWS):
        for x in range(COLS):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > R:
                continue
            ang = math.degrees(math.atan2(dy, dx))
            if ang < 0:
                ang += 360
            delta = abs(ang - mouth_center)
            if delta > 180:
                delta = 360 - delta
            if delta <= half:
                # 红橙口腔让张嘴动作在桌面背景上也清晰可读。
                paint(c, x, y, MOUTH_LIGHT if dy < 0 else MOUTH_DARK)
                continue

            if dy < -R*0.22:
                col = BALL_Y_L
            elif dy > R*0.3:
                col = BALL_Y_D
            else:
                col = BALL_Y
            paint(c, x, y, col)

    # 嘴边缘描边
    for y in range(ROWS):
        for x in range(COLS):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > R - 0.5:
                continue
            ang = math.degrees(math.atan2(dy, dx))
            if ang < 0:
                ang += 360
            delta = abs(ang - mouth_center)
            if delta > 180:
                delta = 360 - delta
            near = abs(delta - half)
            if near < 1.5 and dist > R*0.55:
                paint(c, x, y, OUTLINE)

    # 单眼 (侧面, 一只大黑眼睛, 靠右上方)
    if draw_eye:
        ex, ey = cx + 3.5, cy - 4.5
        ellipse_px(c, ex, ey, 3.4, 3.4, EYE_WHITE)
        ellipse_px(c, ex + 0.9, ey - 0.2, 2.0, 2.0, EYE_DARK)
        ellipse_px(c, ex + 1.45, ey - 1.15, 0.65, 0.65, EYE_SHINE)


def build():
    os.makedirs("assets", exist_ok=True)
    # 张合循环: 8帧 大张→半→近闭→半→...
    mouth_seq = [55, 42, 28, 14, 5, 14, 28, 42]
    for i, deg in enumerate(mouth_seq, 1):
        c = new_canvas()
        draw_ball(c, deg, draw_eye=True)
        render(c, f"assets/charizard_fly{i}.png")

    # 悬停 (轻缓张合)
    hover_seq = [50, 25, 6, 25]
    for i, deg in enumerate(hover_seq, 1):
        c = new_canvas()
        draw_ball(c, deg, draw_eye=True)
        render(c, f"assets/charizard_hover{i}.png")

    # 吃: 闭合粉碎 (大张→完全闭)
    eat_seq = [55, 40, 24, 10, 3, 1]
    for i, deg in enumerate(eat_seq, 1):
        c = new_canvas()
        draw_ball(c, deg, draw_eye=True)
        render(c, f"assets/charizard_eat{i}.png")

    # 左向飞走帧 (同球)
    for i, deg in enumerate(mouth_seq[:4], 1):
        c = new_canvas()
        draw_ball(c, deg, draw_eye=True)
        render(c, f"assets/charizard_left{i}.png")


if __name__ == "__main__":
    build()
