from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import Settings
from app.core.database import Database
from app.models.automation import (
    AutomationCandidateItem,
    AutomationFetchOptions,
    AutomationJobRecord,
    CreateAutomationProjectRequest,
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
from src.grid_video_agent.pipeline import score_news


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
                focus_topics=request.focus_topics,
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

    def get_run_or_raise(self, job_id: str, run_id: str) -> AutomationRunRecord:
        run = self.database.get_automation_run(run_id)
        if run is None or run.job_id != job_id:
            raise ValueError(f"Automation run not found: {run_id}")
        return run

    def set_job_status(self, job_id: str, status: AutomationJobStatus) -> AutomationJobRecord:
        job = self.get_job_or_raise(job_id)
        updates = {"status": status, "last_error": ""}
        if status == AutomationJobStatus.active:
            updates["next_run_at"] = self._next_run_iso(job.interval_minutes)
        job = job.model_copy(update=updates)
        self.database.save_automation_job(job)
        return job

    def create_project_from_run(self, job_id: str, request: CreateAutomationProjectRequest):
        job = self.get_job_or_raise(job_id)
        run = self.get_run_or_raise(job_id, request.run_id)
        feed_path = Path(run.feed_path or Path(run.output_dir) / "fetch" / "fetched_feed.json")
        if not feed_path.exists():
            raise ValueError(f"Fetched feed not found for automation run: {feed_path}")

        selected_item_keys = [
            str(item).strip()
            for item in request.selected_item_keys
            if str(item).strip()
        ]
        if not selected_item_keys:
            selected_item_keys = self._default_selected_keys(run)
        if not selected_item_keys:
            raise ValueError("No candidate materials are available for project creation.")

        project = self.orchestrator.create_from_rpa_feed(
            CreateProjectFromFeedRequest(
                feed_path=str(feed_path),
                title=request.title,
                mode=request.mode or job.mode,
                target_duration_seconds=request.target_duration_seconds or job.target_duration_seconds,
                aspect_ratio=request.aspect_ratio or job.aspect_ratio,
                plan_mode=request.plan_mode or job.fetch.plan_mode,
                render_preview_bundle=request.render_preview_bundle,
                selected_item_keys=selected_item_keys,
            )
        )

        should_auto_render = job.render.auto_render if request.auto_render is None else request.auto_render
        if should_auto_render:
            project = self.orchestrator.render_project(
                project.project_id,
                RenderProjectRequest(
                    preferred_voice=request.preferred_voice or job.render.preferred_voice,
                    publish_mode=request.publish_mode or job.render.publish_mode,
                    render_mode=request.render_mode or job.render.render_mode,
                    aspect_ratio=request.aspect_ratio or job.aspect_ratio,
                    reference_image_path=request.reference_image_path or job.render.reference_image_path,
                ),
            )

        updated_job = job.model_copy(
            update={
                "last_project_id": project.project_id,
                "last_run_status": "success",
                "last_error": "",
            }
        )
        self.database.save_automation_job(updated_job)
        return project

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
        candidate_items: list[AutomationCandidateItem] = []
        new_item_count = 0
        duplicate_item_count = 0
        feed_path = fetch_dir / "fetched_feed.json"
        seen_item_keys = list(job.seen_item_keys)

        try:
            config = AgentConfig(
                duration_seconds=job.target_duration_seconds,
                model_mode=job.fetch.plan_mode,
                source_set=job.fetch.source_set,
                focus_topics=tuple(job.fetch.focus_topics),
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
            if fetched_item_count == 0 or not feed_path.exists():
                raise RuntimeError("No grid news items were fetched for this automation job.")

            candidate_items, new_item_keys, duplicate_item_count = self._build_candidates(items, job.seen_item_keys)
            self._ensure_feed_candidate_keys(feed_path, items)
            new_item_count = len(new_item_keys)
            seen_item_keys = self._merge_seen_item_keys(job.seen_item_keys, [item.candidate_key for item in candidate_items])

            if new_item_count:
                notes.append(f"Retained {new_item_count} new candidate materials for this run.")
            else:
                notes.append("No new candidate materials were found; all fetched items matched recent history.")

            self.database.save_automation_job(
                job.model_copy(
                    update={
                        "last_run_at": started_at,
                        "last_project_id": project_id,
                        "last_run_status": "running",
                        "last_error": "",
                        "latest_feed_path": str(feed_path),
                        "latest_candidate_count": len(candidate_items),
                        "latest_new_item_count": new_item_count,
                        "seen_item_keys": seen_item_keys,
                    }
                )
            )

            auto_selected_keys = self._default_selected_keys_from_candidates(candidate_items)
            if auto_selected_keys:
                project = self.orchestrator.create_from_rpa_feed(
                    CreateProjectFromFeedRequest(
                        feed_path=str(feed_path),
                        title=None,
                        mode=job.mode,
                        target_duration_seconds=job.target_duration_seconds,
                        aspect_ratio=job.aspect_ratio,
                        plan_mode=job.fetch.plan_mode,
                        render_preview_bundle=True,
                        selected_item_keys=auto_selected_keys,
                    )
                )
                project_id = project.project_id

                self.database.save_automation_job(
                    job.model_copy(
                        update={
                            "last_run_at": started_at,
                            "last_project_id": project_id,
                            "last_run_status": "running",
                            "last_error": "",
                            "latest_feed_path": str(feed_path),
                            "latest_candidate_count": len(candidate_items),
                            "latest_new_item_count": new_item_count,
                            "seen_item_keys": seen_item_keys,
                        }
                    )
                )

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
            else:
                notes.append("Skipped default project creation because there were no fresh candidate materials to use.")

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
                feed_path=str(feed_path),
                fetched_item_count=fetched_item_count,
                new_item_count=new_item_count,
                duplicate_item_count=duplicate_item_count,
                candidates=candidate_items,
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
                        "latest_feed_path": str(feed_path),
                        "latest_candidate_count": len(candidate_items),
                        "latest_new_item_count": new_item_count,
                        "seen_item_keys": seen_item_keys,
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
                feed_path=str(feed_path),
                fetched_item_count=fetched_item_count,
                new_item_count=new_item_count,
                duplicate_item_count=duplicate_item_count,
                candidates=candidate_items,
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
                        "latest_feed_path": str(feed_path),
                        "latest_candidate_count": len(candidate_items),
                        "latest_new_item_count": new_item_count,
                        "seen_item_keys": seen_item_keys,
                    }
                )
            )
            raise

    def _build_candidates(
        self,
        items: list,
        seen_item_keys: list[str],
    ) -> tuple[list[AutomationCandidateItem], list[str], int]:
        seen = {str(item).strip() for item in seen_item_keys if str(item).strip()}
        run_seen: set[str] = set()
        duplicate_count = 0
        candidates: list[AutomationCandidateItem] = []

        ranked_items = sorted(items, key=score_news, reverse=True)
        for item in ranked_items:
            candidate_key = self._candidate_key_for_item(item)
            if candidate_key in run_seen:
                duplicate_count += 1
                continue
            run_seen.add(candidate_key)
            is_new = candidate_key not in seen
            if not is_new:
                duplicate_count += 1

            candidates.append(
                AutomationCandidateItem(
                    candidate_key=candidate_key,
                    title=item.title,
                    source=item.source,
                    summary=item.summary,
                    published_at=item.published_at,
                    url=item.url,
                    tags=list(item.tags),
                    content_category=item.content_category,
                    reliability_score=item.reliability_score,
                    hotness_score=item.hotness_score,
                    score=score_news(item),
                    is_new=is_new,
                )
            )

        new_item_keys = [item.candidate_key for item in candidates if item.is_new]
        return candidates, new_item_keys, duplicate_count

    def _candidate_key_for_item(self, item) -> str:
        if getattr(item, "dedupe_key", ""):
            return str(item.dedupe_key)
        if getattr(item, "url", ""):
            return f"url:{item.url}"
        return f"{item.source}|{item.title}"

    def _ensure_feed_candidate_keys(self, feed_path: Path, items: list) -> None:
        payload = json.loads(feed_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict):
            records = payload.get("items", [])
        else:
            return

        changed = False
        keyed_items = [
            (self._candidate_key_for_item(item), item)
            for item in items
        ]
        for record in records:
            if not isinstance(record, dict):
                continue
            if str(record.get("dedupe_key", "")).strip():
                continue
            for candidate_key, item in keyed_items:
                same_url = record.get("url") and record.get("url") == getattr(item, "url", "")
                same_title = record.get("title") == getattr(item, "title", "")
                same_source = record.get("source") == getattr(item, "source", "")
                if same_url or (same_title and same_source):
                    record["dedupe_key"] = candidate_key
                    changed = True
                    break

        if changed:
            feed_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _default_selected_keys(self, run: AutomationRunRecord) -> list[str]:
        return self._default_selected_keys_from_candidates(run.candidates)

    def _default_selected_keys_from_candidates(
        self,
        candidates: list[AutomationCandidateItem],
        limit: int = 6,
    ) -> list[str]:
        preferred = [item.candidate_key for item in candidates if item.is_new]
        if preferred:
            return preferred[:limit]
        return [item.candidate_key for item in candidates[:limit]]

    def _merge_seen_item_keys(self, existing: list[str], incoming: list[str], limit: int = 500) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for key in [*existing, *incoming]:
            normalized = str(key).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
        return merged[-limit:]

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
