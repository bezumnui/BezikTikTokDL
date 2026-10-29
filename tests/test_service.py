import asyncio

import pytest

from bot.models import DownloadError, MediaKind, MediaTooLarge
from bot.service import MediaService
from tests.conftest import FakeDownloader


def make(tmp_path, downloader, publisher, cache, **kw):
    return MediaService(downloader, publisher, cache, tmp_path / "work", **kw)


async def test_downloads_publishes_and_caches(tmp_path, publisher, cache):
    downloader = FakeDownloader()
    service = make(tmp_path, downloader, publisher, cache)
    post = await service.get("u")
    assert post.file_ids == ("id-0",)
    assert service.cached("u") == post
    assert await service.get("u") == post
    assert downloader.calls == ["u"]


async def test_workdir_is_cleaned(tmp_path, publisher, cache):
    service = make(tmp_path, FakeDownloader(MediaKind.PHOTOS), publisher, cache)
    await service.get("u")
    assert list((tmp_path / "work").iterdir()) == []


async def test_concurrent_requests_share_one_download(tmp_path, publisher, cache):
    downloader = FakeDownloader(delay=0.05)
    service = make(tmp_path, downloader, publisher, cache)
    a, b = await asyncio.gather(service.get("u"), service.get("u"))
    assert a == b
    assert downloader.calls == ["u"]


async def test_cancelled_waiter_does_not_cancel_download(tmp_path, publisher, cache):
    downloader = FakeDownloader(delay=0.1)
    service = make(tmp_path, downloader, publisher, cache)
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(service.get("u"), 0.01)
    post = await service.get("u")
    assert post.post_id == "123"
    assert downloader.calls == ["u"]


async def test_too_large(tmp_path, publisher, cache):
    service = make(tmp_path, FakeDownloader(size=100), publisher, cache, max_size=50)
    with pytest.raises(MediaTooLarge):
        await service.get("u")
    assert publisher.published == []
    assert service.cached("u") is None


async def test_timeout_becomes_download_error(tmp_path, publisher, cache):
    service = make(tmp_path, FakeDownloader(delay=1), publisher, cache, timeout=0.01)
    with pytest.raises(DownloadError):
        await service.get("u")


async def test_failure_is_not_cached_and_can_retry(tmp_path, publisher, cache):
    downloader = FakeDownloader(error=DownloadError("boom"))
    service = make(tmp_path, downloader, publisher, cache)
    with pytest.raises(DownloadError):
        await service.get("u")
    downloader.error = None
    assert (await service.get("u")).post_id == "123"
    assert len(downloader.calls) == 2
