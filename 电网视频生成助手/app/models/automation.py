from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutomationJobStatus(str, Enum):
    active = "active"
    paused = "paused"


class AutomationRunStatus(str, Enum):
    success = "success"
    failed = "failed"


class AutomationFetchOptions(BaseModel):
    source_set: str = Field(default="mixed", pattern="^(official|mixed)$")
    per_source_limit: int = Field(default=3, ge=1, le=10)
    total_fetch_limit: int = Field(default=8, ge=1, le=20)
    plan_mode: str = Field(default="rule", pattern="^(rule|auto|api)$")
    focus_topics: list[str] = Field(default_factory=list)


class AutomationRenderOptions(BaseModel):
    auto_render: bool = True
    render_mode: str = Field(default="image_audio", pattern="^(image_audio|video_audio)$")
    preferred_voice: str = "professional_cn_male"
    publish_mode: str = "draft"
    reference_image_path: str | None = None


class AutomationCandidateItem(BaseModel):
    candidate_key: str
    title: str
    source: str
    summary: str = ""
    published_at: str = ""
    url: str = ""
    tags: list[str] = Field(default_factory=list)
    content_category: str = ""
    reliability_score: int = 0
    hotness_score: int = 0
    score: int = 0
    is_new: bool = True


class AutomationJobRecord(BaseModel):
    job_id: str
    name: str
    status: AutomationJobStatus = AutomationJobStatus.active
    interval_minutes: int = Field(default=240, ge=5, le=10080)
    mode: str = Field(default="news_mode", pattern="^(explain_mode|news_mode)$")
    target_duration_seconds: int = Field(default=60, ge=15, le=150)
    aspect_ratio: str = Field(default="9:16", pattern="^(9:16|16:9)$")
    fetch: AutomationFetchOptions = Field(default_factory=AutomationFetchOptions)
    render: AutomationRenderOptions = Field(default_factory=AutomationRenderOptions)
    last_run_at: str | None = None
    next_run_at: str | None = None
    last_project_id: str | None = None
    last_run_status: str = ""
    last_error: str = ""
    seen_item_keys: list[str] = Field(default_factory=list)
    latest_feed_path: str = ""
    latest_candidate_count: int = 0
    latest_new_item_count: int = 0
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class AutomationRunRecord(BaseModel):
    run_id: str
    job_id: str
    trigger_type: str
    status: AutomationRunStatus
    started_at: str
    finished_at: str
    project_id: str | None = None
    output_dir: str = ""
    feed_path: str = ""
    fetched_item_count: int = 0
    new_item_count: int = 0
    duplicate_item_count: int = 0
    candidates: list[AutomationCandidateItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    error_message: str = ""


class CreateAutomationJobRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=60)
    interval_minutes: int = Field(default=240, ge=5, le=10080)
    mode: str = Field(default="news_mode", pattern="^(explain_mode|news_mode)$")
    target_duration_seconds: int = Field(default=60, ge=15, le=150)
    aspect_ratio: str = Field(default="9:16", pattern="^(9:16|16:9)$")
    source_set: str = Field(default="mixed", pattern="^(official|mixed)$")
    per_source_limit: int = Field(default=3, ge=1, le=10)
    total_fetch_limit: int = Field(default=8, ge=1, le=20)
    plan_mode: str = Field(default="rule", pattern="^(rule|auto|api)$")
    focus_topics: list[str] = Field(default_factory=list)
    auto_render: bool = True
    render_mode: str = Field(default="image_audio", pattern="^(image_audio|video_audio)$")
    preferred_voice: str = "professional_cn_male"
    publish_mode: str = "draft"
    reference_image_path: str | None = None


class UpdateAutomationJobStatusRequest(BaseModel):
    status: AutomationJobStatus


class CreateAutomationProjectRequest(BaseModel):
    run_id: str
    selected_item_keys: list[str] = Field(default_factory=list)
    title: str | None = None
    mode: str | None = Field(default=None, pattern="^(explain_mode|news_mode)$")
    target_duration_seconds: int | None = Field(default=None, ge=15, le=150)
    aspect_ratio: str | None = Field(default=None, pattern="^(9:16|16:9)$")
    plan_mode: str | None = Field(default=None, pattern="^(rule|auto|api)$")
    render_preview_bundle: bool = True
    auto_render: bool | None = None
    render_mode: str | None = Field(default=None, pattern="^(image_audio|video_audio)$")
    preferred_voice: str | None = None
    publish_mode: str | None = None
    reference_image_path: str | None = None


class AutomationJobDetailResponse(BaseModel):
    job: AutomationJobRecord
    runs: list[AutomationRunRecord] = Field(default_factory=list)
