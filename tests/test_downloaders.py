import json
from datetime import datetime, timezone

import pytest
from tiktokdl.post_data import TikTokSlide, TikTokVideo

from bot.downloaders import FallbackDownloader
from bot.downloaders.page_data import parse_page_data
from bot.downloaders.tiktokdl import to_downloaded_post
from bot.models import DownloadError, MediaKind, MediaTooLarge
from tests.conftest import FakeDownloader


def page(item: dict) -> str:
    return json.dumps({"__DEFAULT_SCOPE__": {"webapp.video-detail": {"itemInfo": {"itemStruct": item}}}})


def test_parse_video():
    info = parse_page_data(page({
        "id": "7699678984417627423", "desc": "#tag", "author": {"uniqueId": "david"},
        "video": {"playAddr": "https://v16/play.mp4", "downloadAddr": "https://v16/dl.mp4"},
    }))
    assert info.kind is MediaKind.VIDEO
    assert info.post_id == "7699678984417627423"
    assert info.author == "david"
    assert info.media_urls == ("https://v16/play.mp4",)


def test_parse_video_falls_back_to_download_addr():
    info = parse_page_data(page({"id": "1", "video": {"playAddr": "", "downloadAddr": "https://dl"}}))
    assert info.media_urls == ("https://dl",)


def test_parse_slideshow():
    images = [{"imageURL": {"urlList": [f"https://img/{i}.jpeg", "mirror"]}} for i in range(3)]
    info = parse_page_data(page({"id": "1", "author": {"uniqueId": "a"}, "imagePost": {"images": images}}))
    assert info.kind is MediaKind.PHOTOS
    assert info.media_urls == ("https://img/0.jpeg", "https://img/1.jpeg", "https://img/2.jpeg")


@pytest.mark.parametrize("raw", ["", "not json", json.dumps({"__DEFAULT_SCOPE__": {}}),
                                 page({"id": "1", "video": {}})])
def test_parse_rejects_bad_data(raw):
    with pytest.raises(DownloadError):
        parse_page_data(raw)


def _post_fields():
    return dict(
        url="u", post_id="9", author_username="neo", author_display_name="Neo", author_avatar="", author_url="",
        author_id="1", post_download_setting=-1, post_description="d", timestamp=datetime.now(timezone.utc),
        like_count=0, share_count=0, comment_count=0, view_count=0,
    )


def test_tiktokdl_video_mapping():
    post = to_downloaded_post(TikTokVideo(**_post_fields(), video_thumbnail="", download_url="", file_path="/x/9.mp4"))
    assert post.kind is MediaKind.VIDEO
    assert [str(f) for f in post.files] == ["/x/9.mp4"]
    assert post.author == "neo"


def test_tiktokdl_slide_mapping():
    post = to_downloaded_post(TikTokSlide(**_post_fields(), images=["/x/1.jpeg", "/x/2.jpeg"]))
    assert post.kind is MediaKind.PHOTOS
    assert len(post.files) == 2


def test_tiktokdl_without_files_fails():
    with pytest.raises(DownloadError):
        to_downloaded_post(TikTokVideo(**_post_fields(), video_thumbnail="", download_url=""))


async def test_fallback_uses_next_on_failure(tmp_path):
    broken, working = FakeDownloader(error=RuntimeError("api changed")), FakeDownloader()
    post = await FallbackDownloader([broken, working]).download("u", tmp_path)
    assert post.post_id == "123"
    assert broken.calls == working.calls == ["u"]


async def test_fallback_stops_at_first_success(tmp_path):
    first, second = FakeDownloader(), FakeDownloader()
    await FallbackDownloader([first, second]).download("u", tmp_path)
    assert second.calls == []


async def test_fallback_all_fail(tmp_path):
    chain = FallbackDownloader([FakeDownloader(error=RuntimeError("a")), FakeDownloader(error=RuntimeError("b"))])
    with pytest.raises(DownloadError, match="a.*b"):
        await chain.download("u", tmp_path)


async def test_fallback_does_not_retry_too_large(tmp_path):
    second = FakeDownloader()
    with pytest.raises(MediaTooLarge):
        await FallbackDownloader([FakeDownloader(error=MediaTooLarge("big")), second]).download("u", tmp_path)
    assert second.calls == []


def test_fallback_requires_downloaders():
    with pytest.raises(ValueError):
        FallbackDownloader([])
