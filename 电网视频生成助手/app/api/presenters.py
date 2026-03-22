from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.models.project import (
    CreateProjectResponse,
    ProjectAssetLinks,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectRecord,
    ProviderAttemptRecord,
)


def build_create_response(project: ProjectRecord) -> CreateProjectResponse:
    if project.summary is None or project.script is None:
        raise ValueError("Project draft is missing summary or script.")
    return CreateProjectResponse(
        project_id=project.project_id,
        status=project.status,
        summary=project.summary,
        script=project.script,
        storyboard=project.storyboard,
        working_dir=project.artifacts.working_dir,
        warnings=project.warnings,
        artifacts=project.artifacts,
    )


def build_project_list_item(project: ProjectRecord, settings: Settings) -> ProjectListItem:
    final_video_path = project.artifacts.composition.video_path if project.artifacts.composition else None
    return ProjectListItem(
        project_id=project.project_id,
        title=project.summary.title if project.summary else project.content_input.title or project.project_id,
        status=project.status,
        mode=project.content_input.mode.value,
        source_type=project.content_input.source_type,
        shot_count=len(project.storyboard),
        warning_count=len(project.warnings),
        created_at=project.created_at,
        updated_at=project.updated_at,
        working_dir=project.artifacts.working_dir,
        final_video_path=final_video_path,
        final_video_url=build_runtime_url(final_video_path, settings),
    )


def build_project_detail_response(
    project: ProjectRecord,
    attempts: list[dict],
    settings: Settings,
) -> ProjectDetailResponse:
    return ProjectDetailResponse(
        project=project,
        attempts=[build_attempt_record(item) for item in attempts],
        asset_links=ProjectAssetLinks(
            final_video_url=build_runtime_url(
                project.artifacts.composition.video_path if project.artifacts.composition else None,
                settings,
            ),
            audio_url=build_runtime_url(
                project.artifacts.voice.audio_path if project.artifacts.voice else None,
                settings,
            ),
            subtitle_url=build_runtime_url(
                project.artifacts.subtitles.subtitle_path if project.artifacts.subtitles else None,
                settings,
            ),
            publish_payload_url=build_runtime_url(
                project.artifacts.publish_package.payload_path if project.artifacts.publish_package else None,
                settings,
            ),
            preview_cover_url=build_runtime_url(project.artifacts.preview_cover_path, settings),
            preview_gif_url=build_runtime_url(project.artifacts.preview_gif_path, settings),
            preview_video_url=build_runtime_url(project.artifacts.preview_video_path, settings),
            shot_image_urls=_collect_urls([item.image_path for item in project.artifacts.shot_images], settings),
            shot_video_urls=_collect_urls([item.video_path for item in project.artifacts.shot_videos], settings),
            shot_poster_urls=_collect_urls([item.poster_path for item in project.artifacts.shot_videos], settings),
        ),
    )


def build_attempt_record(payload: dict) -> ProviderAttemptRecord:
    return ProviderAttemptRecord(
        provider_name=str(payload.get("provider_name", "")),
        action_name=str(payload.get("action_name", "")),
        attempt_no=int(payload.get("attempt_no", 1)),
        status=str(payload.get("status", "")),
        request_payload=_parse_json(payload.get("request_json")),
        response_payload=_parse_json(payload.get("response_json")),
        error_message=payload.get("error_message"),
        created_at=str(payload.get("created_at", "")),
    )


def build_runtime_url(path_value: str | None, settings: Settings) -> str | None:
    if not path_value:
        return None

    normalized = path_value.replace("\\", "/")
    if normalized.startswith("runtime/"):
        return "/" + normalized

    marker = "/runtime/"
    if marker in normalized:
        return normalized[normalized.index(marker) :]

    runtime_root = settings.runtime_dir.resolve()
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = (settings.project_root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    try:
        relative = candidate.relative_to(runtime_root)
    except ValueError:
        return None
    return "/runtime/" + relative.as_posix()


def _collect_urls(paths: list[str], settings: Settings) -> list[str]:
    urls: list[str] = []
    for path_value in paths:
        url = build_runtime_url(path_value, settings)
        if url:
            urls.append(url)
    return urls


def _parse_json(raw_value: str | None) -> dict | None:
    if not raw_value:
        return None
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return {"raw": raw_value}
