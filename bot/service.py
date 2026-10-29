import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from .cache import PostCache
from .downloaders import Downloader
from .models import DownloadedPost, DownloadError, MediaTooLarge, PublishedPost
from .publisher import Publisher

log = logging.getLogger(__name__)

BOT_API_UPLOAD_LIMIT = 50 * 1024 * 1024


class MediaService:
    """URL -> Telegram file_ids: cache lookup, de-duplicated download, upload."""

    def __init__(
        self,
        downloader: Downloader,
        publisher: Publisher,
        cache: PostCache,
        work_root: Path,
        max_parallel: int = 2,
        timeout: float = 90,
        max_size: int = BOT_API_UPLOAD_LIMIT,
    ):
        self._downloader = downloader
        self._publisher = publisher
        self._cache = cache
        self._work_root = work_root
        self._limit = asyncio.Semaphore(max_parallel)
        self._timeout = timeout
        self._max_size = max_size
        self._in_flight: dict[str, asyncio.Task[PublishedPost]] = {}

    def cached(self, url: str) -> PublishedPost | None:
        return self._cache.get(url)

    async def get(self, url: str) -> PublishedPost:
        """Cancelling the caller does not cancel the shared download."""
        if post := self._cache.get(url):
            return post
        task = self._in_flight.get(url)
        if task is None:
            task = asyncio.create_task(self._fetch(url))
            self._in_flight[url] = task
            task.add_done_callback(lambda _: self._in_flight.pop(url, None))
        return await asyncio.shield(task)

    async def _fetch(self, url: str) -> PublishedPost:
        async with self._limit:
            self._work_root.mkdir(parents=True, exist_ok=True)
            workdir = Path(tempfile.mkdtemp(dir=self._work_root))
            try:
                try:
                    downloaded = await asyncio.wait_for(self._downloader.download(url, workdir), self._timeout)
                except TimeoutError as e:
                    raise DownloadError("download timed out") from e
                self._check_size(downloaded)
                post = await self._publisher.publish(downloaded)
            finally:
                shutil.rmtree(workdir, ignore_errors=True)
        self._cache.put([url], post)
        log.info("published %s (%s, %d file(s))", post.post_id, post.kind.value, len(post.file_ids))
        return post

    def _check_size(self, post: DownloadedPost) -> None:
        for file in post.files:
            if file.stat().st_size > self._max_size:
                raise MediaTooLarge(f"{file.name} is larger than {self._max_size // (1024 * 1024)} MB")
