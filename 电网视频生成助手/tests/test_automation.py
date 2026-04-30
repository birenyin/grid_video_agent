from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.deps import get_automation_service, get_orchestrator
from app.core.database import Database
from app.main import create_app
from app.models.automation import AutomationJobStatus, CreateAutomationJobRequest, CreateAutomationProjectRequest
from app.models.project import ProjectStatus
from app.services.automation_service import AutomationService
from app.services.project_service import ProjectOrchestrator
from src.grid_video_agent.models import GridNewsItem
from tests.helpers import build_test_settings, workspace_tempdir


def fake_fetch_latest_grid_items(config, output_dir, source_set=None, per_source_limit=None, total_limit=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "items": [
            {
                "source": "国家能源局",
                "title": "电网调度协同能力提升",
                "summary": "国家能源局强调调度、保供和新能源消纳协同推进。",
                "published_at": "2026-03-22 09:00:00",
                "url": "https://example.com/nea/grid-01",
                "tags": ["调度", "保供", "新能源"],
                "content": "国家能源局强调调度、保供和新能源消纳协同推进。",
            },
            {
                "source": "南方电网",
                "title": "源网荷储协同迎峰度夏",
                "summary": "南方电网发布源网荷储协同案例，提升系统调节能力。",
                "published_at": "2026-03-22 11:00:00",
                "url": "https://example.com/csg/grid-02",
                "tags": ["源网荷储", "保供"],
                "content": "南方电网发布源网荷储协同案例，提升系统调节能力。",
            },
        ]
    }
    (output_dir / "fetched_feed.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    items = [
        GridNewsItem(
            source="国家能源局",
            title="电网调度协同能力提升",
            summary="国家能源局强调调度、保供和新能源消纳协同推进。",
            published_at="2026-03-22 09:00:00",
            url="https://example.com/nea/grid-01",
            tags=["调度", "保供", "新能源"],
            content="国家能源局强调调度、保供和新能源消纳协同推进。",
            source_type="institution",
            content_category="news",
            reliability_score=95,
            hotness_score=88,
            dedupe_key="a1",
        ),
        GridNewsItem(
            source="南方电网",
            title="源网荷储协同迎峰度夏",
            summary="南方电网发布源网荷储协同案例，提升系统调节能力。",
            published_at="2026-03-22 11:00:00",
            url="https://example.com/csg/grid-02",
            tags=["源网荷储", "保供"],
            content="南方电网发布源网荷储协同案例，提升系统调节能力。",
            source_type="official",
            content_category="news",
            reliability_score=93,
            hotness_score=86,
            dedupe_key="a2",
        ),
    ]
    return items, ["抓取成功：2 条资讯"]


class AutomationServiceTests(unittest.TestCase):
    def test_automation_job_can_fetch_create_and_render_project(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            database = Database(settings.database_path)
            orchestrator = ProjectOrchestrator(settings=settings, database=database)
            service = AutomationService(settings=settings, database=database, orchestrator=orchestrator)

            job = service.create_job(
                CreateAutomationJobRequest(
                    name="自动电网日报",
                    interval_minutes=30,
                    auto_render=True,
                    render_mode="image_audio",
                    aspect_ratio="16:9",
                )
            )

            with patch("app.services.automation_service.fetch_latest_grid_items", side_effect=fake_fetch_latest_grid_items):
                run = service.run_job_now(job.job_id)

            self.assertEqual(run.status.value, "success")
            self.assertIsNotNone(run.project_id)
            project = database.get_project(run.project_id)
            assert project is not None
            self.assertEqual(project.status, ProjectStatus.rendered)
            self.assertTrue(Path(project.artifacts.composition.video_path).exists())  # type: ignore[union-attr]

            updated_job = service.get_job_or_raise(job.job_id)
            self.assertEqual(updated_job.last_project_id, run.project_id)
            self.assertEqual(updated_job.last_run_status, "success")
            self.assertEqual(len(service.list_runs(job.job_id)), 1)
            self.assertEqual(run.new_item_count, 2)
            self.assertEqual(len(run.candidates), 2)
            self.assertTrue(Path(run.feed_path).exists())

    def test_automation_job_can_create_project_from_selected_candidates(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            database = Database(settings.database_path)
            orchestrator = ProjectOrchestrator(settings=settings, database=database)
            service = AutomationService(settings=settings, database=database, orchestrator=orchestrator)

            job = service.create_job(
                CreateAutomationJobRequest(
                    name="候选资料池任务",
                    interval_minutes=30,
                    auto_render=False,
                    render_mode="image_audio",
                    aspect_ratio="16:9",
                )
            )

            with patch("app.services.automation_service.fetch_latest_grid_items", side_effect=fake_fetch_latest_grid_items):
                run = service.run_job_now(job.job_id)

            self.assertIsNotNone(run.project_id)
            created = service.create_project_from_run(
                job.job_id,
                CreateAutomationProjectRequest(
                    run_id=run.run_id,
                    selected_item_keys=["a2"],
                    auto_render=False,
                ),
            )

            self.assertEqual(created.status, ProjectStatus.draft)
            self.assertEqual(created.content_input.source_type, "rpa_feed")
            self.assertIn("源网荷储协同", created.script.full_script)  # type: ignore[union-attr]
            self.assertTrue(Path(created.artifacts.news_plan_path).exists())

    def test_queue_due_jobs_only_schedules_active_due_jobs(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            database = Database(settings.database_path)
            orchestrator = ProjectOrchestrator(settings=settings, database=database)
            service = AutomationService(settings=settings, database=database, orchestrator=orchestrator)

            due_job = service.create_job(CreateAutomationJobRequest(name="到期任务", interval_minutes=15))
            paused_job = service.create_job(CreateAutomationJobRequest(name="暂停任务", interval_minutes=15))
            future_job = service.create_job(CreateAutomationJobRequest(name="未来任务", interval_minutes=15))

            past_iso = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            future_iso = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            database.save_automation_job(due_job.model_copy(update={"next_run_at": past_iso}))
            database.save_automation_job(
                paused_job.model_copy(update={"status": AutomationJobStatus.paused, "next_run_at": past_iso})
            )
            database.save_automation_job(future_job.model_copy(update={"next_run_at": future_iso}))

            queued_calls: list[tuple[str, str]] = []

            def fake_run_async(job_id: str, trigger_type: str = "schedule") -> bool:
                queued_calls.append((job_id, trigger_type))
                return True

            with patch.object(service, "run_job_async", side_effect=fake_run_async):
                queued = service.queue_due_jobs()

            self.assertEqual(queued, [due_job.job_id])
            self.assertEqual(queued_calls, [(due_job.job_id, "schedule")])


class AutomationRouteTests(unittest.TestCase):
    def _build_client(self, temp_dir: Path) -> tuple[TestClient, AutomationService]:
        settings = build_test_settings(temp_dir)
        database = Database(settings.database_path)
        orchestrator = ProjectOrchestrator(settings=settings, database=database)
        service = AutomationService(settings=settings, database=database, orchestrator=orchestrator)
        app = create_app()
        app.dependency_overrides[get_orchestrator] = lambda: orchestrator
        app.dependency_overrides[get_automation_service] = lambda: service
        return TestClient(app), service

    def test_automation_routes_create_run_and_get_job(self) -> None:
        with workspace_tempdir() as temp_dir:
            client, _ = self._build_client(Path(temp_dir))

            create_response = client.post(
                "/automation/jobs",
                json={
                    "name": "自动电网速递",
                    "interval_minutes": 60,
                    "source_set": "mixed",
                    "plan_mode": "rule",
                    "auto_render": True,
                    "render_mode": "image_audio",
                },
            )
            self.assertEqual(create_response.status_code, 200)
            job_id = create_response.json()["job_id"]

            with patch("app.services.automation_service.fetch_latest_grid_items", side_effect=fake_fetch_latest_grid_items):
                run_response = client.post(f"/automation/jobs/{job_id}/run")
            self.assertEqual(run_response.status_code, 200)
            self.assertEqual(run_response.json()["status"], "success")

            detail_response = client.get(f"/automation/jobs/{job_id}")
            self.assertEqual(detail_response.status_code, 200)
            self.assertEqual(detail_response.json()["job"]["job_id"], job_id)
            self.assertEqual(len(detail_response.json()["runs"]), 1)
            self.assertGreaterEqual(detail_response.json()["runs"][0]["new_item_count"], 1)
            self.assertEqual(len(detail_response.json()["runs"][0]["candidates"]), 2)

            create_project_response = client.post(
                f"/automation/jobs/{job_id}/projects",
                json={
                    "run_id": detail_response.json()["runs"][0]["run_id"],
                    "selected_item_keys": ["a1"],
                    "auto_render": False,
                },
            )
            self.assertEqual(create_project_response.status_code, 200)
            self.assertEqual(create_project_response.json()["status"], "draft")

            pause_response = client.post(f"/automation/jobs/{job_id}/status", json={"status": "paused"})
            self.assertEqual(pause_response.status_code, 200)
            self.assertEqual(pause_response.json()["status"], "paused")


if __name__ == "__main__":
    unittest.main()
