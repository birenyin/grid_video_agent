from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_orchestrator
from app.api.presenters import (
    build_attempt_record,
    build_create_response,
    build_project_detail_response,
    build_project_list_item,
)
from app.models.project import (
    CreateProjectFromFeedRequest,
    CreateProjectFromScriptRequest,
    CreateProjectFromTextRequest,
    CreateProjectFromUrlRequest,
    CreateProjectResponse,
    ProjectDetailResponse,
    ProjectListItem,
    ProviderAttemptRecord,
    RenderProjectRequest,
    RenderProjectResponse,
    WorkflowGenerateImagesRequest,
    WorkflowGenerateVideosRequest,
    WorkflowScriptUpdateRequest,
)
from app.services.project_service import ProjectOrchestrator


router = APIRouter()


@router.post("/create_from_text", response_model=CreateProjectResponse)
def create_from_text(
    request: CreateProjectFromTextRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> CreateProjectResponse:
    project = orchestrator.create_from_text(request)
    return build_create_response(project)


@router.post("/create_from_script", response_model=CreateProjectResponse)
def create_from_script(
    request: CreateProjectFromScriptRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> CreateProjectResponse:
    project = orchestrator.create_from_script(request)
    return build_create_response(project)


@router.post("/create_from_url", response_model=CreateProjectResponse)
def create_from_url(
    request: CreateProjectFromUrlRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> CreateProjectResponse:
    try:
        project = orchestrator.create_from_url(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch source URL: {exc}") from exc
    return build_create_response(project)


@router.post("/create_from_rpa_feed", response_model=CreateProjectResponse)
def create_from_rpa_feed(
    request: CreateProjectFromFeedRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> CreateProjectResponse:
    try:
        project = orchestrator.create_from_rpa_feed(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_create_response(project)


@router.post("/{project_id}/render", response_model=RenderProjectResponse)
def render_project(
    project_id: str,
    request: RenderProjectRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> RenderProjectResponse:
    try:
        project = orchestrator.render_project(project_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if (
        project.artifacts.composition is None
        or project.artifacts.voice is None
        or project.artifacts.subtitles is None
        or project.artifacts.publish_package is None
    ):
        raise HTTPException(status_code=500, detail="Render completed without all expected artifacts.")

    attempt_count = len(orchestrator.database.list_provider_attempts(project_id))
    return RenderProjectResponse(
        project_id=project.project_id,
        status=project.status,
        final_video_path=project.artifacts.composition.video_path,
        audio_path=project.artifacts.voice.audio_path,
        subtitle_path=project.artifacts.subtitles.subtitle_path,
        publish_payload_path=project.artifacts.publish_package.payload_path,
        attempt_count=attempt_count,
    )


@router.put("/{project_id}/workflow/script", response_model=ProjectDetailResponse)
def update_workflow_script(
    project_id: str,
    request: WorkflowScriptUpdateRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> ProjectDetailResponse:
    try:
        project = orchestrator.update_workflow_script(project_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    attempts = orchestrator.database.list_provider_attempts(project.project_id)
    return build_project_detail_response(project, attempts, orchestrator.settings)


@router.post("/{project_id}/workflow/images", response_model=ProjectDetailResponse)
def generate_workflow_images(
    project_id: str,
    request: WorkflowGenerateImagesRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> ProjectDetailResponse:
    try:
        project = orchestrator.generate_workflow_images(project_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    attempts = orchestrator.database.list_provider_attempts(project.project_id)
    return build_project_detail_response(project, attempts, orchestrator.settings)


@router.post("/{project_id}/workflow/videos", response_model=ProjectDetailResponse)
def generate_workflow_videos(
    project_id: str,
    request: WorkflowGenerateVideosRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> ProjectDetailResponse:
    try:
        project = orchestrator.generate_workflow_videos(project_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    attempts = orchestrator.database.list_provider_attempts(project.project_id)
    return build_project_detail_response(project, attempts, orchestrator.settings)


@router.post("/{project_id}/workflow/render", response_model=RenderProjectResponse)
def render_workflow_project(
    project_id: str,
    request: RenderProjectRequest,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> RenderProjectResponse:
    try:
        project = orchestrator.render_workflow_project(project_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if (
        project.artifacts.composition is None
        or project.artifacts.voice is None
        or project.artifacts.subtitles is None
        or project.artifacts.publish_package is None
    ):
        raise HTTPException(status_code=500, detail="Workflow render completed without all expected artifacts.")

    attempt_count = len(orchestrator.database.list_provider_attempts(project_id))
    return RenderProjectResponse(
        project_id=project.project_id,
        status=project.status,
        final_video_path=project.artifacts.composition.video_path,
        audio_path=project.artifacts.voice.audio_path,
        subtitle_path=project.artifacts.subtitles.subtitle_path,
        publish_payload_path=project.artifacts.publish_package.payload_path,
        attempt_count=attempt_count,
    )


@router.get("", response_model=list[ProjectListItem])
def list_projects(
    limit: int = Query(default=50, ge=1, le=200),
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> list[ProjectListItem]:
    return [build_project_list_item(project, orchestrator.settings) for project in orchestrator.list_projects(limit)]


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: str,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> ProjectDetailResponse:
    try:
        project = orchestrator.get_project_or_raise(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    attempts = orchestrator.database.list_provider_attempts(project_id)
    return build_project_detail_response(project, attempts, orchestrator.settings)


@router.get("/{project_id}/attempts", response_model=list[ProviderAttemptRecord])
def list_project_attempts(
    project_id: str,
    orchestrator: ProjectOrchestrator = Depends(get_orchestrator),
) -> list[ProviderAttemptRecord]:
    try:
        orchestrator.get_project_or_raise(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [build_attempt_record(item) for item in orchestrator.database.list_provider_attempts(project_id)]
