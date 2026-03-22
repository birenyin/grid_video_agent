from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover
    imageio_ffmpeg = None

from app.models.content import CompositionResult


class FFmpegComposer:
    def __init__(self) -> None:
        self.ffmpeg_bin = self._resolve_ffmpeg()

    def compose(
        self,
        clip_paths: list[Path],
        audio_path: Path,
        subtitle_path: Path,
        output_dir: Path,
        cover_path: Path,
        aspect_ratio: str = "9:16",
    ) -> CompositionResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        concat_list = output_dir / "clips.txt"
        concat_list.write_text("\n".join([f"file '{clip_path.name}'" for clip_path in clip_paths]), encoding="utf-8")
        canvas_width, canvas_height = self._canvas_size(aspect_ratio)

        for clip_path in clip_paths:
            target = output_dir / clip_path.name
            if clip_path.resolve() != target.resolve():
                target.write_bytes(clip_path.read_bytes())
        if audio_path.resolve() != (output_dir / audio_path.name).resolve():
            (output_dir / audio_path.name).write_bytes(audio_path.read_bytes())
        if subtitle_path.resolve() != (output_dir / subtitle_path.name).resolve():
            (output_dir / subtitle_path.name).write_bytes(subtitle_path.read_bytes())

        merged_path = output_dir / "merged_video.mp4"
        voiced_path = output_dir / "voiced_video.mp4"
        final_path = output_dir / "final_video.mp4"

        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list.name,
                "-vf",
                (
                    f"scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=decrease,"
                    f"pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2:black"
                ),
                "-pix_fmt",
                "yuv420p",
                merged_path.name,
            ],
            cwd=output_dir,
        )
        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-i",
                merged_path.name,
                "-i",
                audio_path.name,
                "-shortest",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                voiced_path.name,
            ],
            cwd=output_dir,
        )

        used_subtitle_burn = True
        try:
            self._run(
                [
                    self.ffmpeg_bin,
                    "-y",
                    "-i",
                    voiced_path.name,
                    "-vf",
                    f"subtitles={subtitle_path.name}",
                    "-c:a",
                    "copy",
                    final_path.name,
                ],
                cwd=output_dir,
            )
        except subprocess.CalledProcessError:
            used_subtitle_burn = False
            shutil.copyfile(voiced_path, final_path)

        return CompositionResult(
            video_path=str(final_path),
            cover_path=str(cover_path),
            clip_paths=[str(path) for path in clip_paths],
            used_subtitle_burn=used_subtitle_burn,
        )

    def fit_audio_to_duration(self, audio_path: Path, target_duration_seconds: float) -> Path:
        if target_duration_seconds <= 0:
            return audio_path
        current_duration = self._probe_media_duration(audio_path)
        if current_duration <= 0 or abs(current_duration - target_duration_seconds) < 0.5:
            return audio_path

        adjusted_path = audio_path.with_name(f"{audio_path.stem}_aligned{audio_path.suffix}")
        atempo = current_duration / target_duration_seconds
        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-i",
                audio_path.name,
                "-filter:a",
                self._build_atempo_filter(atempo),
                "-vn",
                adjusted_path.name,
            ],
            cwd=audio_path.parent,
        )
        return adjusted_path

    def _resolve_ffmpeg(self) -> str:
        if imageio_ffmpeg is not None:
            return imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        raise RuntimeError("ffmpeg is not available. Install imageio-ffmpeg or ffmpeg on PATH.")

    def _run(self, command: list[str], cwd: Path) -> None:
        subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _canvas_size(self, aspect_ratio: str) -> tuple[int, int]:
        if aspect_ratio == "16:9":
            return 1920, 1080
        return 1080, 1920

    def _build_atempo_filter(self, speed_factor: float) -> str:
        if speed_factor <= 0:
            return "atempo=1.0"
        factors: list[float] = []
        remaining = speed_factor
        while remaining > 2.0:
            factors.append(2.0)
            remaining /= 2.0
        while remaining < 0.5:
            factors.append(0.5)
            remaining /= 0.5
        factors.append(remaining)
        return ",".join(f"atempo={factor:.6f}" for factor in factors)

    def _probe_media_duration(self, media_path: Path) -> float:
        command = [
            self.ffmpeg_bin,
            "-i",
            media_path.name,
            "-f",
            "null",
            "-",
        ]
        completed = subprocess.run(
            command,
            cwd=media_path.parent,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = completed.stderr or ""
        duration_marker = "Duration: "
        start = output.find(duration_marker)
        if start == -1:
            return 0.0
        start += len(duration_marker)
        end = output.find(",", start)
        if end == -1:
            return 0.0
        timestamp = output[start:end].strip()
        hours, minutes, seconds = timestamp.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
