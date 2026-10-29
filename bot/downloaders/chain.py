import logging
from collections.abc import Sequence
from pathlib import Path

from ..models import DownloadedPost, DownloadError, MediaTooLarge
from .base import Downloader

log = logging.getLogger(__name__)


class FallbackDownloader:
    """Tries each downloader in order until one succeeds."""

    name = "fallback"

    def __init__(self, downloaders: Sequence[Downloader]):
        if not downloaders:
            raise ValueError("at least one downloader is required")
        self._downloaders = tuple(downloaders)

    async def download(self, url: str, workdir: Path) -> DownloadedPost:
        errors: list[str] = []
        for downloader in self._downloaders:
            try:
                return await downloader.download(url, workdir)
            except MediaTooLarge:
                raise
            except Exception as e:
                log.warning("%s failed for %s: %s", downloader.name, url, e)
                errors.append(f"{downloader.name}: {e}")
        raise DownloadError("; ".join(errors))
