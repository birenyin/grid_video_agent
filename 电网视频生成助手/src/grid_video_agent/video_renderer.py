from __future__ import annotations

import importlib.util
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont

from .models import VideoPlan


def render_preview_bundle(plan: VideoPlan, output_dir: Path, width: int = 1080, height: int = 1920) -> None:
    frames_dir = output_dir / "preview_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_paths: list[Path] = []
    cover_path = output_dir / "cover.png"
    render_cover(plan, cover_path, width, height)

    for index, segment in enumerate(plan.segments, start=1):
        frame_path = frames_dir / f"scene_{index:02d}.png"
        render_scene(plan, segment.scene, segment.narration, segment.visual, frame_path, width, height)
        frame_paths.append(frame_path)

    if frame_paths:
        images = [imageio.imread(path) for path in frame_paths]
        imageio.mimsave(output_dir / "preview.gif", images, duration=2.2, loop=0)
        render_preview_mp4(frame_paths, output_dir / "preview.mp4")


def render_cover(plan: VideoPlan, output_path: Path, width: int, height: int) -> None:
    image = Image.new("RGB", (width, height), "#0E2A47")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, int(height * 0.32)), fill="#163E68")
    draw.ellipse((width - 400, 140, width - 40, 500), fill="#E6B422")
    draw.rectangle((70, 1180, width - 70, 1630), fill="#F5F1E8")

    title_font = load_font(84)
    subtitle_font = load_font(48)
    small_font = load_font(34)

    draw.text((80, 90), "电网视频智能体", font=small_font, fill="#F7F3EC")
    draw_wrapped_text(draw, plan.cover_text, (90, 1260), width - 180, title_font, "#113456", 26)
    draw_wrapped_text(draw, plan.title, (90, 1460), width - 180, subtitle_font, "#113456", 18)
    draw.text((90, 1720), "自动抓取新闻 · 生成分镜 · 输出字幕", font=small_font, fill="#DCE7F2")

    image.save(output_path)


def render_scene(
    plan: VideoPlan,
    scene_number: int,
    narration: str,
    visual: str,
    output_path: Path,
    width: int,
    height: int,
) -> None:
    image = Image.new("RGB", (width, height), "#F4EFE6")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 220), fill="#173B63")
    draw.rectangle((65, 310, width - 65, 1710), fill="#FFFFFF")
    draw.rounded_rectangle((65, 310, width - 65, 1710), radius=34, outline="#D9CFC0", width=4)
    draw.ellipse((820, 80, 1010, 270), fill="#E4B64A")

    badge_font = load_font(40)
    title_font = load_font(54)
    body_font = load_font(38)
    caption_font = load_font(30)

    draw.text((78, 84), f"镜头 {scene_number}", font=badge_font, fill="#F6F3EC")
    draw_wrapped_text(draw, plan.title, (80, 390), width - 160, title_font, "#19334D", 20)
    draw_wrapped_text(draw, narration, (90, 620), width - 180, body_font, "#2A2A2A", 14)

    draw.rectangle((90, 1330, width - 90, 1610), fill="#F7F1E7")
    draw_wrapped_text(draw, f"画面建议：{visual}", (120, 1380), width - 240, caption_font, "#5C4B33", 12)

    draw.text((90, 1780), "生成内容供审核后发布", font=caption_font, fill="#56708B")
    image.save(output_path)


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    origin: tuple[int, int],
    max_width: int,
    font: ImageFont.ImageFont,
    fill: str,
    line_spacing: int,
) -> None:
    x, y = origin
    lines = wrap_text(draw, text, max_width, font)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y = bbox[3] + line_spacing


def wrap_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font: ImageFont.ImageFont) -> list[str]:
    if not text:
        return [""]

    lines: list[str] = []
    current = ""
    for char in text:
        if char == "\n":
            if current:
                lines.append(current)
                current = ""
            continue
        trial = current + char
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ):
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def render_preview_mp4(frame_paths: list[Path], output_path: Path, fps: int = 12, seconds_per_scene: int = 2) -> bool:
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        return False

    with imageio.get_writer(
        output_path,
        fps=fps,
        codec="libx264",
        quality=8,
        macro_block_size=1,
    ) as writer:
        for frame_path in frame_paths:
            frame = imageio.imread(frame_path)
            for _ in range(fps * seconds_per_scene):
                writer.append_data(frame)
    return True
