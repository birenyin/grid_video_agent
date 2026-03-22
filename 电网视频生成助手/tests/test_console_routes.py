from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.deps import get_orchestrator
from app.core.database import Database
from app.main import create_app
from app.services.ingestion_service import IngestionService
from app.services.project_service import ProjectOrchestrator
from tests.helpers import build_test_settings, workspace_tempdir


class ConsoleRouteTests(unittest.TestCase):
    def _build_client(self, temp_dir: Path) -> tuple[TestClient, ProjectOrchestrator]:
        settings = build_test_settings(temp_dir)
        orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
        app = create_app()
        app.dependency_overrides[get_orchestrator] = lambda: orchestrator
        return TestClient(app), orchestrator

    def test_home_route_serves_console(self) -> None:
        with workspace_tempdir() as temp_dir:
            client, _ = self._build_client(Path(temp_dir))
            response = client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertIn("电网视频生成智能体", response.text)
            self.assertIn("RPA Feed", response.text)

    def test_project_list_and_detail_routes_return_created_project(self) -> None:
        with workspace_tempdir() as temp_dir:
            client, _ = self._build_client(Path(temp_dir))
            create_response = client.post(
                "/projects/create_from_script",
                json={
                    "title": "国家电网一分钟科普",
                    "full_script": (
                        "家人们，你们知道电是怎么从电厂安全稳定地到你家的吗？"
                        "国家电网负责把电从电厂送到千家万户，调度中心则持续平衡负荷和频率。"
                    ),
                    "mode": "explain_mode",
                    "target_duration_seconds": 30,
                    "aspect_ratio": "16:9",
                },
            )
            self.assertEqual(create_response.status_code, 200)
            project_id = create_response.json()["project_id"]

            list_response = client.get("/projects")
            self.assertEqual(list_response.status_code, 200)
            self.assertEqual(len(list_response.json()), 1)
            self.assertEqual(list_response.json()[0]["project_id"], project_id)

            detail_response = client.get(f"/projects/{project_id}")
            self.assertEqual(detail_response.status_code, 200)
            detail_payload = detail_response.json()
            self.assertEqual(detail_payload["project"]["project_id"], project_id)
            self.assertIn("asset_links", detail_payload)

    def test_create_from_url_route_uses_fetched_page_text(self) -> None:
        with workspace_tempdir() as temp_dir:
            client, _ = self._build_client(Path(temp_dir))
            with patch.object(
                IngestionService,
                "fetch_url_content",
                return_value=(
                    "网页抓取标题",
                    (
                        "国家电网负责把电力安全稳定送到用户侧。"
                        "调度中心会持续监测负荷、频率和新能源波动，"
                        "并通过源网荷储协同提高系统运行效率。"
                    ),
                ),
            ):
                response = client.post(
                    "/projects/create_from_url",
                    json={
                        "source_url": "https://example.com/grid-news",
                        "mode": "news_mode",
                        "target_duration_seconds": 45,
                        "aspect_ratio": "9:16",
                    },
                )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["summary"]["title"], "网页抓取标题")
            self.assertEqual(payload["status"], "draft")

    def test_create_from_rpa_feed_route_generates_newsroom_artifacts(self) -> None:
        with workspace_tempdir() as temp_dir:
            client, _ = self._build_client(Path(temp_dir))
            feed_path = Path(__file__).resolve().parents[1] / "data" / "input" / "rpa_raw_feed.json"
            response = client.post(
                "/projects/create_from_rpa_feed",
                json={
                    "feed_path": str(feed_path),
                    "target_duration_seconds": 60,
                    "aspect_ratio": "9:16",
                    "plan_mode": "rule",
                    "render_preview_bundle": True,
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            artifacts = payload["artifacts"]
            self.assertTrue(Path(artifacts["news_plan_path"]).exists())
            self.assertTrue(Path(artifacts["selected_sources_path"]).exists())
            self.assertTrue(Path(artifacts["preview_cover_path"]).exists())


if __name__ == "__main__":
    unittest.main()
