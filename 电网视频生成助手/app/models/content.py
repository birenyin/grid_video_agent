from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ContentMode(str, Enum):
    explain_mode = "explain_mode"
    news_mode = "news_mode"


class ShotType(str, Enum):
    host = "host"
    explainer = "explainer"
    broll = "broll"
    data = "data"


class ContentInput(BaseModel):
    title: str | None = None
    raw_text: str = Field(..., min_length=20)
    source_url: str | None = None
    source_type: str = "manual"
    mode: ContentMode = ContentMode.news_mode
    target_duration_seconds: int = Field(default=60, ge=15, le=150)
    aspect_ratio: str = Field(default="9:16", pattern="^(9:16|16:9)$")
    keywords: list[str] = Field(default_factory=list)


class ContentSummary(BaseModel):
    title: str
    summary: str
    bullet_points: list[str] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    publish_angle: str = ""


class ScriptDraft(BaseModel):
    title: str
    intro_hook: str
    full_script: str
    closing: str
    review_notes: list[str] = Field(default_factory=list)


class StoryboardShot(BaseModel):
    shot_id: int
    shot_duration: int = Field(..., ge=3, le=6)
    aspect_ratio: str = Field(default="9:16", pattern="^(9:16|16:9)$")
    narration_text: str
    subtitle_text: str
    visual_prompt_cn: str
    visual_prompt_en: str
    shot_type: ShotType
    camera_movement: str
    visual_keywords: list[str] = Field(default_factory=list)
    safety_notes: str = ""
    needs_real_material: bool = False


class VoiceSynthesisOptions(BaseModel):
    voice: str = "professional_cn_male"
    speed: float = 1.0
    pitch: float = 1.0
    emotion: str = "professional"
    format: str = "wav"
    voice_clone_id: str | None = None


class TTSResult(BaseModel):
    provider_name: str
    audio_path: str
    duration_seconds: float
    voice_name: str
    raw_response: dict = Field(default_factory=dict)
    used_fallback: bool = False


class SubtitleCue(BaseModel):
    index: int
    start_seconds: float
    end_seconds: float
    text: str


class SubtitleResult(BaseModel):
    provider_name: str
    subtitle_path: str
    cues: list[SubtitleCue] = Field(default_factory=list)


class ImageGenerationResult(BaseModel):
    provider_name: str
    shot_id: int
    image_path: str
    public_image_url: str = ""
    source_video_path: str = ""
    raw_response: dict = Field(default_factory=dict)
    used_fallback: bool = False


class VideoGenerationResult(BaseModel):
    provider_name: str
    shot_id: int
    video_path: str
    poster_path: str
    task_id: str | None = None
    raw_response: dict = Field(default_factory=dict)
    used_fallback: bool = False


class CompositionResult(BaseModel):
    video_path: str
    cover_path: str
    clip_paths: list[str] = Field(default_factory=list)
    used_subtitle_burn: bool = False


class PublishPackage(BaseModel):
    provider_name: str
    title: str
    description: str
    hashtags: list[str] = Field(default_factory=list)
    video_path: str
    cover_path: str
    publish_mode: str = "draft"
    payload_path: str
    raw_payload: dict = Field(default_factory=dict)
