"""Real downloads from TikTok. Run with: pytest -m live"""
import subprocess

import pytest

from bot.downloaders import PageDataDownloader, TikTokDLDownloader
from bot.models import MediaKind

URLS = ["https://vt.tiktok.com/ZSgQ4q459", "https://vt.tiktok.com/ZSbYPdRrr", "https://vt.tiktok.com/ZSbRpvQxw"]

pytestmark = pytest.mark.live


def assert_valid_video(path):
    """Decode the whole file without playing it; any error means the file is broken."""
    probe = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                           capture_output=True, text=True, timeout=120)
    assert probe.returncode == 0 and not probe.stderr.strip(), probe.stderr


@pytest.mark.parametrize("url", URLS)
async def test_page_data_downloads_valid_video(url, tmp_path):
    post = await PageDataDownloader().download(url, tmp_path)
    assert post.kind is MediaKind.VIDEO and post.post_id.isdigit()
    assert post.files[0].stat().st_size > 10_000
    assert_valid_video(post.files[0])


@pytest.mark.xfail(reason="TikTok stopped issuing /api/reflow/item/detail/ for many posts", strict=False)
@pytest.mark.parametrize("url", URLS[:1])
async def test_tiktokdl_library(url, tmp_path):
    post = await TikTokDLDownloader().download(url, tmp_path)
    assert_valid_video(post.files[0])
