from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import Settings
from app.core.database import Database
from app.models.automation import (
    AutomationFetchOptions,
    AutomationJobRecord,
    AutomationJobStatus,
    AutomationRenderOptions,
    AutomationRunRecord,
    AutomationRunStatus,
    CreateAutomationJobRequest,
)
from app.models.project import CreateProjectFromFeedRequest, RenderProjectRequest
from app.services.project_service import ProjectOrchestrator
from app.utils.files import ensure_dir
from src.grid_video_agent.config import AgentConfig
from src.grid_video_agent.fetchers import fetch_latest_grid_items


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_utc_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class AutomationService:
    def __init__(self, settings: Settings, database: Database, orchestrator: ProjectOrchestrator) -> None:
        self.settings = settings
        self.database = database
        self.orchestrator = orchestrator
        self.runtime_dir = ensure_dir(self.settings.runtime_dir / "automation_runs")
        self._running_job_ids: set[str] = set()
        self._lock = threading.Lock()

    def create_job(self, request: CreateAutomationJobRequest) -> AutomationJobRecord:
        job = AutomationJobRecord(
            job_id=uuid.uuid4().hex[:12],
            name=request.name,
            status=AutomationJobStatus.active,
            interval_minutes=request.interval_minutes,
            mode=request.mode,
            target_duration_seconds=request.target_duration_seconds,
            aspect_ratio=request.aspect_ratio,
            fetch=AutomationFetchOptions(
                source_set=request.source_set,
                per_source_limit=request.per_source_limit,
                total_fetch_limit=request.total_fetch_limit,
                plan_mode=request.plan_mode,
            ),
            render=AutomationRenderOptions(
                auto_render=request.auto_render,
                render_mode=request.render_mode,
                preferred_voice=request.preferred_voice,
                publish_mode=request.publish_mode,
                reference_image_path=request.reference_image_path,
            ),
            next_run_at=self._next_run_iso(request.interval_minutes),
        )
        self.database.save_automation_job(job)
        return job

    def list_jobs(self, limit: int = 100) -> list[AutomationJobRecord]:
        return self.database.list_automation_jobs(limit)

    def get_job_or_raise(self, job_id: str) -> AutomationJobRecord:
        job = self.database.get_automation_job(job_id)
        if job is None:
            raise ValueError(f"Automation job not found: {job_id}")
        return job

    def list_runs(self, job_id: str, limit: int = 30) -> list[AutomationRunRecord]:
        return self.database.list_automation_runs(job_id, limit)

    def set_job_status(self, job_id: str, status: AutomationJobStatus) -> AutomationJobRecord:
        job = self.get_job_or_raise(job_id)
        updates = {"status": status, "last_error": ""}
        if status == AutomationJobStatus.active:
            updates["next_run_at"] = self._next_run_iso(job.interval_minutes)
        job = job.model_copy(update=updates)
        self.database.save_automation_job(job)
        return job

    def run_job_now(self, job_id: str) -> AutomationRunRecord:
        job = self.get_job_or_raise(job_id)
        if not self._mark_running(job_id):
            raise RuntimeError(f"Automation job is already running: {job_id}")
        try:
            return self._execute_job(job, trigger_type="manual")
        finally:
            self._clear_running(job_id)

    def run_job_async(self, job_id: str, trigger_type: str = "schedule") -> bool:
        if not self._mark_running(job_id):
            return False

        thread = threading.Thread(
            target=self._run_job_thread,
            args=(job_id, trigger_type),
            daemon=True,
            name=f"automation-job-{job_id}",
        )
        thread.start()
        return True

    def queue_due_jobs(self) -> list[str]:
        queued: list[str] = []
        now = utc_now()
        for job in self.list_jobs():
            if job.status != AutomationJobStatus.active:
                continue
            next_run = parse_utc_iso(job.next_run_at)
            if next_run is None or next_run > now:
                continue
            if self.run_job_async(job.job_id, trigger_type="schedule"):
                queued.append(job.job_id)
        return queued

    def _run_job_thread(self, job_id: str, trigger_type: str) -> None:
        try:
            job = self.get_job_or_raise(job_id)
            self._execute_job(job, trigger_type=trigger_type)
        finally:
            self._clear_running(job_id)

    def _execute_job(self, job: AutomationJobRecord, trigger_type: str) -> AutomationRunRecord:
        started_at = utc_now_iso()
        run_dir = ensure_dir(self.runtime_dir / job.job_id / self._timestamp_label())
        fetch_dir = ensure_dir(run_dir / "fetch")
        notes: list[str] = []
        project_id: str | None = None
        fetched_item_count = 0

        try:
            config = AgentConfig(
                duration_seconds=job.target_duration_seconds,
                model_mode=job.fetch.plan_mode,
                source_set=job.fetch.source_set,
                per_source_limit=job.fetch.per_source_limit,
                total_fetch_limit=job.fetch.total_fetch_limit,
            )
            items, notes = fetch_latest_grid_items(
                config=config,
                output_dir=fetch_dir,
                source_set=job.fetch.source_set,
                per_source_limit=job.fetch.per_source_limit,
                total_limit=job.fetch.total_fetch_limit,
            )
            fetched_item_count = len(items)
            feed_path = fetch_dir / "fetched_feed.json"
            if fetched_item_count == 0 or not feed_path.exists():
                raise RuntimeError("No grid news items were fetched for this automation job.")

            project = self.orchestrator.create_from_rpa_feed(
                CreateProjectFromFeedRequest(
                    feed_path=str(feed_path),
                    title=None,
                    mode=job.mode,
                    target_duration_seconds=job.target_duration_seconds,
                    aspect_ratio=job.aspect_ratio,
                    plan_mode=job.fetch.plan_mode,
                    render_preview_bundle=True,
                )
            )
            project_id = project.project_id

            if job.render.auto_render:
                rendered = self.orchestrator.render_project(
                    project.project_id,
                    RenderProjectRequest(
                        preferred_voice=job.render.preferred_voice,
                        publish_mode=job.render.publish_mode,
                        render_mode=job.render.render_mode,
                        aspect_ratio=job.aspect_ratio,
                        reference_image_path=job.render.reference_image_path,
                    ),
                )
                project_id = rendered.project_id

            finished_at = utc_now_iso()
            run = AutomationRunRecord(
                run_id=uuid.uuid4().hex[:12],
                job_id=job.job_id,
                trigger_type=trigger_type,
                status=AutomationRunStatus.success,
                started_at=started_at,
                finished_at=finished_at,
                project_id=project_id,
                output_dir=str(run_dir),
                fetched_item_count=fetched_item_count,
                notes=notes,
            )
            self.database.save_automation_run(run)
            self.database.save_automation_job(
                job.model_copy(
                    update={
                        "last_run_at": finished_at,
                        "next_run_at": self._next_run_iso(job.interval_minutes),
                        "last_project_id": project_id,
                        "last_run_status": run.status,
                        "last_error": "",
                    }
                )
            )
            return run
        except Exception as exc:
            finished_at = utc_now_iso()
            run = AutomationRunRecord(
                run_id=uuid.uuid4().hex[:12],
                job_id=job.job_id,
                trigger_type=trigger_type,
                status=AutomationRunStatus.failed,
                started_at=started_at,
                finished_at=finished_at,
                project_id=project_id,
                output_dir=str(run_dir),
                fetched_item_count=fetched_item_count,
                notes=notes,
                error_message=str(exc),
            )
            self.database.save_automation_run(run)
            self.database.save_automation_job(
                job.model_copy(
                    update={
                        "last_run_at": finished_at,
                        "next_run_at": self._next_run_iso(job.interval_minutes),
                        "last_project_id": project_id,
                        "last_run_status": run.status,
                        "last_error": str(exc),
                    }
                )
            )
            raise

    def _next_run_iso(self, interval_minutes: int) -> str:
        return (utc_now() + timedelta(minutes=interval_minutes)).isoformat()

    def _timestamp_label(self) -> str:
        return utc_now().strftime("%Y%m%dT%H%M%SZ")

    def _mark_running(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._running_job_ids:
                return False
            self._running_job_ids.add(job_id)
            return True

    def _clear_running(self, job_id: str) -> None:
        with self._lock:
            self._running_job_ids.discard(job_id)


class AutomationScheduler:
    def __init__(self, service: AutomationService, poll_seconds: float = 30.0) -> None:
        self.service = service
        self.poll_seconds = poll_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="automation-scheduler")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.service.queue_due_jobs()
            except Exception:
                pass
            self._stop_event.wait(self.poll_seconds)
