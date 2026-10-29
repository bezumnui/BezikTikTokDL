from pathlib import Path
from typing import Protocol

from ..models import DownloadedPost


class Downloader(Protocol):
    name: str

    async def download(self, url: str, workdir: Path) -> DownloadedPost:
        """Save the post's media into workdir. Raises DownloadError on failure."""
