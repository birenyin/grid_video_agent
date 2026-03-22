from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.models.content import (
    CompositionResult,
    ContentInput,
    ContentSummary,
    ImageGenerationResult,
    PublishPackage,
    ScriptDraft,
    StoryboardShot,
    SubtitleResult,
    TTSResult,
    VideoGenerationResult,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectStatus(str, Enum):
    draft = "draft"
    rendering = "rendering"
    rendered = "rendered"
    failed = "failed"


class ProjectArtifacts(BaseModel):
    working_dir: str = ""
    storyboard_path: str = ""
    summary_path: str = ""
    script_path: str = ""
    news_plan_path: str = ""
    news_report_path: str = ""
    selected_sources_path: str = ""
    preview_cover_path: str = ""
    preview_gif_path: str = ""
    preview_video_path: str = ""
    last_render_mode: str = ""
    resolved_reference_image_path: str = ""
    voice: TTSResult | None = None
    subtitles: SubtitleResult | None = None
    shot_images: list[ImageGenerationResult] = Field(default_factory=list)
    shot_videos: list[VideoGenerationResult] = Field(default_factory=list)
    composition: CompositionResult | None = None
    publish_package: PublishPackage | None = None


class ProjectRecord(BaseModel):
    project_id: str
    status: ProjectStatus = ProjectStatus.draft
    content_input: ContentInput
    summary: ContentSummary | None = None
    script: ScriptDraft | None = None
    storyboard: list[StoryboardShot] = Field(default_factory=list)
    artifacts: ProjectArtifacts = Field(default_factory=ProjectArtifacts)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateProjectFromTextRequest(BaseModel):
    title: str | None = None
    content_text: str = Field(..., min_length=20)
    source_url: str | None = None
    mode: str = Field(default="news_mode", pattern="^(explain_mode|news_mode)$")
    target_duration_seconds: int = Field(default=60, ge=15, le=150)
    aspect_ratio: str = Field(default="9:16", pattern="^(9:16|16:9)$")


class CreateProjectFromScriptRequest(BaseModel):
    title: str
    full_script: str = Field(..., min_length=40)
    mode: str = Field(default="explain_mode", pattern="^(explain_mode|news_mode)$")
    target_duration_seconds: int = Field(default=60, ge=15, le=150)
    aspect_ratio: str = Field(default="9:16", pattern="^(9:16|16:9)$")


class CreateProjectFromUrlRequest(BaseModel):
    source_url: str = Field(..., min_length=8)
    title: str | None = None
    mode: str = Field(default="news_mode", pattern="^(explain_mode|news_mode)$")
    target_duration_seconds: int = Field(default=60, ge=15, le=150)
    aspect_ratio: str = Field(default="9:16", pattern="^(9:16|16:9)$")


class CreateProjectFromFeedRequest(BaseModel):
    feed_path: str = Field(..., min_length=3)
    title: str | None = None
    mode: str = Field(default="news_mode", pattern="^(explain_mode|news_mode)$")
    target_duration_seconds: int = Field(default=60, ge=15, le=150)
    aspect_ratio: str = Field(default="9:16", pattern="^(9:16|16:9)$")
    plan_mode: str = Field(default="rule", pattern="^(rule|auto|api)$")
    render_preview_bundle: bool = True


class CreateProjectResponse(BaseModel):
    project_id: str
    status: ProjectStatus
    summary: ContentSummary
    script: ScriptDraft
    storyboard: list[StoryboardShot]
    working_dir: str
    warnings: list[str] = Field(default_factory=list)
    artifacts: ProjectArtifacts | None = None


class RenderProjectRequest(BaseModel):
    preferred_voice: str = "professional_cn_male"
    publish_mode: str = "draft"
    render_mode: str = Field(default="video_audio", pattern="^(image_audio|video_audio)$")
    aspect_ratio: str | None = Field(default=None, pattern="^(9:16|16:9)$")
    reference_image_path: str | None = None


class RenderProjectResponse(BaseModel):
    project_id: str
    status: ProjectStatus
    final_video_path: str
    audio_path: str
    subtitle_path: str
    publish_payload_path: str
    attempt_count: int


class ProviderAttemptRecord(BaseModel):
    provider_name: str
    action_name: str
    attempt_no: int
    status: str
    request_payload: dict | None = None
    response_payload: dict | None = None
    error_message: str | None = None
    created_at: str


class ProjectAssetLinks(BaseModel):
    final_video_url: str | None = None
    audio_url: str | None = None
    subtitle_url: str | None = None
    publish_payload_url: str | None = None
    preview_cover_url: str | None = None
    preview_gif_url: str | None = None
    preview_video_url: str | None = None
    shot_image_urls: list[str] = Field(default_factory=list)
    shot_video_urls: list[str] = Field(default_factory=list)
    shot_poster_urls: list[str] = Field(default_factory=list)


class ProjectListItem(BaseModel):
    project_id: str
    title: str
    status: ProjectStatus
    mode: str
    source_type: str
    shot_count: int
    warning_count: int
    created_at: str
    updated_at: str
    working_dir: str
    final_video_path: str | None = None
    final_video_url: str | None = None


class ProjectDetailResponse(BaseModel):
    project: ProjectRecord
    attempts: list[ProviderAttemptRecord] = Field(default_factory=list)
    asset_links: ProjectAssetLinks = Field(default_factory=ProjectAssetLinks)
