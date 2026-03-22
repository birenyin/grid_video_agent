from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import get_orchestrator
from app.core.database import Database
from app.main import create_app
from app.services.project_service import ProjectOrchestrator
from tests.helpers import build_test_settings, workspace_tempdir


class ApiValidationTests(unittest.TestCase):
    def test_invalid_duration_returns_422(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
            app = create_app()
            app.dependency_overrides[get_orchestrator] = lambda: orchestrator
            client = TestClient(app)

            response = client.post(
                "/projects/create_from_text",
                json={
                    "title": "测试",
                    "content_text": "这是一段足够长的电网内容文本，用于验证接口参数校验逻辑是否正常工作。",
                    "mode": "news_mode",
                    "target_duration_seconds": 10,
                },
            )
            self.assertEqual(response.status_code, 422)

    def test_create_from_script_route_accepts_valid_payload(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
            app = create_app()
            app.dependency_overrides[get_orchestrator] = lambda: orchestrator
            client = TestClient(app)

            response = client.post(
                "/projects/create_from_script",
                json={
                    "title": "国家电网一分钟科普",
                    "full_script": "国家电网负责把电从电厂送到千家万户，调度中心则像一个24小时不停运转的指挥室，持续平衡负荷、频率和新能源波动。",
                    "mode": "explain_mode",
                    "target_duration_seconds": 15,
                },
            )
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
