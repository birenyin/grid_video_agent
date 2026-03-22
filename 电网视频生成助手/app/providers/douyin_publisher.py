from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.models.content import ContentSummary, PublishPackage, ScriptDraft
from app.providers.base import PublishingProvider
from app.utils.files import write_json


class DouyinPublisher(PublishingProvider):
    name = "douyin_publisher"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def export(
        self,
        script: ScriptDraft,
        summary: ContentSummary,
        final_video_path: Path,
        cover_path: Path,
        output_dir: Path,
        publish_mode: str,
    ) -> PublishPackage:
        hashtags = self._build_hashtags(summary)
        payload = {
            "title": script.title[:30],
            "description": f"{summary.summary}\n\n{' '.join(hashtags)}",
            "hashtags": hashtags,
            "video_path": str(final_video_path),
            "cover_path": str(cover_path),
            "publish_mode": publish_mode,
            "oauth": {
                "client_key_set": bool(self.settings.douyin_client_key),
                "client_secret_set": bool(self.settings.douyin_client_secret),
                "enable_real_publish": self.settings.enable_real_publish,
            },
            "provider": self.name,
            "todo": "OAuth exchange and real publish flow should be added after final account approval.",
        }
        payload_path = write_json(output_dir / "publish_payload.json", payload)
        return PublishPackage(
            provider_name=self.name,
            title=payload["title"],
            description=payload["description"],
            hashtags=hashtags,
            video_path=str(final_video_path),
            cover_path=str(cover_path),
            publish_mode=publish_mode,
            payload_path=str(payload_path),
            raw_payload=payload,
        )

    def _build_hashtags(self, summary: ContentSummary) -> list[str]:
        tags = ["#电网", "#电力行业"]
        text = " ".join(summary.key_facts + summary.bullet_points)
        if "调度" in text:
            tags.append("#调度")
        if "市场" in text:
            tags.append("#电力市场")
        if "新能源" in text:
            tags.append("#新能源")
        if "保供" in text:
            tags.append("#保供")
        return tags[:6]
