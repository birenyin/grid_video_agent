from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.database import Database
from app.services.automation_service import AutomationScheduler, AutomationService
from app.services.project_service import ProjectOrchestrator


@lru_cache(maxsize=1)
def get_orchestrator() -> ProjectOrchestrator:
    settings = get_settings()
    return ProjectOrchestrator(settings=settings, database=Database(settings.database_path))


@lru_cache(maxsize=1)
def get_automation_service() -> AutomationService:
    settings = get_settings()
    database = Database(settings.database_path)
    return AutomationService(settings=settings, database=database, orchestrator=get_orchestrator())


@lru_cache(maxsize=1)
def get_automation_scheduler() -> AutomationScheduler:
    settings = get_settings()
    return AutomationScheduler(get_automation_service(), poll_seconds=settings.automation_poll_seconds)
