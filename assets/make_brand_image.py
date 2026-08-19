"""
X投稿に添える、楽脳研究所の固定ブランド画像を生成するスクリプト。

著作権的にクリーンな「自作画像」として使うためのもの。他サイトのサムネイル等は
一切使わず、テキストと図形だけで構成している。

実行すると assets/brand_image.png が生成される。
生成は一度だけでよく、日々の投稿では同じファイルを使い回す想定。
"""

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 675

FONT_DIR = "/usr/share/fonts/opentype/noto"
FONT_BLACK = f"{FONT_DIR}/NotoSansCJK-Black.ttc"
FONT_BOLD = f"{FONT_DIR}/NotoSansCJK-Bold.ttc"
FONT_MEDIUM = f"{FONT_DIR}/NotoSansCJK-Medium.ttc"

# 配色（ダークネイビー基調 + アンバーのアクセント。レトロ〜最新機種を横断する
# 雰囲気を狙い、彩度を抑えた大人っぽいトーンにしている）
COLOR_TOP = (18, 20, 38)
COLOR_BOTTOM = (30, 27, 58)
COLOR_ACCENT = (255, 176, 59)
COLOR_ACCENT_DIM = (255, 176, 59, 60)
COLOR_TEXT_MAIN = (245, 245, 250)
COLOR_TEXT_SUB = (255, 176, 59)
COLOR_TEXT_TAGLINE = (170, 172, 195)


def vertical_gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def draw_pixel_motif(draw, x, y, size, color):
    """8bit風のドット絵っぽい飾り（ファミコン〜最新機種のイメージ）。
    シンプルなコントローラーの十字キー風モチーフを描く。
    """
    # 十字キー（レトロゲーム機のイメージ）
    cell = size
    coords = [
        (1, 0), (0, 1), (1, 1), (2, 1), (1, 2),
    ]
    for cx, cy in coords:
        draw.rectangle(
            [x + cx * cell, y + cy * cell, x + (cx + 1) * cell, y + (cy + 1) * cell],
            fill=color,
        )
    # ボタン（丸）2つ
    btn_r = int(cell * 0.9)
    bx = x + cell * 4
    by = y + cell * 1
    draw.ellipse([bx, by, bx + btn_r, by + btn_r], fill=color)
    draw.ellipse(
        [bx + btn_r + cell // 2, by + cell, bx + 2 * btn_r + cell // 2, by + cell + btn_r],
        fill=color,
    )


def main():
    img = vertical_gradient((WIDTH, HEIGHT), COLOR_TOP, COLOR_BOTTOM)
    draw = ImageDraw.Draw(img, "RGBA")

    # 右上に薄いドットグリッド装飾（さりげなく「ゲーム」らしさを添える）
    dot_color = (255, 176, 59, 25)
    step = 28
    for gx in range(WIDTH - 420, WIDTH - 20, step):
        for gy in range(40, 260, step):
            draw.ellipse([gx, gy, gx + 4, gy + 4], fill=dot_color)

    # 左端にアクセントの縦ライン
    draw.rectangle([0, 0, 10, HEIGHT], fill=COLOR_ACCENT)

    # ピクセル風コントローラーモチーフ（左下）
    draw_pixel_motif(draw, 90, HEIGHT - 160, 18, (255, 176, 59, 200))

    # メインタイトル
    font_main = ImageFont.truetype(FONT_BLACK, 108)
    font_sub = ImageFont.truetype(FONT_BOLD, 52)
    font_tag = ImageFont.truetype(FONT_MEDIUM, 30)

    title = "楽脳研究所"
    subtitle = "ゲームニュースまとめ"
    tagline = "ファミコンから最新機種まで"

    draw.text((90, 220), title, font=font_main, fill=COLOR_TEXT_MAIN)
    draw.text((94, 350), subtitle, font=font_sub, fill=COLOR_TEXT_SUB)
    draw.text((94, 430), tagline, font=font_tag, fill=COLOR_TEXT_TAGLINE)

    out_path = "assets/brand_image.png"
    img.save(out_path)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
