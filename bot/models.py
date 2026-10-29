from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MediaKind(str, Enum):
    VIDEO = "video"
    PHOTOS = "photos"


class DownloadError(Exception):
    """The post could not be fetched or saved."""


class MediaTooLarge(DownloadError):
    """The file exceeds the Bot API upload limit."""


@dataclass(frozen=True)
class DownloadedPost:
    post_id: str
    author: str
    kind: MediaKind
    files: tuple[Path, ...]
    description: str = ""


@dataclass(frozen=True)
class PublishedPost:
    """A post already uploaded to Telegram, addressable by reusable file_ids."""

    post_id: str
    author: str
    kind: MediaKind
    file_ids: tuple[str, ...]
    description: str = ""

    @property
    def caption(self) -> str:
        return f"@{self.author}" if self.author else ""
