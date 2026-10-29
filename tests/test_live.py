"""Real downloads from TikTok. Run with: pytest -m live"""
import subprocess

import pytest

from bot.downloaders import FirefoxDownloader, HttpDownloader
from bot.models import MediaKind

URLS = ["https://vt.tiktok.com/ZSgQ4q459", "https://vt.tiktok.com/ZSbYPdRrr", "https://vt.tiktok.com/ZSbRpvQxw"]

pytestmark = pytest.mark.live


def assert_valid_video(path):
    """Decode the whole file without playing it; any error means the file is broken."""
    probe = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                           capture_output=True, text=True, timeout=120)
    assert probe.returncode == 0 and not probe.stderr.strip(), probe.stderr


@pytest.mark.parametrize("downloader", [HttpDownloader, FirefoxDownloader], ids=lambda d: d.name)
@pytest.mark.parametrize("url", URLS)
async def test_downloads_valid_video(downloader, url, tmp_path):
    post = await downloader().download(url, tmp_path)
    assert post.kind is MediaKind.VIDEO and post.post_id.isdigit()
    assert post.files[0].stat().st_size > 10_000
    assert_valid_video(post.files[0])
