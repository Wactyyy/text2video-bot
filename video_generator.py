"""
Video generator: text → TTS audio → video with subtitles
Uses: gTTS (free TTS), MoviePy (free video editing), Pillow (image generation)
"""

import os
import textwrap
import uuid
from gtts import gTTS
from moviepy.editor import (
    AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ── Style presets ──────────────────────────────────────────────────────────────
STYLES = {
    "dark": {
        "bg_color": (15, 15, 20),
        "text_color": (255, 255, 255),
        "accent_color": (99, 179, 237),
        "sub_bg": (30, 30, 40, 200),
    },
    "light": {
        "bg_color": (245, 245, 250),
        "text_color": (20, 20, 30),
        "accent_color": (49, 130, 206),
        "sub_bg": (220, 220, 230, 200),
    },
    "blue": {
        "bg_color": (10, 25, 60),
        "text_color": (255, 255, 255),
        "accent_color": (144, 205, 244),
        "sub_bg": (20, 50, 100, 200),
    },
}

VIDEO_W, VIDEO_H = 720, 1280   # Vertical (9:16) — ideal for Telegram
FPS = 24
FONT_SIZE = 38
SUBTITLE_FONT_SIZE = 34

LANG_MAP = {
    "uk": "uk",
    "en": "en",
    "pl": "pl",
}


def wrap_text(text: str, max_chars: int = 32) -> list[str]:
    return textwrap.wrap(text, width=max_chars)


def get_font(size: int):
    """Try to load a nice font, fall back to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_rounded_rect(draw, xy, radius=20, fill=None):
    """Draw a rounded rectangle on a PIL ImageDraw."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill)


def create_background_frame(style: dict, width=VIDEO_W, height=VIDEO_H) -> Image.Image:
    """Create a styled background with gradient effect."""
    img = Image.new("RGB", (width, height), style["bg_color"])
    draw = ImageDraw.Draw(img)

    # Subtle gradient overlay
    accent = style["accent_color"]
    for i in range(height // 3):
        alpha = int(30 * (1 - i / (height / 3)))
        color = tuple(min(255, c + alpha) for c in style["bg_color"])
        draw.line([(0, i), (width, i)], fill=color)

    # Decorative top bar
    bar_h = 6
    draw.rectangle([(0, 0), (width, bar_h)], fill=style["accent_color"])

    # Corner accent dots
    dot_r = 40
    draw.ellipse(
        [(-dot_r, -dot_r), (dot_r * 2, dot_r * 2)],
        fill=tuple(min(255, c + 40) for c in style["bg_color"])
    )
    draw.ellipse(
        [(width - dot_r * 2, height - dot_r * 2), (width + dot_r, height + dot_r)],
        fill=tuple(min(255, c + 40) for c in style["bg_color"])
    )

    return img


def create_text_frame(
    chunk: str,
    style_name: str,
    chunk_index: int,
    total_chunks: int,
) -> np.ndarray:
    """Create a single video frame (as numpy array) with text."""
    style = STYLES[style_name]
    img = create_background_frame(style)
    draw = ImageDraw.Draw(img, "RGBA")

    font_large = get_font(FONT_SIZE)
    font_small = get_font(22)

    # ── Progress bar ──────────────────────────────────────────────────────────
    bar_y = VIDEO_H - 30
    bar_total_w = VIDEO_W - 80
    bar_filled = int(bar_total_w * (chunk_index + 1) / total_chunks)
    draw.rounded_rectangle(
        [40, bar_y, 40 + bar_total_w, bar_y + 8],
        radius=4,
        fill=(*style["bg_color"][:3], 100),
    )
    if bar_filled > 0:
        draw.rounded_rectangle(
            [40, bar_y, 40 + bar_filled, bar_y + 8],
            radius=4,
            fill=style["accent_color"],
        )

    # ── Main text ─────────────────────────────────────────────────────────────
    lines = wrap_text(chunk, max_chars=28)
    line_h = FONT_SIZE + 12
    total_text_h = len(lines) * line_h
    text_y_start = (VIDEO_H - total_text_h) // 2 - 40

    # Card background
    padding = 40
    card_x1 = 50
    card_x2 = VIDEO_W - 50
    card_y1 = text_y_start - padding
    card_y2 = text_y_start + total_text_h + padding
    draw.rounded_rectangle(
        [card_x1, card_y1, card_x2, card_y2],
        radius=20,
        fill=(*style["sub_bg"][:3], style["sub_bg"][3]),
    )

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_large)
        text_w = bbox[2] - bbox[0]
        x = (VIDEO_W - text_w) // 2
        y = text_y_start + i * line_h

        # Shadow
        draw.text((x + 2, y + 2), line, font=font_large, fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font_large, fill=style["text_color"])

    # ── Watermark ─────────────────────────────────────────────────────────────
    wm = "🎬 Text2Video Bot"
    draw.text((20, VIDEO_H - 55), wm, font=font_small, fill=(*style["accent_color"], 150))

    return np.array(img)


def split_into_chunks(text: str, words_per_chunk: int = 8) -> list[str]:
    """Split text into bite-sized subtitle chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), words_per_chunk):
        chunks.append(" ".join(words[i:i + words_per_chunk]))
    return chunks


def generate_video(
    text: str,
    language: str = "uk",
    style: str = "dark",
    user_id: int = 0,
) -> str:
    """
    Main entry point.
    Returns the path to the generated .mp4 file.
    """
    tmp_dir = "/tmp"
    uid = f"{user_id}_{uuid.uuid4().hex[:8]}"
    audio_path = os.path.join(tmp_dir, f"audio_{uid}.mp3")
    output_path = os.path.join(tmp_dir, f"video_{uid}.mp4")

    # 1. Generate TTS audio
    tts_lang = LANG_MAP.get(language, "uk")
    tts = gTTS(text=text, lang=tts_lang, slow=False)
    tts.save(audio_path)

    # 2. Load audio to get duration
    audio_clip = AudioFileClip(audio_path)
    total_duration = audio_clip.duration

    # 3. Split text into chunks; distribute duration evenly
    chunks = split_into_chunks(text, words_per_chunk=7)
    if not chunks:
        chunks = [text]

    chunk_duration = total_duration / len(chunks)

    # 4. Create image clips for each chunk
    clips = []
    for i, chunk in enumerate(chunks):
        frame = create_text_frame(chunk, style, i, len(chunks))
        img_clip = (
            ImageClip(frame)
            .set_duration(chunk_duration)
            .set_fps(FPS)
        )
        clips.append(img_clip)

    # 5. Concatenate and add audio
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_audio(audio_clip)

    # 6. Write output
    final_video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=os.path.join(tmp_dir, f"temp_audio_{uid}.m4a"),
        remove_temp=True,
        logger=None,
    )

    # Cleanup audio
    audio_clip.close()
    final_video.close()
    if os.path.exists(audio_path):
        os.remove(audio_path)

    return output_path
