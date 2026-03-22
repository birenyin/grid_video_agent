from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.content import (
    ContentInput,
    ContentSummary,
    ImageGenerationResult,
    PublishPackage,
    ScriptDraft,
    StoryboardShot,
    SubtitleResult,
    TTSResult,
    VideoGenerationResult,
    VoiceSynthesisOptions,
)


class ProviderError(RuntimeError):
    """Base provider exception."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a real provider is selected but required credentials are missing."""


class ProviderContractError(ProviderError):
    """Raised when a provider response cannot be mapped into the project contract."""


class BaseProvider(ABC):
    name: str


class LLMProvider(BaseProvider, ABC):
    @abstractmethod
    def summarize_content(self, content: ContentInput) -> ContentSummary:
        raise NotImplementedError

    @abstractmethod
    def generate_script(self, content: ContentInput, summary: ContentSummary) -> ScriptDraft:
        raise NotImplementedError


class VideoGenerationProvider(BaseProvider, ABC):
    @abstractmethod
    def text_to_video(self, shot: StoryboardShot, output_dir: Path) -> VideoGenerationResult:
        raise NotImplementedError

    @abstractmethod
    def image_to_video(self, shot: StoryboardShot, image_path: Path, output_dir: Path) -> VideoGenerationResult:
        raise NotImplementedError


class ImageGenerationProvider(BaseProvider, ABC):
    @abstractmethod
    def generate(
        self,
        shot: StoryboardShot,
        output_dir: Path,
        reference_image_path: Path,
    ) -> ImageGenerationResult:
        raise NotImplementedError


class TTSProvider(BaseProvider, ABC):
    @abstractmethod
    def synthesize(
        self,
        script: ScriptDraft,
        shots: list[StoryboardShot],
        output_dir: Path,
        options: VoiceSynthesisOptions,
    ) -> TTSResult:
        raise NotImplementedError


class SubtitleProvider(BaseProvider, ABC):
    @abstractmethod
    def generate(self, shots: list[StoryboardShot], output_dir: Path) -> SubtitleResult:
        raise NotImplementedError


class PublishingProvider(BaseProvider, ABC):
    @abstractmethod
    def export(
        self,
        script: ScriptDraft,
        summary: ContentSummary,
        final_video_path: Path,
        cover_path: Path,
        output_dir: Path,
        publish_mode: str,
    ) -> PublishPackage:
        raise NotImplementedError
