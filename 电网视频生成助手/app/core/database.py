from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.models.automation import AutomationJobRecord, AutomationRunRecord
from app.models.project import ProjectRecord


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    attempt_no INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    request_json TEXT,
                    response_json TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_runs (
                    run_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_project(self, project: ProjectRecord) -> None:
        created_at = project.created_at
        updated_at = utc_now_iso()
        payload = project.model_copy(update={"updated_at": updated_at})
        payload_json = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO projects(project_id, status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    status=excluded.status,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    project.project_id,
                    payload.status,
                    payload_json,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()

    def get_project(self, project_id: str) -> ProjectRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return ProjectRecord.model_validate_json(row["payload_json"])

    def list_projects(self, limit: int = 50) -> list[ProjectRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM projects
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [ProjectRecord.model_validate_json(row["payload_json"]) for row in rows]

    def log_provider_attempt(
        self,
        project_id: str,
        provider_name: str,
        action_name: str,
        attempt_no: int,
        status: str,
        request_payload: dict | None = None,
        response_payload: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_attempts(
                    project_id, provider_name, action_name, attempt_no, status,
                    request_json, response_json, error_message, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    provider_name,
                    action_name,
                    attempt_no,
                    status,
                    json.dumps(request_payload, ensure_ascii=False) if request_payload else None,
                    json.dumps(response_payload, ensure_ascii=False) if response_payload else None,
                    error_message,
                    utc_now_iso(),
                ),
            )
            conn.commit()

    def list_provider_attempts(self, project_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT provider_name, action_name, attempt_no, status, request_json,
                       response_json, error_message, created_at
                FROM provider_attempts
                WHERE project_id = ?
                ORDER BY id ASC
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_automation_job(self, job: AutomationJobRecord) -> None:
        created_at = job.created_at
        updated_at = utc_now_iso()
        payload = job.model_copy(update={"updated_at": updated_at})
        payload_json = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO automation_jobs(job_id, status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    job.job_id,
                    payload.status,
                    payload_json,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()

    def get_automation_job(self, job_id: str) -> AutomationJobRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM automation_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return AutomationJobRecord.model_validate_json(row["payload_json"])

    def list_automation_jobs(self, limit: int = 100) -> list[AutomationJobRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM automation_jobs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [AutomationJobRecord.model_validate_json(row["payload_json"]) for row in rows]

    def save_automation_run(self, run: AutomationRunRecord) -> None:
        payload_json = json.dumps(run.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO automation_runs(run_id, job_id, status, payload_json, created_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.job_id,
                    run.status,
                    payload_json,
                    run.started_at,
                    run.finished_at,
                ),
            )
            conn.commit()

    def list_automation_runs(self, job_id: str, limit: int = 30) -> list[AutomationRunRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM automation_runs
                WHERE job_id = ?
                ORDER BY finished_at DESC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
        return [AutomationRunRecord.model_validate_json(row["payload_json"]) for row in rows]
