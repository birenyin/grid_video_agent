from __future__ import annotations

import math
import uuid
import wave
from pathlib import Path
from struct import pack

import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont

from app.models.content import (
    ContentInput,
    ContentSummary,
    ImageGenerationResult,
    PublishPackage,
    ScriptDraft,
    ShotType,
    StoryboardShot,
    SubtitleCue,
    SubtitleResult,
    TTSResult,
    VideoGenerationResult,
    VoiceSynthesisOptions,
)
from app.providers.base import (
    ImageGenerationProvider,
    LLMProvider,
    PublishingProvider,
    SubtitleProvider,
    TTSProvider,
    VideoGenerationProvider,
)
from app.utils.files import ensure_dir, write_json


class MockLLMProvider(LLMProvider):
    name = "mock_llm"

    def summarize_content(self, content: ContentInput) -> ContentSummary:
        sentences = self._split_sentences(content.raw_text)
        title = content.title or sentences[0][:24]
        summary = " ".join(sentences[:2])[:180]
        bullet_points = sentences[:4]
        key_facts = bullet_points[:3]
        warnings = []
        if not content.source_url:
            warnings.append("待人工确认：当前输入没有来源链接。")
        return ContentSummary(
            title=title,
            summary=summary,
            bullet_points=bullet_points,
            key_facts=key_facts,
            warnings=warnings,
            publish_angle="先说结论，再讲影响，强调调度、保供和系统协同。",
        )

    def generate_script(self, content: ContentInput, summary: ContentSummary) -> ScriptDraft:
        facts = summary.bullet_points or [summary.summary]
        intro_hook = f"先说结论，{summary.title} 这件事不只是行业资讯，它会直接影响我们对电网运行的判断。"
        body = facts[:3]
        body.append("真正值得关注的，不只是新闻表面，而是它背后的负荷、保供、市场和设备运行信号。")
        closing = "如果信息还不完整，请先保留“待人工确认”标记，再决定是否进入发布流程。"
        full_script = "。".join([intro_hook, *body, closing]) + "。"
        return ScriptDraft(
            title=summary.title,
            intro_hook=intro_hook,
            full_script=full_script,
            closing=closing,
            review_notes=list(summary.warnings),
        )

    def _split_sentences(self, text: str) -> list[str]:
        raw = [part.strip(" ，,。") for part in text.replace("\n", " ").split("。")]
        return [part for part in raw if part]


class MockVideoGenerationProvider(VideoGenerationProvider):
    name = "mock_video"

    def text_to_video(self, shot: StoryboardShot, output_dir: Path) -> VideoGenerationResult:
        return self._render_clip(shot, output_dir, include_prompt=True)

    def image_to_video(self, shot: StoryboardShot, image_path: Path, output_dir: Path) -> VideoGenerationResult:
        ensure_dir(output_dir)
        if not image_path.exists():
            return self._render_clip(shot, output_dir, include_prompt=False, base_image_path=image_path)
        return self._render_image_clip(shot, image_path, output_dir, provider_name=self.name, mode="mock_image_to_video")

    def _render_clip(
        self,
        shot: StoryboardShot,
        output_dir: Path,
        include_prompt: bool,
        base_image_path: Path | None = None,
    ) -> VideoGenerationResult:
        ensure_dir(output_dir)
        poster_path = output_dir / f"shot_{shot.shot_id:02d}.png"
        video_path = output_dir / f"shot_{shot.shot_id:02d}.mp4"

        frame = self._build_frame(shot, poster_path, include_prompt, base_image_path)
        writer = imageio.get_writer(video_path, fps=12, codec="libx264", quality=8, macro_block_size=1)
        try:
            for _ in range(shot.shot_duration * 12):
                writer.append_data(frame)
        finally:
            writer.close()

        return VideoGenerationResult(
            provider_name=self.name,
            shot_id=shot.shot_id,
            video_path=str(video_path),
            poster_path=str(poster_path),
            task_id=f"mock-{uuid.uuid4().hex[:10]}",
            raw_response={"mode": "mock", "duration": shot.shot_duration, "aspect_ratio": shot.aspect_ratio},
        )

    def _build_frame(
        self,
        shot: StoryboardShot,
        poster_path: Path,
        include_prompt: bool,
        base_image_path: Path | None,
    ):
        width, height = self._canvas_size(shot.aspect_ratio)
        if base_image_path and base_image_path.exists():
            image = Image.open(base_image_path).convert("RGB").resize((width, height))
        else:
            palette = {
                ShotType.host: "#16324F",
                ShotType.explainer: "#0D4A4A",
                ShotType.broll: "#2A3142",
                ShotType.data: "#3D2C4A",
            }
            image = Image.new("RGB", (width, height), palette.get(shot.shot_type, "#1F2937"))

        draw = ImageDraw.Draw(image)
        header_height = int(height * 0.14)
        outer_margin_x = int(width * 0.06)
        card_top = int(height * 0.18)
        card_bottom = int(height * 0.87)
        subtitle_top = int(height * 0.67)
        subtitle_bottom = int(height * 0.83)
        radius = max(24, int(min(width, height) * 0.03))

        draw.rectangle((0, 0, width, header_height), fill="#101D2C")
        draw.rounded_rectangle(
            (outer_margin_x, card_top, width - outer_margin_x, card_bottom),
            radius=radius,
            fill="#F4EFE7",
        )
        draw.rectangle(
            (outer_margin_x + 20, subtitle_top, width - outer_margin_x - 20, subtitle_bottom),
            fill="#E6EEF6",
        )

        title_font = self._load_font(max(38, int(min(width, height) * 0.05)))
        body_font = self._load_font(max(28, int(min(width, height) * 0.032)))
        small_font = self._load_font(max(22, int(min(width, height) * 0.026)))

        title_origin = (outer_margin_x + 22, max(34, int(header_height * 0.35)))
        narration_origin = (outer_margin_x + 40, card_top + 70)
        prompt_origin = (outer_margin_x + 40, int(height * 0.42))
        subtitle_origin = (outer_margin_x + 40, subtitle_top + 60)
        footer_origin = (outer_margin_x + 20, height - 80)
        text_width = width - 2 * (outer_margin_x + 40)

        draw.text(title_origin, f"镜头 {shot.shot_id}", font=small_font, fill="#F2F4F8")
        self._draw_wrapped(draw, shot.narration_text, narration_origin, text_width, title_font, "#17324D", 18)
        self._draw_wrapped(draw, shot.subtitle_text, subtitle_origin, text_width, body_font, "#23364D", 10)
        if include_prompt:
            self._draw_wrapped(draw, shot.visual_prompt_cn, prompt_origin, text_width, body_font, "#5A4632", 10, max_lines=8)
        draw.text(footer_origin, f"Aspect {shot.aspect_ratio} | static shot", font=small_font, fill="#E5EEF7")

        image.save(poster_path)
        return imageio.imread(poster_path)

    def _render_image_clip(
        self,
        shot: StoryboardShot,
        image_path: Path,
        output_dir: Path,
        provider_name: str,
        mode: str,
    ) -> VideoGenerationResult:
        width, height = self._canvas_size(shot.aspect_ratio)
        poster_path = output_dir / f"shot_{shot.shot_id:02d}.png"
        video_path = output_dir / f"shot_{shot.shot_id:02d}.mp4"

        frame = self._resize_with_letterbox(Image.open(image_path).convert("RGB"), width, height)
        frame.save(poster_path)
        frame_array = imageio.imread(poster_path)

        writer = imageio.get_writer(video_path, fps=12, codec="libx264", quality=8, macro_block_size=1)
        try:
            for _ in range(max(1, shot.shot_duration * 12)):
                writer.append_data(frame_array)
        finally:
            writer.close()

        return VideoGenerationResult(
            provider_name=provider_name,
            shot_id=shot.shot_id,
            video_path=str(video_path),
            poster_path=str(poster_path),
            task_id=f"{provider_name}-{uuid.uuid4().hex[:10]}",
            raw_response={
                "mode": mode,
                "source_image": str(image_path),
                "duration": shot.shot_duration,
                "aspect_ratio": shot.aspect_ratio,
            },
        )

    def _draw_wrapped(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        origin: tuple[int, int],
        max_width: int,
        font: ImageFont.ImageFont,
        fill: str,
        spacing: int,
        max_lines: int | None = None,
    ) -> None:
        x, y = origin
        lines = []
        current = ""
        for char in text:
            if char == "\n":
                lines.append(current)
                current = ""
                continue
            trial = current + char
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
        if max_lines is not None:
            lines = lines[:max_lines]
        for line in lines:
            draw.text((x, y), line, font=font, fill=fill)
            y = draw.textbbox((x, y), line, font=font)[3] + spacing

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        for candidate in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/arial.ttf"):
            path = Path(candidate)
            if path.exists():
                return ImageFont.truetype(str(path), size)
        return ImageFont.load_default()

    def _canvas_size(self, aspect_ratio: str) -> tuple[int, int]:
        if aspect_ratio == "16:9":
            return 1920, 1080
        return 1080, 1920

    def _resize_with_letterbox(self, image: Image.Image, target_w: int, target_h: int) -> Image.Image:
        target_ratio = target_w / target_h
        image_ratio = image.width / image.height
        if abs(image_ratio - target_ratio) < 0.01:
            return image.resize((target_w, target_h))
        if image_ratio > target_ratio:
            resized_width = target_w
            resized_height = max(1, int(target_w / image_ratio))
        else:
            resized_height = target_h
            resized_width = max(1, int(target_h * image_ratio))
        resized = image.resize((resized_width, resized_height))
        canvas = Image.new("RGB", (target_w, target_h), "black")
        offset_x = (target_w - resized_width) // 2
        offset_y = (target_h - resized_height) // 2
        canvas.paste(resized, (offset_x, offset_y))
        return canvas


class StaticImageVideoProvider(VideoGenerationProvider):
    name = "static_image_video"

    def __init__(self) -> None:
        self._delegate = MockVideoGenerationProvider()

    def text_to_video(self, shot: StoryboardShot, output_dir: Path) -> VideoGenerationResult:
        return self._as_static_result(self._delegate._render_clip(shot, output_dir, include_prompt=False))

    def image_to_video(self, shot: StoryboardShot, image_path: Path, output_dir: Path) -> VideoGenerationResult:
        ensure_dir(output_dir)
        if image_path.exists():
            return self._render_from_image(shot, image_path, output_dir)
        # 回退到占位渲染
        return self._as_static_result(
            self._delegate._render_clip(shot, output_dir, include_prompt=False, base_image_path=image_path)
        )

    def _as_static_result(self, result: VideoGenerationResult) -> VideoGenerationResult:
        return result.model_copy(update={"provider_name": self.name})

    def _render_from_image(self, shot: StoryboardShot, image_path: Path, output_dir: Path) -> VideoGenerationResult:
        width, height = self._delegate._canvas_size(shot.aspect_ratio)
        poster_path = output_dir / f"shot_{shot.shot_id:02d}.png"
        video_path = output_dir / f"shot_{shot.shot_id:02d}.mp4"

        frame = self._resize_with_letterbox(Image.open(image_path).convert("RGB"), width, height)
        frame.save(poster_path)

        writer = imageio.get_writer(video_path, fps=12, codec="libx264", quality=8, macro_block_size=1)
        frame_array = imageio.imread(poster_path)
        try:
            for _ in range(max(1, shot.shot_duration * 12)):
                writer.append_data(frame_array)
        finally:
            writer.close()

        return VideoGenerationResult(
            provider_name=self.name,
            shot_id=shot.shot_id,
            video_path=str(video_path),
            poster_path=str(poster_path),
            task_id=f"static-{uuid.uuid4().hex[:10]}",
            raw_response={
                "mode": "static_image",
                "source_image": str(image_path),
                "aspect_ratio": shot.aspect_ratio,
                "duration": shot.shot_duration,
            },
        )

    def _resize_with_letterbox(self, image: Image.Image, target_w: int, target_h: int) -> Image.Image:
        target_ratio = target_w / target_h
        img_ratio = image.width / image.height
        if abs(img_ratio - target_ratio) < 0.01:
            return image.resize((target_w, target_h))
        if img_ratio > target_ratio:
            new_w = target_w
            new_h = max(1, int(target_w / img_ratio))
        else:
            new_h = target_h
            new_w = max(1, int(target_h * img_ratio))
        resized = image.resize((new_w, new_h))
        canvas = Image.new("RGB", (target_w, target_h), "black")
        offset_x = (target_w - new_w) // 2
        offset_y = (target_h - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y))
        return canvas


class MockImageGenerationProvider(ImageGenerationProvider):
    name = "mock_image"

    def __init__(self) -> None:
        self._delegate = MockVideoGenerationProvider()

    def generate(
        self,
        shot: StoryboardShot,
        output_dir: Path,
        reference_image_path: Path,
    ) -> ImageGenerationResult:
        ensure_dir(output_dir)
        image_path = output_dir / f"shot_{shot.shot_id:02d}.png"
        base_image_path = reference_image_path if reference_image_path.exists() else None
        self._delegate._build_frame(shot, image_path, include_prompt=False, base_image_path=base_image_path)
        return ImageGenerationResult(
            provider_name=self.name,
            shot_id=shot.shot_id,
            image_path=str(image_path),
            raw_response={"mode": "mock", "reference_image_path": str(reference_image_path)},
        )


class MockTTSProvider(TTSProvider):
    name = "mock_tts"

    def synthesize(
        self,
        script: ScriptDraft,
        shots: list[StoryboardShot],
        output_dir: Path,
        options: VoiceSynthesisOptions,
    ) -> TTSResult:
        ensure_dir(output_dir)
        audio_path = output_dir / "voice_track.wav"
        sample_rate = 22050
        amplitude = 12000
        total_duration = float(sum(shot.shot_duration for shot in shots))

        with wave.open(str(audio_path), "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frame_count = int(total_duration * sample_rate)
            for index in range(frame_count):
                frequency = 220 + (index // (sample_rate * 2) % 3) * 40
                sample = int(amplitude * math.sin(2 * math.pi * frequency * (index / sample_rate)))
                wav_file.writeframes(pack("<h", sample))

        return TTSResult(
            provider_name=self.name,
            audio_path=str(audio_path),
            duration_seconds=total_duration,
            voice_name=options.voice,
            raw_response={"mode": "mock", "format": options.format},
        )


class LocalSubtitleProvider(SubtitleProvider):
    name = "local_subtitle"

    def generate(self, shots: list[StoryboardShot], output_dir: Path) -> SubtitleResult:
        ensure_dir(output_dir)
        subtitle_path = output_dir / "subtitles.srt"
        cues: list[SubtitleCue] = []
        cursor = 0.0
        lines: list[str] = []
        for shot in shots:
            cue = SubtitleCue(
                index=shot.shot_id,
                start_seconds=cursor,
                end_seconds=cursor + shot.shot_duration,
                text=shot.subtitle_text,
            )
            cues.append(cue)
            lines.extend(
                [
                    str(cue.index),
                    f"{self._format_srt_time(cue.start_seconds)} --> {self._format_srt_time(cue.end_seconds)}",
                    cue.text,
                    "",
                ]
            )
            cursor += shot.shot_duration
        subtitle_path.write_text("\n".join(lines), encoding="utf-8")
        return SubtitleResult(provider_name=self.name, subtitle_path=str(subtitle_path), cues=cues)

    def _format_srt_time(self, value: float) -> str:
        total_ms = int(value * 1000)
        hours = total_ms // 3_600_000
        minutes = (total_ms % 3_600_000) // 60_000
        seconds = (total_ms % 60_000) // 1_000
        millis = total_ms % 1_000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


class MockPublishingProvider(PublishingProvider):
    name = "mock_publisher"

    def export(
        self,
        script: ScriptDraft,
        summary: ContentSummary,
        final_video_path: Path,
        cover_path: Path,
        output_dir: Path,
        publish_mode: str,
    ) -> PublishPackage:
        hashtags = self._build_hashtags(summary)
        payload = {
            "title": script.title[:30],
            "description": f"{summary.summary}\n\n{' '.join(hashtags)}",
            "hashtags": hashtags,
            "video_path": str(final_video_path),
            "cover_path": str(cover_path),
            "publish_mode": publish_mode,
        }
        payload_path = write_json(output_dir / "publish_payload.json", payload)
        return PublishPackage(
            provider_name=self.name,
            title=payload["title"],
            description=payload["description"],
            hashtags=hashtags,
            video_path=str(final_video_path),
            cover_path=str(cover_path),
            publish_mode=publish_mode,
            payload_path=str(payload_path),
            raw_payload=payload,
        )

    def _build_hashtags(self, summary: ContentSummary) -> list[str]:
        tags = ["#电网", "#电力行业"]
        for item in summary.key_facts:
            if "调度" in item and "#调度" not in tags:
                tags.append("#调度")
            if "市场" in item and "#电力市场" not in tags:
                tags.append("#电力市场")
            if "新能源" in item and "#新能源" not in tags:
                tags.append("#新能源")
        return tags[:5]
