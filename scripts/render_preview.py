"""生成不删除任何文件的动画预览 GIF。"""
from pathlib import Path
import random

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUT = ROOT / "preview" / "pacman-delete-preview.gif"
SIZE = (1280, 720)
SPRITE_SIZE = 112
FPS = 20


def sprite(kind, index):
    frame = Image.open(ASSETS / f"charizard_{kind}{index}.png").convert("RGBA")
    return frame.resize((SPRITE_SIZE, SPRITE_SIZE), Image.Resampling.NEAREST)


def main():
    random.seed(9)
    frames = []
    particles = []
    target_x, target_y = 350, 348

    # 右侧飞入、悬停、三轮咬合、左侧飞离；保持与应用的移动方向一致。
    positions = [
        (int(1320 - (1320 - target_x) * i / 60), target_y) for i in range(61)
    ]
    positions += [(target_x, target_y + int((i % 8 - 4) * 0.75)) for i in range(20)]
    positions += [(target_x, target_y) for _ in range(48)]
    positions += [(int(target_x - 700 * i / 45), target_y) for i in range(46)]

    for tick, (x, y) in enumerate(positions):
        canvas = Image.new("RGBA", SIZE, (61, 91, 128, 255))
        draw = ImageDraw.Draw(canvas)
        # 简化的桌面与被吞掉的文件图标。
        draw.rectangle((0, 578, 1280, 720), fill=(50, 76, 108, 255))
        chew_tick = tick - 81
        file_visible_width = 58
        if 0 <= chew_tick < 48:
            file_visible_width = max(2, int(58 * (1 - chew_tick / 47 * 0.96)))
        if tick < 129:
            draw.rounded_rectangle((target_x - 48, target_y + 118, target_x + 45, target_y + 145), 5,
                                  fill=(29, 43, 61, 170))
            draw.rounded_rectangle((target_x - 29, target_y + 14, target_x - 29 + file_visible_width, target_y + 90), 5,
                                  fill=(239, 246, 255, 255), outline=(151, 174, 199, 255), width=3)
            if file_visible_width > 42:
                draw.polygon([(target_x + 10, target_y + 14), (target_x + 29, target_y + 33),
                              (target_x + 10, target_y + 33)], fill=(191, 213, 235, 255))

        if tick < 61 and tick % 2 == 0:
            for index in range(3):
                particles.append([x + random.randint(84, 108), y + random.randint(20, 90), random.choice([
                    (53, 211, 255), (247, 66, 138), (255, 230, 52), (114, 108, 255)
                ]), random.randint(5, 10) if index == 0 else random.randint(3, 7), random.randint(-3, 3)])
        # 每次闭嘴都喷出几颗短命碎片；最后一口粒子更多、更分散。
        if 0 <= chew_tick < 48 and chew_tick % 12 in (6, 7):
            amount = 11 if chew_tick >= 42 else 4
            for _ in range(amount):
                particles.append([target_x + 4, target_y + random.randint(35, 78), random.choice([
                    (239, 246, 255), (53, 211, 255), (247, 66, 138), (255, 230, 52)
                ]), random.randint(2, 6), random.randint(-5, 3)])

        next_particles = []
        for px, py, color, side, rise in particles:
            px += 3 if tick < 81 else random.choice((-2, -1, 1, 2))
            py += rise + 1
            side = max(2, side - 0.04)
            if px < SIZE[0] + 24 and py < SIZE[1]:
                draw.rectangle((px + 2, py + 2, px + side + 2, py + side + 2), fill=(25, 20, 36, 150))
                draw.rectangle((px, py, px + side, py + side), fill=color + (255,))
                next_particles.append([px, py, color, side, rise])
        particles = next_particles

        if 81 <= tick < 129:
            chew_frames = (1, 2, 3, 4, 3, 2, 1, 2, 3, 4, 5, 4)
            canvas.alpha_composite(sprite("eat", chew_frames[chew_tick % len(chew_frames)]), (x, y))
        else:
            canvas.alpha_composite(sprite("fly", tick % 8 + 1), (x, y))
        frames.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE))

    OUT.parent.mkdir(exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=1000 // FPS, loop=0,
                   disposal=2)
    print(OUT)


if __name__ == "__main__":
    main()
