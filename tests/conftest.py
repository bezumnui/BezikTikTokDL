from pathlib import Path

import pytest

from bot.models import DownloadedPost, MediaKind, PublishedPost


class FakeDownloader:
    name = "fake"

    def __init__(self, kind: MediaKind = MediaKind.VIDEO, size: int = 10, delay: float = 0, error: Exception | None = None):
        self.kind, self.size, self.delay, self.error = kind, size, delay, error
        self.calls: list[str] = []

    async def download(self, url: str, workdir: Path) -> DownloadedPost:
        import asyncio

        self.calls.append(url)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        count = 1 if self.kind is MediaKind.VIDEO else 3
        files = []
        for i in range(count):
            path = workdir / f"{i}.bin"
            path.write_bytes(b"x" * self.size)
            files.append(path)
        return DownloadedPost("123", "author", self.kind, tuple(files), "desc")


class FakePublisher:
    def __init__(self):
        self.published: list[DownloadedPost] = []

    async def publish(self, post: DownloadedPost) -> PublishedPost:
        assert all(f.exists() for f in post.files), "files must exist while publishing"
        self.published.append(post)
        ids = tuple(f"id-{i}" for i in range(len(post.files)))
        return PublishedPost(post.post_id, post.author, post.kind, ids, post.description, post.fallback)


class MemoryCache:
    def __init__(self):
        self.data: dict[str, PublishedPost] = {}

    def get(self, key):
        return self.data.get(key)

    def put(self, keys, post):
        for key in (*keys, post.post_id):
            self.data[key] = post


@pytest.fixture
def publisher():
    return FakePublisher()


@pytest.fixture
def cache():
    return MemoryCache()
