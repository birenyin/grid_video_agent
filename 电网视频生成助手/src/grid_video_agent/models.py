from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class GridNewsItem:
    source: str
    title: str
    summary: str
    published_at: str
    url: str
    tags: list[str] = field(default_factory=list)
    content: str = ""
    source_type: str = "official"
    content_category: str = "news"
    reliability_score: int = 80
    hotness_score: int = 60
    dedupe_key: str = ""
    compliance_flags: list[str] = field(default_factory=list)


@dataclass
class VideoSegment:
    scene: int
    visual: str
    narration: str
    subtitle: str


@dataclass
class VideoPlan:
    title: str
    cover_text: str
    intro_hook: str
    takeaway: str
    hashtags: list[str]
    selected_news: list[dict]
    segments: list[VideoSegment]
    generation_mode: str = "rule"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["segments"] = [asdict(segment) for segment in self.segments]
        return data


@dataclass
class PipelineReport:
    total_items: int
    selected_items: int
    dropped_items: int
    duplicate_items: int
    risky_items: int
    output_files: list[str]
    input_mode: str = "file"
    source_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
