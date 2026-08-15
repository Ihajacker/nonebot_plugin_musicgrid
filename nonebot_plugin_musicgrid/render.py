import io
import os

from PIL import Image, ImageDraw, ImageFont

IMG_SIZE = 200
TEXT_WIDTH = 450
TEXT_MAX_WIDTH = 420
BG_DARK = "#151515"
BG_LIGHT = "#ffffff"


def _truncate_to_width(text, font, max_width):
    # 超宽截断并加省略号
    if font.getlength(text) <= max_width:
        return text
    while font.getlength(text + "…") > max_width and text:
        text = text[:-1]
    return text + "…"


def _cover_resize(image, width, height):
    # 等比缩放并居中裁切到目标尺寸
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * ratio), round(image.height * ratio)), Image.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def render_grid(images, tracks, cols, rows, include_text, font_path, text_key="name",
                background=None, background_opacity=0.5):
    # 封面网格拼图，可选右侧文字列表与自定义背景
    canvas_width = cols * IMG_SIZE + (TEXT_WIDTH if include_text else 0)
    canvas_height = rows * IMG_SIZE
    bg_color = BG_DARK if include_text else BG_LIGHT
    canvas = Image.new("RGB", (canvas_width, canvas_height), bg_color)

    for i, img in enumerate(images[: cols * rows]):
        col, row = i % cols, i // cols
        canvas.paste(img, (col * IMG_SIZE, row * IMG_SIZE))

    lines = [f"{i + 1}. {t['artist']} - {t.get(text_key, '')}" for i, t in enumerate(tracks[: cols * rows])]
    if not include_text or not lines:
        return _to_jpeg(canvas)

    if background is not None:
        # 背景图铺满文字区，按不透明度叠加深色
        bg = _cover_resize(background.convert("RGB"), TEXT_WIDTH, canvas_height)
        if background_opacity < 1:
            overlay = Image.new("RGBA", bg.size, (21, 21, 21, int(255 * (1 - background_opacity))))
            bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        canvas.paste(bg, (cols * IMG_SIZE, 0))

    if not os.path.exists(font_path):
        raise FileNotFoundError(f"字体文件不存在: {font_path}")

    # 字号仅受行高约束，上限18；超宽行绘制时单独截断
    max_by_height = int((canvas_height - 80) / len(lines)) - 4
    font_size = max(10, min(18, max_by_height))
    font = ImageFont.truetype(font_path, font_size)

    draw = ImageDraw.Draw(canvas)
    padding_left = cols * IMG_SIZE + 30
    padding_top = 40
    line_height = (canvas_height - padding_top * 2) / len(lines)
    for index, line in enumerate(lines):
        draw.text(
            (padding_left, padding_top + index * line_height + font_size),
            _truncate_to_width(line, font, TEXT_MAX_WIDTH),
            fill="#ffffff",
            font=font,
        )

    return _to_jpeg(canvas)


def _to_jpeg(image):
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return buf.getvalue()
