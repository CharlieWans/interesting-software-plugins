"""
生成应用图标: 吃豆人球风格
  - icon.png  (512x512, 用于 README / 资源)
  - icon.ico  (多尺寸: 16/24/32/48/64/128/256, 用于 exe / 快捷方式 / 右键菜单)
"""
import math
import os
from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

BALL_Y = (255, 216, 0)
BALL_Y_D = (216, 176, 0)
BALL_Y_L = (255, 240, 120)
DARK = (20, 20, 24)
EYE_WHITE = (245, 245, 245)


def draw_ball(size, mouth_deg=55.0):
    """画一个嘴朝左、带单眼的吃豆人球 (RGBA)"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cx = cy = size / 2.0
    R = size / 2.0 - 1
    half = math.radians(mouth_deg / 2.0)

    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.hypot(dx, dy)
            if dist > R:
                continue
            ang = math.atan2(dy, dx)
            # 嘴朝左: 中心角 π
            if abs(ang - math.pi) <= half:
                continue  # 嘴透明
            if dy < -R * 0.22:
                col = BALL_Y_L
            elif dy > R * 0.3:
                col = BALL_Y_D
            else:
                col = BALL_Y
            px[x, y] = col + (255,)

    # 平滑边缘: 抗锯齿 (对边界像素做透明度过渡)
    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.hypot(dx, dy)
            if R - 1.0 < dist <= R:
                r, g, b, a = px[x, y]
                if a == 0:
                    alpha = int(255 * (1 - (dist - (R - 1.0))))
                    # 外圈采样最近的有色像素做边缘色
                    ang = math.atan2(dy, dx)
                    if abs(ang - math.pi) <= half:
                        continue
                    col = BALL_Y if dy >= -R * 0.22 and dy <= R * 0.3 else (BALL_Y_L if dy < -R * 0.22 else BALL_Y_D)
                    px[x, y] = col + (alpha,)

    draw = ImageDraw.Draw(img)
    # 嘴缘描边 (左上/左下)
    for sgn in (-1, 1):
        ax = cx + R * math.cos(math.pi + sgn * half)
        ay = cy + R * math.sin(math.pi + sgn * half)
        draw.line([(cx, cy), (ax, ay)], fill=DARK + (255,), width=max(1, size // 48))

    # 单眼 (靠右上方)
    ex, ey = cx + size * 0.11, cy - size * 0.14
    er = size * 0.115
    draw.ellipse([ex - er, ey - er, ex + er, ey + er], fill=EYE_WHITE + (255,))
    pr = size * 0.065
    draw.ellipse([ex - pr, ey - pr, ex + pr, ey + pr], fill=DARK + (255,))
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    big = draw_ball(512, mouth_deg=55)
    big.save(os.path.join(OUT_DIR, "icon.png"))
    print("saved", os.path.join(OUT_DIR, "icon.png"))

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    imgs = [draw_ball(s, mouth_deg=55).resize((s, s), Image.LANCZOS) for s, _ in sizes]
    big.resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT_DIR, "icon.ico"), format="ICO", sizes=sizes, append_images=imgs[1:]
    )
    print("saved", os.path.join(OUT_DIR, "icon.ico"))


if __name__ == "__main__":
    main()
