from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.project import CreateProjectFromScriptRequest, RenderProjectRequest
from app.services.project_service import ProjectOrchestrator


def main() -> None:
    case_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/cases/state_grid_intro_case.json")
    payload = json.loads(case_path.read_text(encoding="utf-8"))

    orchestrator = ProjectOrchestrator()
    project = orchestrator.create_from_script(
        CreateProjectFromScriptRequest(
            title=payload["title"],
            full_script=payload["full_script"],
            mode=payload.get("mode", "explain_mode"),
            target_duration_seconds=payload.get("target_duration_seconds", 60),
            aspect_ratio=payload.get("aspect_ratio", "9:16"),
        )
    )
    rendered = orchestrator.render_project(
        project.project_id,
        RenderProjectRequest(
            preferred_voice=payload.get("preferred_voice", "professional_cn_male"),
            publish_mode="draft",
            render_mode=payload.get("render_mode", "image_audio"),
            aspect_ratio=payload.get("aspect_ratio"),
            reference_image_path=payload.get("reference_image_path"),
        ),
    )

    result = {
        "project_id": rendered.project_id,
        "status": rendered.status.value,
        "working_dir": rendered.artifacts.working_dir,
        "audio_path": rendered.artifacts.voice.audio_path if rendered.artifacts.voice else "",
        "video_path": rendered.artifacts.composition.video_path if rendered.artifacts.composition else "",
        "subtitle_path": rendered.artifacts.subtitles.subtitle_path if rendered.artifacts.subtitles else "",
        "image_count": len(rendered.artifacts.shot_images),
        "first_image_path": rendered.artifacts.shot_images[0].image_path if rendered.artifacts.shot_images else "",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
