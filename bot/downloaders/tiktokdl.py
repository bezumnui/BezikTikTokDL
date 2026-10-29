import asyncio
from pathlib import Path

from tiktokdl.download_post import get_post
from tiktokdl.post_data import TikTokSlide, TikTokVideo

from ..models import DownloadedPost, DownloadError, MediaKind


def to_downloaded_post(post: TikTokVideo | TikTokSlide) -> DownloadedPost:
    if isinstance(post, TikTokSlide):
        kind, files = MediaKind.PHOTOS, tuple(Path(p) for p in post.images or ())
    else:
        kind, files = MediaKind.VIDEO, (Path(post.file_path),) if post.file_path else ()
    if not files:
        raise DownloadError("TikTokDL returned no files")
    return DownloadedPost(
        post_id=str(post.post_id),
        author=post.author_username or "",
        kind=kind,
        files=files,
        description=post.post_description or "",
    )


class TikTokDLDownloader:
    """Adapter over Fluxticks/TikTokDL (`tiktok-dlpy`)."""

    name = "tiktokdl"

    def __init__(self, request_timeout: float = 10.0, retries: int = 0):
        self._request_timeout_ms = request_timeout * 1000
        self._retries = retries

    async def download(self, url: str, workdir: Path) -> DownloadedPost:
        # The library downloads with blocking `requests`, so keep it off the bot's event loop.
        post = await asyncio.to_thread(asyncio.run, get_post(
            url,
            headless=True,
            retries=self._retries,
            request_timeout=self._request_timeout_ms,
            download_path=str(workdir),
        ))
        return to_downloaded_post(post)
