from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_automation_service
from app.api.presenters import build_create_response
from app.models.automation import (
    AutomationJobDetailResponse,
    AutomationJobRecord,
    AutomationRunRecord,
    CreateAutomationProjectRequest,
    CreateAutomationJobRequest,
    UpdateAutomationJobStatusRequest,
)
from app.models.project import CreateProjectResponse
from app.services.automation_service import AutomationService


router = APIRouter()


@router.post("/jobs", response_model=AutomationJobRecord)
def create_job(
    request: CreateAutomationJobRequest,
    service: AutomationService = Depends(get_automation_service),
) -> AutomationJobRecord:
    return service.create_job(request)


@router.get("/jobs", response_model=list[AutomationJobRecord])
def list_jobs(
    limit: int = Query(default=100, ge=1, le=200),
    service: AutomationService = Depends(get_automation_service),
) -> list[AutomationJobRecord]:
    return service.list_jobs(limit)


@router.get("/jobs/{job_id}", response_model=AutomationJobDetailResponse)
def get_job(
    job_id: str,
    service: AutomationService = Depends(get_automation_service),
) -> AutomationJobDetailResponse:
    try:
        job = service.get_job_or_raise(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AutomationJobDetailResponse(job=job, runs=service.list_runs(job_id))


@router.post("/jobs/{job_id}/run", response_model=AutomationRunRecord)
def run_job_now(
    job_id: str,
    service: AutomationService = Depends(get_automation_service),
) -> AutomationRunRecord:
    try:
        return service.run_job_now(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/projects", response_model=CreateProjectResponse)
def create_project_from_run(
    job_id: str,
    request: CreateAutomationProjectRequest,
    service: AutomationService = Depends(get_automation_service),
) -> CreateProjectResponse:
    try:
        project = service.create_project_from_run(job_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return build_create_response(project)


@router.post("/jobs/{job_id}/status", response_model=AutomationJobRecord)
def update_job_status(
    job_id: str,
    request: UpdateAutomationJobStatusRequest,
    service: AutomationService = Depends(get_automation_service),
) -> AutomationJobRecord:
    try:
        return service.set_job_status(job_id, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
