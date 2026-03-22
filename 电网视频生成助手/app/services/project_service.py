from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Callable, TypeVar

from app.core.config import Settings, get_settings
from app.core.database import Database
from app.models.content import (
    ContentInput,
    ContentSummary,
    ContentMode,
    ImageGenerationResult,
    PublishPackage,
    ScriptDraft,
    StoryboardShot,
    SubtitleResult,
    TTSResult,
    VideoGenerationResult,
    VoiceSynthesisOptions,
)
from app.models.project import (
    CreateProjectFromFeedRequest,
    CreateProjectFromScriptRequest,
    CreateProjectFromTextRequest,
    CreateProjectFromUrlRequest,
    ProjectArtifacts,
    ProjectRecord,
    ProjectStatus,
    RenderProjectRequest,
    WorkflowGenerateImagesRequest,
    WorkflowScriptUpdateRequest,
)
from app.providers.base import (
    ImageGenerationProvider,
    LLMProvider,
    ProviderError,
    PublishingProvider,
    SubtitleProvider,
    TTSProvider,
    VideoGenerationProvider,
)
from app.providers.douyin_publisher import DouyinPublisher
from app.providers.mock import (
    LocalSubtitleProvider,
    MockImageGenerationProvider,
    MockLLMProvider,
    MockPublishingProvider,
    MockTTSProvider,
    MockVideoGenerationProvider,
    StaticImageVideoProvider,
)
from app.providers.openai_compatible_llm import OpenAICompatibleLLMProvider
from app.providers.volcengine_image import VolcengineImageProvider
from app.providers.volcengine_tts import VolcengineTTSProvider
from app.providers.volcengine_video import VolcengineVideoProvider
from app.services.composer_service import FFmpegComposer
from app.services.ingestion_service import IngestionService
from app.services.storyboard_prompt_engine import StoryboardPromptEngine
from app.utils.files import ensure_dir, write_json
from src.grid_video_agent.config import AgentConfig
from src.grid_video_agent.pipeline import run_pipeline
from src.grid_video_agent.video_renderer import render_preview_bundle


T = TypeVar("T")


class ProjectOrchestrator:
    def __init__(self, settings: Settings | None = None, database: Database | None = None) -> None:
        self.settings = settings or get_settings()
        self.database = database or Database(self.settings.database_path)
        self.ingestion_service = IngestionService()
        self.storyboard_engine = StoryboardPromptEngine()
        self.composer = FFmpegComposer()

    def create_from_text(self, request: CreateProjectFromTextRequest) -> ProjectRecord:
        project_id, working_dir = self._create_project_workspace()
        content = self.ingestion_service.ingest_content(
            ContentInput(
                title=request.title,
                raw_text=request.content_text,
                source_url=request.source_url,
                mode=ContentMode(request.mode),
                target_duration_seconds=request.target_duration_seconds,
                aspect_ratio=request.aspect_ratio,
            )
        )

        summary, script = self._resolve_provider_chain(
            project_id=project_id,
            action_name="summarize_and_script",
            provider_names=self.settings.llm_provider_priority,
            builder=self._build_llm_provider,
            request_payload=content.model_dump(),
            handler=lambda provider: self._run_llm_chain(provider, content),
        )
        storyboard = self.storyboard_engine.split_storyboard(
            title=summary.title,
            content_summary=summary.summary,
            full_script=script.full_script,
            mode=content.mode,
            target_duration_seconds=content.target_duration_seconds,
            aspect_ratio=content.aspect_ratio,
        )

        write_json(working_dir / "summary.json", summary.model_dump())
        write_json(working_dir / "script.json", script.model_dump())
        write_json(working_dir / "storyboard.json", {"shots": [shot.model_dump() for shot in storyboard]})

        project = ProjectRecord(
            project_id=project_id,
            status=ProjectStatus.draft,
            content_input=content,
            summary=summary,
            script=script,
            storyboard=storyboard,
            warnings=list(summary.warnings) + list(script.review_notes),
            artifacts=ProjectArtifacts(
                working_dir=str(working_dir),
                summary_path=str(working_dir / "summary.json"),
                script_path=str(working_dir / "script.json"),
                storyboard_path=str(working_dir / "storyboard.json"),
            ),
        )
        self.database.save_project(project)
        return project

    def create_from_script(self, request: CreateProjectFromScriptRequest) -> ProjectRecord:
        project_id, working_dir = self._create_project_workspace()
        content = self.ingestion_service.ingest_content(
            ContentInput(
                title=request.title,
                raw_text=request.full_script,
                mode=ContentMode(request.mode),
                target_duration_seconds=request.target_duration_seconds,
                source_type="manual_script",
                aspect_ratio=request.aspect_ratio,
            )
        )
        summary = self._build_script_summary(request.title, request.full_script)
        script = self._build_script_draft(request.title, request.full_script)
        storyboard = self.storyboard_engine.split_storyboard(
            title=summary.title,
            content_summary=summary.summary,
            full_script=script.full_script,
            mode=content.mode,
            target_duration_seconds=content.target_duration_seconds,
            aspect_ratio=content.aspect_ratio,
        )

        write_json(working_dir / "summary.json", summary.model_dump())
        write_json(working_dir / "script.json", script.model_dump())
        write_json(working_dir / "storyboard.json", {"shots": [shot.model_dump() for shot in storyboard]})

        project = ProjectRecord(
            project_id=project_id,
            status=ProjectStatus.draft,
            content_input=content,
            summary=summary,
            script=script,
            storyboard=storyboard,
            warnings=[],
            artifacts=ProjectArtifacts(
                working_dir=str(working_dir),
                summary_path=str(working_dir / "summary.json"),
                script_path=str(working_dir / "script.json"),
                storyboard_path=str(working_dir / "storyboard.json"),
            ),
        )
        self.database.save_project(project)
        return project

    def create_from_url(self, request: CreateProjectFromUrlRequest) -> ProjectRecord:
        fetched_title, fetched_text = self.ingestion_service.fetch_url_content(request.source_url)
        return self.create_from_text(
            CreateProjectFromTextRequest(
                title=request.title or fetched_title,
                content_text=fetched_text,
                source_url=request.source_url,
                mode=request.mode,
                target_duration_seconds=request.target_duration_seconds,
                aspect_ratio=request.aspect_ratio,
            )
        )

    def create_from_rpa_feed(self, request: CreateProjectFromFeedRequest) -> ProjectRecord:
        feed_path = Path(request.feed_path)
        if not feed_path.exists():
            raise ValueError(f"RPA feed not found: {request.feed_path}")

        project_id, working_dir = self._create_project_workspace()
        newsroom_dir = ensure_dir(working_dir / "newsroom")
        config = AgentConfig(
            duration_seconds=request.target_duration_seconds,
            model_mode=request.plan_mode,
        )
        plan, _ = run_pipeline(feed_path, newsroom_dir, config)

        if request.render_preview_bundle:
            preview_width, preview_height = self._preview_canvas_size(request.aspect_ratio)
            render_preview_bundle(
                plan,
                newsroom_dir,
                width=preview_width,
                height=preview_height,
            )

        full_script = self._compose_feed_script(plan.intro_hook, [segment.narration for segment in plan.segments], plan.takeaway)
        content = self.ingestion_service.ingest_content(
            ContentInput(
                title=request.title or plan.title,
                raw_text=full_script,
                source_type="rpa_feed",
                mode=ContentMode(request.mode),
                target_duration_seconds=request.target_duration_seconds,
                aspect_ratio=request.aspect_ratio,
            )
        )
        summary = ContentSummary(
            title=request.title or plan.title,
            summary=plan.takeaway or plan.intro_hook,
            bullet_points=[segment.narration for segment in plan.segments[:4]],
            key_facts=[str(item.get("title", "")) for item in plan.selected_news[:3]],
            warnings=list(plan.warnings),
            publish_angle="rpa_feed_pipeline",
        )
        script = ScriptDraft(
            title=summary.title,
            intro_hook=plan.intro_hook,
            full_script=full_script,
            closing=plan.takeaway or (plan.segments[-1].narration if plan.segments else summary.title),
            review_notes=list(plan.warnings),
        )
        storyboard = self.storyboard_engine.split_storyboard(
            title=summary.title,
            content_summary=summary.summary,
            full_script=script.full_script,
            mode=content.mode,
            target_duration_seconds=content.target_duration_seconds,
            aspect_ratio=content.aspect_ratio,
        )

        write_json(working_dir / "summary.json", summary.model_dump())
        write_json(working_dir / "script.json", script.model_dump())
        write_json(working_dir / "storyboard.json", {"shots": [shot.model_dump() for shot in storyboard]})

        project = ProjectRecord(
            project_id=project_id,
            status=ProjectStatus.draft,
            content_input=content,
            summary=summary,
            script=script,
            storyboard=storyboard,
            warnings=list(plan.warnings),
            artifacts=ProjectArtifacts(
                working_dir=str(working_dir),
                summary_path=str(working_dir / "summary.json"),
                script_path=str(working_dir / "script.json"),
                storyboard_path=str(working_dir / "storyboard.json"),
                news_plan_path=str(newsroom_dir / "video_plan.json"),
                news_report_path=str(newsroom_dir / "run_report.json"),
                selected_sources_path=str(newsroom_dir / "selected_sources.md"),
                preview_cover_path=str(newsroom_dir / "cover.png") if (newsroom_dir / "cover.png").exists() else "",
                preview_gif_path=str(newsroom_dir / "preview.gif") if (newsroom_dir / "preview.gif").exists() else "",
                preview_video_path=str(newsroom_dir / "preview.mp4") if (newsroom_dir / "preview.mp4").exists() else "",
            ),
        )
        self.database.save_project(project)
        return project

    def list_projects(self, limit: int = 50) -> list[ProjectRecord]:
        return self.database.list_projects(limit)

    def get_project_or_raise(self, project_id: str) -> ProjectRecord:
        project = self.database.get_project(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")
        return project

    def update_workflow_script(self, project_id: str, request: WorkflowScriptUpdateRequest) -> ProjectRecord:
        project = self.get_project_or_raise(project_id)

        title = request.title.strip()
        full_script = request.full_script.strip()
        mode = ContentMode(request.mode)
        summary = self._build_script_summary(title, full_script)
        if request.summary:
            summary = summary.model_copy(update={"summary": request.summary.strip()})
        script = self._build_script_draft(title, full_script)
        storyboard = (
            self.storyboard_engine.split_storyboard(
                title=title,
                content_summary=summary.summary,
                full_script=full_script,
                mode=mode,
                target_duration_seconds=request.target_duration_seconds,
                aspect_ratio=request.aspect_ratio,
            )
            if request.regenerate_storyboard or not request.storyboard
            else [
                shot if shot.aspect_ratio == request.aspect_ratio else shot.model_copy(update={"aspect_ratio": request.aspect_ratio})
                for shot in request.storyboard
            ]
        )

        project.content_input = project.content_input.model_copy(
            update={
                "title": title,
                "raw_text": full_script,
                "mode": mode,
                "target_duration_seconds": request.target_duration_seconds,
                "aspect_ratio": request.aspect_ratio,
            }
        )
        project.summary = summary
        project.script = script
        project.storyboard = storyboard
        project.status = ProjectStatus.draft
        project.warnings = list(dict.fromkeys(list(summary.warnings) + list(script.review_notes)))
        self._reset_render_outputs(project, clear_images=True)
        self.database.clear_provider_attempts(project.project_id)
        self._write_project_documents(project)
        self.database.save_project(project)
        return project

    def generate_workflow_images(self, project_id: str, request: WorkflowGenerateImagesRequest) -> ProjectRecord:
        project = self.get_project_or_raise(project_id)
        if not project.storyboard:
            raise ValueError("Project has no storyboard to generate images from.")

        aspect_ratio = request.aspect_ratio or project.content_input.aspect_ratio
        storyboard = [
            shot if shot.aspect_ratio == aspect_ratio else shot.model_copy(update={"aspect_ratio": aspect_ratio})
            for shot in project.storyboard
        ]
        working_dir = ensure_dir(Path(project.artifacts.working_dir))
        images_dir = ensure_dir(working_dir / "images")
        selected_shot_ids = set(request.shot_ids) if request.shot_ids else {shot.shot_id for shot in storyboard}
        existing_images = self._collect_existing_shot_images(project, storyboard)
        shot_reference_paths = dict(project.artifacts.shot_reference_paths)
        resolved_default_reference = self._resolve_reference_image_path(request.reference_image_path)
        if resolved_default_reference:
            project.artifacts.resolved_reference_image_path = resolved_default_reference

        for shot_key, raw_value in request.shot_reference_overrides.items():
            cleaned = raw_value.strip()
            if not cleaned:
                shot_reference_paths.pop(str(shot_key), None)
                continue
            shot_reference_paths[str(shot_key)] = self._require_existing_local_path(cleaned)

        generated_images: list[ImageGenerationResult] = []
        preview_fallback_used = False
        placeholder_fallback_used = False
        for shot in storyboard:
            current_image = existing_images.get(shot.shot_id)
            if shot.shot_id not in selected_shot_ids:
                if current_image is not None:
                    generated_images.append(current_image)
                continue

            shot_reference = shot_reference_paths.get(str(shot.shot_id), resolved_default_reference or "")
            if shot_reference:
                generated_images.append(
                    self._generate_reference_image_for_shot(
                        project_id=project.project_id,
                        shot=shot,
                        images_dir=images_dir,
                        reference_image_path=shot_reference,
                    )
                )
                continue

            preview_result = self._load_newsroom_preview_images(project, [shot])
            if preview_result:
                preview_fallback_used = True
                self.database.log_provider_attempt(
                    project_id=project.project_id,
                    provider_name="newsroom_preview",
                    action_name=f"generate_reference_image_{shot.shot_id}",
                    attempt_no=1,
                    status="success",
                    request_payload={"shot_id": shot.shot_id, "aspect_ratio": shot.aspect_ratio},
                    response_payload=preview_result[0].model_dump(),
                )
                generated_images.append(preview_result[0])
                continue

            placeholder_fallback_used = True
            generated_images.append(
                self._generate_placeholder_image_for_shot(
                    project_id=project.project_id,
                    shot=shot,
                    images_dir=images_dir,
                )
            )

        project.storyboard = storyboard
        project.status = ProjectStatus.draft
        project.artifacts.shot_reference_paths = shot_reference_paths
        project.artifacts.shot_images = sorted(generated_images, key=lambda item: item.shot_id)
        self._reset_render_outputs(project, clear_images=False)
        if preview_fallback_used:
            self._append_project_warning(project, "部分镜头未提供参考图，已回退为 newsroom 预览帧。")
        if placeholder_fallback_used:
            self._append_project_warning(project, "部分镜头缺少参考图和预览帧，已回退为占位图片。")
        self.database.save_project(project)
        return project

    def render_workflow_project(self, project_id: str, request: RenderProjectRequest | None = None) -> ProjectRecord:
        project = self.get_project_or_raise(project_id)
        if project.summary is None or project.script is None or not project.storyboard:
            raise ValueError("Project is incomplete and cannot be rendered.")

        request = request or RenderProjectRequest()
        working_dir = ensure_dir(Path(project.artifacts.working_dir))
        shots_dir = ensure_dir(working_dir / "shots")
        images_dir = ensure_dir(working_dir / "images")
        aspect_ratio = request.aspect_ratio or project.content_input.aspect_ratio
        resolved_reference_image_path = self._resolve_reference_image_path(request.reference_image_path)
        storyboard = [
            shot if shot.aspect_ratio == aspect_ratio else shot.model_copy(update={"aspect_ratio": aspect_ratio})
            for shot in project.storyboard
        ]
        project.status = ProjectStatus.rendering
        project.artifacts.last_render_mode = request.render_mode
        project.artifacts.resolved_reference_image_path = resolved_reference_image_path or project.artifacts.resolved_reference_image_path
        self.database.save_project(project)

        try:
            voice = self._generate_voice(project_id, project.script, storyboard, working_dir, request)
            storyboard = self._align_storyboard_to_voice(storyboard, voice.duration_seconds)
            voice = self._align_voice_to_storyboard(voice, storyboard)
            write_json(working_dir / "storyboard.json", {"shots": [shot.model_dump() for shot in storyboard]})
            subtitles = self._generate_subtitles(project_id, storyboard, working_dir)
            shot_images = self._prepare_shot_images_for_render(
                project=project,
                project_id=project_id,
                storyboard=storyboard,
                images_dir=images_dir,
                render_mode=request.render_mode,
                reference_image_path=resolved_reference_image_path,
                reuse_existing_shot_images=request.reuse_existing_shot_images,
            )
            shot_videos = self._generate_shot_videos(
                project_id=project_id,
                shots=storyboard,
                shots_dir=shots_dir,
                render_mode=request.render_mode,
                shot_images=shot_images,
            )
            shot_images = self._attach_generated_videos_to_images(shot_images, shot_videos)
            if any(item.provider_name in {"mock_video", "static_image_video"} or item.used_fallback for item in shot_videos):
                self._append_project_warning(project, "部分镜头未走通真实视频接口，已自动回退为静态图视频。")
            composition = self.composer.compose(
                clip_paths=[Path(item.video_path) for item in shot_videos],
                audio_path=Path(voice.audio_path),
                subtitle_path=Path(subtitles.subtitle_path),
                output_dir=working_dir,
                cover_path=Path(shot_videos[0].poster_path),
                aspect_ratio=aspect_ratio,
            )
            publish_package = self._export_publish_package(
                project_id=project_id,
                script=project.script,
                summary=project.summary,
                final_video_path=Path(composition.video_path),
                cover_path=Path(composition.cover_path),
                working_dir=working_dir,
                publish_mode=request.publish_mode,
            )
        except Exception as exc:  # noqa: BLE001
            project.status = ProjectStatus.failed
            self._append_project_warning(project, f"工作流渲染失败：{exc}")
            self.database.save_project(project)
            raise

        project.status = ProjectStatus.rendered
        project.artifacts.voice = voice
        project.artifacts.subtitles = subtitles
        project.artifacts.shot_images = shot_images
        project.artifacts.shot_videos = shot_videos
        project.artifacts.composition = composition
        project.artifacts.publish_package = publish_package
        project.storyboard = storyboard
        self.database.save_project(project)
        return project

    def render_project(self, project_id: str, request: RenderProjectRequest | None = None) -> ProjectRecord:
        project = self.database.get_project(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")
        if project.summary is None or project.script is None or not project.storyboard:
            raise ValueError("Project is incomplete and cannot be rendered.")

        request = request or RenderProjectRequest()
        working_dir = ensure_dir(Path(project.artifacts.working_dir))
        shots_dir = ensure_dir(working_dir / "shots")
        images_dir = ensure_dir(working_dir / "images")
        aspect_ratio = request.aspect_ratio or project.content_input.aspect_ratio
        resolved_reference_image_path = self._resolve_reference_image_path(request.reference_image_path)
        storyboard = [
            shot if shot.aspect_ratio == aspect_ratio else shot.model_copy(update={"aspect_ratio": aspect_ratio})
            for shot in project.storyboard
        ]
        project.status = ProjectStatus.rendering
        project.artifacts.last_render_mode = request.render_mode
        project.artifacts.resolved_reference_image_path = resolved_reference_image_path or ""
        self.database.save_project(project)

        try:
            voice = self._generate_voice(project_id, project.script, storyboard, working_dir, request)
            storyboard = self._align_storyboard_to_voice(storyboard, voice.duration_seconds)
            voice = self._align_voice_to_storyboard(voice, storyboard)
            write_json(working_dir / "storyboard.json", {"shots": [shot.model_dump() for shot in storyboard]})
            subtitles = self._generate_subtitles(project_id, storyboard, working_dir)
            shot_images = self._generate_shot_images(
                project_id=project_id,
                shots=storyboard,
                images_dir=images_dir,
                render_mode=request.render_mode,
                reference_image_path=resolved_reference_image_path,
            )
            if not shot_images:
                shot_images = self._load_newsroom_preview_images(project, storyboard)
                if shot_images:
                    self._append_project_warning(project, "未生成镜头图片，已回退为 newsroom 预览帧。")

            shot_videos = self._generate_shot_videos(
                project_id=project_id,
                shots=storyboard,
                shots_dir=shots_dir,
                render_mode=request.render_mode,
                shot_images=shot_images,
            )
            shot_images = self._attach_generated_videos_to_images(shot_images, shot_videos)
            if any(item.provider_name in {"mock_video", "static_image_video"} or item.used_fallback for item in shot_videos):
                self._append_project_warning(project, "部分镜头未走通真实视频接口，已自动回退为静态图视频。")
            composition = self.composer.compose(
                clip_paths=[Path(item.video_path) for item in shot_videos],
                audio_path=Path(voice.audio_path),
                subtitle_path=Path(subtitles.subtitle_path),
                output_dir=working_dir,
                cover_path=Path(shot_videos[0].poster_path),
                aspect_ratio=aspect_ratio,
            )
            publish_package = self._export_publish_package(
                project_id=project_id,
                script=project.script,
                summary=project.summary,
                final_video_path=Path(composition.video_path),
                cover_path=Path(composition.cover_path),
                working_dir=working_dir,
                publish_mode=request.publish_mode,
            )
        except Exception as exc:  # noqa: BLE001
            project.status = ProjectStatus.failed
            self._append_project_warning(project, f"渲染失败：{exc}")
            self.database.save_project(project)
            raise

        project.status = ProjectStatus.rendered
        project.artifacts.voice = voice
        project.artifacts.subtitles = subtitles
        project.artifacts.shot_images = shot_images
        project.artifacts.shot_videos = shot_videos
        project.artifacts.composition = composition
        project.artifacts.publish_package = publish_package
        project.storyboard = storyboard
        self.database.save_project(project)
        return project

    def _run_llm_chain(self, provider: LLMProvider, content: ContentInput):
        summary = provider.summarize_content(content)
        script = provider.generate_script(content, summary)
        return summary, script

    def _generate_voice(
        self,
        project_id: str,
        script: ScriptDraft,
        shots: list[StoryboardShot],
        working_dir: Path,
        request: RenderProjectRequest,
    ) -> TTSResult:
        options = VoiceSynthesisOptions(voice=request.preferred_voice)
        output_dir = ensure_dir(working_dir / "audio")
        return self._resolve_provider_chain(
            project_id=project_id,
            action_name="generate_voice",
            provider_names=self.settings.tts_provider_priority,
            builder=self._build_tts_provider,
            request_payload={"voice": options.voice, "shot_count": len(shots)},
            handler=lambda provider: self._run_with_retries(
                project_id,
                provider.name,
                "generate_voice",
                max_attempts=2 if provider.name == "volcengine_tts" else 1,
                request_payload={"voice": options.voice},
                func=lambda: provider.synthesize(script, shots, output_dir, options),
            ),
        )

    def _generate_subtitles(self, project_id: str, shots: list[StoryboardShot], working_dir: Path) -> SubtitleResult:
        output_dir = ensure_dir(working_dir / "subtitles")
        provider = self._build_subtitle_provider(self.settings.subtitle_provider_priority[0])
        return self._run_with_retries(
            project_id,
            provider.name,
            "generate_subtitles",
            max_attempts=1,
            request_payload={"shot_count": len(shots)},
            func=lambda: provider.generate(shots, output_dir),
        )

    def _align_voice_to_storyboard(self, voice: TTSResult, shots: list[StoryboardShot]) -> TTSResult:
        target_duration = float(sum(shot.shot_duration for shot in shots))
        aligned_audio_path = self.composer.fit_audio_to_duration(Path(voice.audio_path), target_duration)
        if aligned_audio_path == Path(voice.audio_path):
            return voice
        raw_response = dict(voice.raw_response)
        raw_response["aligned_from_duration_seconds"] = round(voice.duration_seconds, 3)
        raw_response["aligned_to_duration_seconds"] = round(target_duration, 3)
        return voice.model_copy(
            update={
                "audio_path": str(aligned_audio_path),
                "duration_seconds": target_duration,
                "raw_response": raw_response,
            }
        )

    def _align_storyboard_to_voice(self, shots: list[StoryboardShot], voice_duration_seconds: float) -> list[StoryboardShot]:
        if not shots:
            return shots
        target_duration = max(15, round(voice_duration_seconds))
        durations = self.storyboard_engine._allocate_durations(len(shots), target_duration)
        if durations == [shot.shot_duration for shot in shots]:
            return shots
        return [
            shot.model_copy(update={"shot_duration": duration})
            for shot, duration in zip(shots, durations)
        ]

    def _generate_shot_videos_with_mode(
        self,
        project_id: str,
        shots: list[StoryboardShot],
        shots_dir: Path,
        render_mode: str,
        shot_images: list[ImageGenerationResult] | None = None,
    ) -> list[VideoGenerationResult]:
        results: list[VideoGenerationResult] = []
        shot_image_map = {item.shot_id: item for item in shot_images or []}
        for shot in shots:
            shot_dir = ensure_dir(shots_dir / f"shot_{shot.shot_id:02d}")
            shot_image = shot_image_map.get(shot.shot_id)
            if render_mode == "image_audio":
                result = self._render_static_image_shot(project_id, shot, shot_dir, shot_image)
            elif shot_image is not None and Path(shot_image.image_path).exists():
                result = self._render_video_shot_from_image(project_id, shot, shot_dir, shot_image)
            else:
                result = self._render_video_shot_from_text(project_id, shot, shot_dir)
            results.append(result)
        return results

    def _generate_shot_videos(
        self,
        project_id: str,
        shots: list[StoryboardShot],
        shots_dir: Path,
        render_mode: str = "video_audio",
        shot_images: list[ImageGenerationResult] | None = None,
    ) -> list[VideoGenerationResult]:
        return self._generate_shot_videos_with_mode(project_id, shots, shots_dir, render_mode, shot_images)

    def _generate_shot_images(
        self,
        project_id: str,
        shots: list[StoryboardShot],
        images_dir: Path,
        render_mode: str,
        reference_image_path: str | None,
    ) -> list[ImageGenerationResult]:
        if render_mode not in {"image_audio", "video_audio"}:
            return []
        if not reference_image_path:
            return []

        reference_path = Path(reference_image_path)
        if not reference_path.exists():
            raise ValueError(f"Reference image not found: {reference_image_path}")

        generated_images: list[ImageGenerationResult] = []
        for shot in shots:
            image_result = self._generate_reference_image_for_shot(
                project_id=project_id,
                shot=shot,
                images_dir=images_dir,
                reference_image_path=str(reference_path),
            )
            generated_images.append(image_result)
        return generated_images

    def _generate_reference_image_for_shot(
        self,
        project_id: str,
        shot: StoryboardShot,
        images_dir: Path,
        reference_image_path: str,
    ) -> ImageGenerationResult:
        reference_path = Path(reference_image_path)
        if not reference_path.exists():
            raise ValueError(f"Reference image not found: {reference_image_path}")
        image_dir = ensure_dir(images_dir / f"shot_{shot.shot_id:02d}")
        return self._resolve_provider_chain(
            project_id=project_id,
            action_name=f"generate_reference_image_{shot.shot_id}",
            provider_names=self.settings.image_provider_priority,
            builder=self._build_image_provider,
            request_payload={"reference_image_path": str(reference_path), **shot.model_dump()},
            handler=lambda provider, shot=shot, image_dir=image_dir: self._run_with_retries(
                project_id,
                provider.name,
                f"generate_reference_image_{shot.shot_id}",
                max_attempts=2 if provider.name == "volcengine_image" else 1,
                request_payload={"reference_image_path": str(reference_path), **shot.model_dump()},
                func=lambda provider=provider, shot=shot, image_dir=image_dir: provider.generate(
                    shot,
                    image_dir,
                    reference_path,
                ),
            ),
        )

    def _load_newsroom_preview_images(
        self,
        project: ProjectRecord,
        shots: list[StoryboardShot],
    ) -> list[ImageGenerationResult]:
        frames_dir = Path(project.artifacts.working_dir) / "newsroom" / "preview_frames"
        frame_paths = sorted(frames_dir.glob("scene_*.png"))
        if not frame_paths:
            return []

        preview_images: list[ImageGenerationResult] = []
        for index, shot in enumerate(shots):
            frame_path = frame_paths[index % len(frame_paths)]
            preview_images.append(
                ImageGenerationResult(
                    provider_name="newsroom_preview",
                    shot_id=shot.shot_id,
                    image_path=str(frame_path),
                    raw_response={
                        "mode": "newsroom_preview",
                        "source_frame": frame_path.name,
                        "reused_frame": index >= len(frame_paths),
                    },
                    used_fallback=True,
                )
            )
        return preview_images

    def _render_static_image_shot(
        self,
        project_id: str,
        shot: StoryboardShot,
        shot_dir: Path,
        shot_image: ImageGenerationResult | None,
    ) -> VideoGenerationResult:
        provider = StaticImageVideoProvider()
        if shot_image is not None and Path(shot_image.image_path).exists():
            func = lambda provider=provider, shot=shot, shot_dir=shot_dir, shot_image=shot_image: provider.image_to_video(
                shot,
                Path(shot_image.image_path),
                shot_dir,
            )
        else:
            func = lambda provider=provider, shot=shot, shot_dir=shot_dir: provider.text_to_video(shot, shot_dir)
        return self._run_with_retries(
            project_id,
            provider.name,
            f"generate_image_shot_{shot.shot_id}",
            max_attempts=1,
            request_payload=shot.model_dump(),
            func=func,
        )

    def _render_video_shot_from_text(
        self,
        project_id: str,
        shot: StoryboardShot,
        shot_dir: Path,
    ) -> VideoGenerationResult:
        return self._resolve_provider_chain(
            project_id=project_id,
            action_name=f"generate_video_shot_{shot.shot_id}",
            provider_names=self.settings.video_provider_priority,
            builder=self._build_video_provider,
            request_payload=shot.model_dump(),
            handler=lambda provider, shot=shot, shot_dir=shot_dir: self._run_with_retries(
                project_id,
                provider.name,
                f"generate_video_shot_{shot.shot_id}",
                max_attempts=3 if provider.name == "volcengine_video" else 1,
                request_payload=shot.model_dump(),
                func=lambda provider=provider, shot=shot, shot_dir=shot_dir: provider.text_to_video(shot, shot_dir),
            ),
        )

    def _render_video_shot_from_image(
        self,
        project_id: str,
        shot: StoryboardShot,
        shot_dir: Path,
        shot_image: ImageGenerationResult,
    ) -> VideoGenerationResult:
        request_payload = {"image_path": shot_image.image_path, **shot.model_dump()}
        provider_names = tuple(name for name in self.settings.video_provider_priority if name != "mock_video")
        if not provider_names:
            provider_names = ("static_image_video",)
        try:
            return self._resolve_provider_chain(
                project_id=project_id,
                action_name=f"generate_video_from_image_shot_{shot.shot_id}",
                provider_names=provider_names,
                builder=self._build_video_or_static_provider,
                request_payload=request_payload,
                handler=lambda provider, shot=shot, shot_dir=shot_dir, shot_image=shot_image: self._run_with_retries(
                    project_id,
                    provider.name,
                    f"generate_video_from_image_shot_{shot.shot_id}",
                    max_attempts=3 if provider.name == "volcengine_video" else 1,
                    request_payload=request_payload,
                    func=lambda provider=provider, shot=shot, shot_dir=shot_dir, shot_image=shot_image: self._invoke_image_to_video_provider(
                        provider,
                        shot,
                        shot_dir,
                        shot_image,
                    ),
                ),
            )
        except RuntimeError as exc:
            fallback_provider = StaticImageVideoProvider()
            fallback_result = self._run_with_retries(
                project_id,
                fallback_provider.name,
                f"generate_video_from_image_shot_{shot.shot_id}_fallback",
                max_attempts=1,
                request_payload={**request_payload, "fallback_reason": str(exc)},
                func=lambda: fallback_provider.image_to_video(shot, Path(shot_image.image_path), shot_dir),
            )
            raw_response = dict(fallback_result.raw_response)
            raw_response["upstream_error"] = str(exc)
            return fallback_result.model_copy(update={"used_fallback": True, "raw_response": raw_response})

    def _invoke_image_to_video_provider(
        self,
        provider: VideoGenerationProvider,
        shot: StoryboardShot,
        shot_dir: Path,
        shot_image: ImageGenerationResult,
    ) -> VideoGenerationResult:
        if isinstance(provider, VolcengineVideoProvider) and shot_image.public_image_url:
            return provider.image_url_to_video(shot, shot_image.public_image_url, shot_dir)
        return provider.image_to_video(shot, Path(shot_image.image_path), shot_dir)

    def _attach_generated_videos_to_images(
        self,
        shot_images: list[ImageGenerationResult],
        shot_videos: list[VideoGenerationResult],
    ) -> list[ImageGenerationResult]:
        if not shot_images:
            return shot_images
        video_map = {item.shot_id: item.video_path for item in shot_videos}
        return [
            shot_image.model_copy(update={"source_video_path": video_map.get(shot_image.shot_id, shot_image.source_video_path)})
            for shot_image in shot_images
        ]

    def _prepare_shot_images_for_render(
        self,
        project: ProjectRecord,
        project_id: str,
        storyboard: list[StoryboardShot],
        images_dir: Path,
        render_mode: str,
        reference_image_path: str | None,
        reuse_existing_shot_images: bool,
    ) -> list[ImageGenerationResult]:
        if reuse_existing_shot_images:
            existing_images = self._collect_existing_shot_images(project, storyboard)
            if len(existing_images) == len(storyboard):
                return [existing_images[shot.shot_id] for shot in storyboard]

        shot_images = self._generate_shot_images(
            project_id=project_id,
            shots=storyboard,
            images_dir=images_dir,
            render_mode=render_mode,
            reference_image_path=reference_image_path,
        )
        if shot_images:
            return shot_images

        shot_images = self._load_newsroom_preview_images(project, storyboard)
        if shot_images:
            self._append_project_warning(project, "未生成镜头图片，已回退为 newsroom 预览帧。")
        return shot_images

    def _collect_existing_shot_images(
        self,
        project: ProjectRecord,
        storyboard: list[StoryboardShot],
    ) -> dict[int, ImageGenerationResult]:
        valid_ids = {shot.shot_id for shot in storyboard}
        existing: dict[int, ImageGenerationResult] = {}
        for item in project.artifacts.shot_images:
            if item.shot_id in valid_ids and Path(item.image_path).exists():
                existing[item.shot_id] = item
        return existing

    def _generate_placeholder_image_for_shot(
        self,
        project_id: str,
        shot: StoryboardShot,
        images_dir: Path,
    ) -> ImageGenerationResult:
        provider = MockImageGenerationProvider()
        image_dir = ensure_dir(images_dir / f"shot_{shot.shot_id:02d}")
        placeholder_reference = image_dir / "_placeholder_reference.png"
        return self._run_with_retries(
            project_id,
            provider.name,
            f"generate_reference_image_{shot.shot_id}_placeholder",
            max_attempts=1,
            request_payload={"shot_id": shot.shot_id, "placeholder": True},
            func=lambda: provider.generate(shot, image_dir, placeholder_reference),
        )

    def _export_publish_package(
        self,
        project_id: str,
        script: ScriptDraft,
        summary,
        final_video_path: Path,
        cover_path: Path,
        working_dir: Path,
        publish_mode: str,
    ) -> PublishPackage:
        publish_dir = ensure_dir(working_dir / "publish")
        return self._resolve_provider_chain(
            project_id=project_id,
            action_name="export_publish_package",
            provider_names=self.settings.publishing_provider_priority,
            builder=self._build_publishing_provider,
            request_payload={"publish_mode": publish_mode},
            handler=lambda provider: self._run_with_retries(
                project_id,
                provider.name,
                "export_publish_package",
                max_attempts=1,
                request_payload={"publish_mode": publish_mode},
                func=lambda: provider.export(script, summary, final_video_path, cover_path, publish_dir, publish_mode),
            ),
        )

    def _resolve_provider_chain(
        self,
        project_id: str,
        action_name: str,
        provider_names: tuple[str, ...],
        builder: Callable[[str], T],
        request_payload: dict,
        handler: Callable[[T], T],
    ) -> T:
        errors: list[str] = []
        for provider_name in provider_names:
            try:
                provider = builder(provider_name)
            except ProviderError as exc:
                errors.append(f"{provider_name}: {exc}")
                continue
            try:
                return handler(provider)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{provider_name}: {exc}")
                continue
        self.database.log_provider_attempt(
            project_id=project_id,
            provider_name="provider_chain",
            action_name=action_name,
            attempt_no=1,
            status="failed",
            request_payload=request_payload,
            error_message=" | ".join(errors),
        )
        raise RuntimeError(f"All providers failed for {action_name}: {' | '.join(errors)}")

    def _run_with_retries(
        self,
        project_id: str,
        provider_name: str,
        action_name: str,
        max_attempts: int,
        request_payload: dict,
        func: Callable[[], T],
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                result = func()
                response_payload = json.loads(result.model_dump_json())
                self.database.log_provider_attempt(
                    project_id=project_id,
                    provider_name=provider_name,
                    action_name=action_name,
                    attempt_no=attempt,
                    status="success",
                    request_payload=request_payload,
                    response_payload=response_payload,
                )
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self.database.log_provider_attempt(
                    project_id=project_id,
                    provider_name=provider_name,
                    action_name=action_name,
                    attempt_no=attempt,
                    status="failed",
                    request_payload=request_payload,
                    error_message=str(exc),
                )
        raise RuntimeError(f"{provider_name} failed after {max_attempts} attempts: {last_error}")

    def _build_llm_provider(self, name: str) -> LLMProvider:
        if name == "mock_llm":
            return MockLLMProvider()
        if name == "openai_llm":
            return OpenAICompatibleLLMProvider(self.settings)
        raise ProviderError(f"Unknown LLM provider: {name}")

    def _build_video_provider(self, name: str) -> VideoGenerationProvider:
        if name == "mock_video":
            return MockVideoGenerationProvider()
        if name == "volcengine_video":
            return VolcengineVideoProvider(self.settings)
        raise ProviderError(f"Unknown video provider: {name}")

    def _build_video_or_static_provider(self, name: str) -> VideoGenerationProvider:
        if name == "static_image_video":
            return StaticImageVideoProvider()
        return self._build_video_provider(name)

    def _build_image_provider(self, name: str) -> ImageGenerationProvider:
        if name == "mock_image":
            return MockImageGenerationProvider()
        if name == "volcengine_image":
            return VolcengineImageProvider(self.settings)
        raise ProviderError(f"Unknown image provider: {name}")

    def _build_tts_provider(self, name: str) -> TTSProvider:
        if name == "mock_tts":
            return MockTTSProvider()
        if name == "volcengine_tts":
            return VolcengineTTSProvider(self.settings)
        raise ProviderError(f"Unknown TTS provider: {name}")

    def _build_subtitle_provider(self, name: str) -> SubtitleProvider:
        if name == "local_subtitle":
            return LocalSubtitleProvider()
        raise ProviderError(f"Unknown subtitle provider: {name}")

    def _build_publishing_provider(self, name: str) -> PublishingProvider:
        if name == "douyin_publisher":
            return DouyinPublisher(self.settings)
        if name == "mock_publisher":
            return MockPublishingProvider()
        raise ProviderError(f"Unknown publishing provider: {name}")

    def _create_project_workspace(self) -> tuple[str, Path]:
        project_id = uuid.uuid4().hex[:12]
        working_dir = ensure_dir(self.settings.runtime_dir / project_id)
        return project_id, working_dir

    def _write_project_documents(self, project: ProjectRecord) -> None:
        working_dir = ensure_dir(Path(project.artifacts.working_dir))
        if project.summary is not None:
            write_json(working_dir / "summary.json", project.summary.model_dump())
            project.artifacts.summary_path = str(working_dir / "summary.json")
        if project.script is not None:
            write_json(working_dir / "script.json", project.script.model_dump())
            project.artifacts.script_path = str(working_dir / "script.json")
        write_json(working_dir / "storyboard.json", {"shots": [shot.model_dump() for shot in project.storyboard]})
        project.artifacts.storyboard_path = str(working_dir / "storyboard.json")

    def _reset_render_outputs(self, project: ProjectRecord, clear_images: bool) -> None:
        if clear_images:
            project.artifacts.shot_images = []
            project.artifacts.shot_reference_paths = {}
        project.artifacts.shot_videos = []
        project.artifacts.composition = None
        project.artifacts.publish_package = None
        project.artifacts.voice = None
        project.artifacts.subtitles = None
        project.artifacts.last_render_mode = ""

    def _require_existing_local_path(self, raw_path: str) -> str:
        candidate = self._normalize_local_path(raw_path)
        if not candidate.exists():
            raise ValueError(f"Reference image not found: {candidate}")
        return str(candidate)

    def _compose_feed_script(self, intro_hook: str, segment_narrations: list[str], takeaway: str) -> str:
        sections: list[str] = []
        if intro_hook:
            sections.append(intro_hook)
        sections.extend(item for item in segment_narrations if item)
        if takeaway:
            sections.append(takeaway)
        deduped_sections: list[str] = []
        for section in sections:
            if section not in deduped_sections:
                deduped_sections.append(section)
        return " ".join(deduped_sections)

    def _resolve_reference_image_path(self, reference_image_path: str | None) -> str | None:
        explicit_path = (reference_image_path or "").strip()
        if explicit_path:
            candidate = self._normalize_local_path(explicit_path)
            if not candidate.exists():
                raise ValueError(f"Reference image not found: {candidate}")
            return str(candidate)

        default_path = self.settings.default_reference_image_path.strip()
        if not default_path:
            return None
        candidate = self._normalize_local_path(default_path)
        if candidate.exists():
            return str(candidate)
        return None

    def _normalize_local_path(self, raw_path: str) -> Path:
        normalized = raw_path.strip().strip('"')
        if len(normalized) > 2 and normalized[1] == ":" and normalized[2] not in {"\\", "/"}:
            suffix = normalized[2:].lstrip("\\/")
            normalized = f"{normalized[:2]}\\{suffix}"
        return Path(normalized)

    def _append_project_warning(self, project: ProjectRecord, warning: str) -> None:
        if warning and warning not in project.warnings:
            project.warnings.append(warning)

    def _preview_canvas_size(self, aspect_ratio: str) -> tuple[int, int]:
        if aspect_ratio == "16:9":
            return 1920, 1080
        return 1080, 1920

    def _build_script_summary(self, title: str, full_script: str) -> ContentSummary:
        sentences = self.storyboard_engine._split_sentences(full_script)
        bullet_points = sentences[:4]
        key_facts = sentences[1:4] if len(sentences) > 1 else sentences[:3]
        return ContentSummary(
            title=title,
            summary=" ".join(sentences[:2])[:180],
            bullet_points=bullet_points,
            key_facts=key_facts,
            warnings=[],
            publish_angle="script_first_case",
        )

    def _build_script_draft(self, title: str, full_script: str) -> ScriptDraft:
        sentences = self.storyboard_engine._split_sentences(full_script)
        intro_hook = sentences[0] if sentences else title
        closing = sentences[-1] if sentences else title
        return ScriptDraft(
            title=title,
            intro_hook=intro_hook,
            full_script=full_script,
            closing=closing,
            review_notes=[],
        )
