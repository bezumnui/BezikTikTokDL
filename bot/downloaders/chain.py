import logging
from collections.abc import Sequence
from pathlib import Path

from ..models import DownloadedPost, DownloadError, MediaTooLarge
from .base import Downloader

log = logging.getLogger(__name__)


class FallbackDownloader:
    """Tries the primary downloader, then each fallback in order, until one succeeds."""

    name = "fallback"

    def __init__(self, downloaders: Sequence[Downloader]):
        if not downloaders:
            raise ValueError("at least one downloader is required")
        self._downloaders = tuple(downloaders)

    def describe(self) -> str:
        primary, *fallbacks = (d.name for d in self._downloaders)
        return " -> ".join([f"{primary} (primary)", *(f"{name} (fallback)" for name in fallbacks)])

    async def download(self, url: str, workdir: Path) -> DownloadedPost:
        errors: list[str] = []
        for idx, downloader in enumerate(self._downloaders):
            try:
                post = await downloader.download(url, workdir)
            except MediaTooLarge:
                raise
            except Exception as e:
                errors.append(f"{downloader.name}: {e}")
                following = self._downloaders[idx + 1:]
                if following:
                    log.warning("%s failed for %s: %s; using fallback %s", downloader.name, url, e, following[0].name)
                else:
                    log.error("%s failed for %s: %s; no fallbacks left", downloader.name, url, e)
                continue
            if idx:
                log.warning("downloaded %s via fallback %s", url, downloader.name)
            return post
        raise DownloadError("; ".join(errors))
