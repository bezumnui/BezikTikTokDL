import json
import logging

import pytest
from aiohttp import web

from bot.downloaders import FallbackDownloader, HttpDownloader
from bot.downloaders.tiktok_page import extract_page_data, parse_page_data
from bot.models import DownloadError, MediaKind, MediaTooLarge
from tests.conftest import FakeDownloader


def page_json(item: dict) -> str:
    return json.dumps({"__DEFAULT_SCOPE__": {"webapp.video-detail": {"itemInfo": {"itemStruct": item}}}})


def page_html(item: dict) -> str:
    return (f'<html><head><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">'
            f"{page_json(item)}</script></head></html>")


def test_parse_video():
    info = parse_page_data(page_json({
        "id": "7699678984417627423", "desc": "#tag", "author": {"uniqueId": "david"},
        "video": {"playAddr": "https://v16/play.mp4", "downloadAddr": "https://v16/dl.mp4"},
    }))
    assert info.kind is MediaKind.VIDEO
    assert info.post_id == "7699678984417627423"
    assert info.author == "david"
    assert info.media_urls == ("https://v16/play.mp4",)
    assert info.suffix == ".mp4"


def test_parse_video_falls_back_to_download_addr():
    info = parse_page_data(page_json({"id": "1", "video": {"playAddr": "", "downloadAddr": "https://dl"}}))
    assert info.media_urls == ("https://dl",)


def test_parse_slideshow():
    images = [{"imageURL": {"urlList": [f"https://img/{i}.jpeg", "mirror"]}} for i in range(3)]
    info = parse_page_data(page_json({"id": "1", "author": {"uniqueId": "a"}, "imagePost": {"images": images}}))
    assert info.kind is MediaKind.PHOTOS
    assert info.media_urls == ("https://img/0.jpeg", "https://img/1.jpeg", "https://img/2.jpeg")


@pytest.mark.parametrize("raw", ["", "not json", json.dumps({"__DEFAULT_SCOPE__": {}}),
                                 page_json({"id": "1", "video": {}})])
def test_parse_rejects_bad_data(raw):
    with pytest.raises(DownloadError):
        parse_page_data(raw)


def test_extract_page_data():
    assert json.loads(extract_page_data(page_html({"id": "1"})))["__DEFAULT_SCOPE__"]


def test_extract_page_data_missing():
    with pytest.raises(DownloadError, match="no post data"):
        extract_page_data("<html>captcha</html>")


@pytest.fixture
async def tiktok_server(aiohttp_server):
    """Mimics TikTok: short link -> redirect to post page (sets cookie) -> CDN that requires cookie + referer."""
    async def short(request):
        raise web.HTTPFound("/@neo/video/42")

    async def post(request):
        base = str(request.url.origin())
        item = {"id": "42", "desc": "d", "author": {"uniqueId": "neo"}, "video": {"playAddr": f"{base}/cdn/42.mp4"}}
        response = web.Response(text=page_html(item), content_type="text/html")
        response.set_cookie("tt_chain_token", "ok")
        return response

    async def slides(request):
        base = str(request.url.origin())
        images = [{"imageURL": {"urlList": [f"{base}/cdn/{i}.jpeg"]}} for i in range(2)]
        return web.Response(text=page_html({"id": "7", "imagePost": {"images": images}}), content_type="text/html")

    async def cdn(request):
        if request.headers.get("referer") != "https://www.tiktok.com/":
            return web.Response(status=403)
        if request.match_info["name"].endswith(".mp4") and request.cookies.get("tt_chain_token") != "ok":
            return web.Response(status=403)
        return web.Response(body=b"media:" + request.match_info["name"].encode())

    async def home(request):
        return web.Response(text="<html></html>")

    app = web.Application()
    app.router.add_get("/short", short)
    app.router.add_get("/@neo/video/42", post)
    app.router.add_get("/@neo/photo/7", slides)
    app.router.add_get("/home", home)
    app.router.add_get("/cdn/{name}", cdn)
    return await aiohttp_server(app)


async def test_http_downloads_video_with_page_cookies(tiktok_server, tmp_path):
    post = await HttpDownloader().download(str(tiktok_server.make_url("/short")), tmp_path)
    assert (post.post_id, post.author, post.kind) == ("42", "neo", MediaKind.VIDEO)
    assert post.files[0].read_bytes() == b"media:42.mp4"


async def test_http_downloads_slideshow(tiktok_server, tmp_path):
    post = await HttpDownloader().download(str(tiktok_server.make_url("/@neo/photo/7")), tmp_path)
    assert post.kind is MediaKind.PHOTOS
    assert [f.read_bytes() for f in post.files] == [b"media:0.jpeg", b"media:1.jpeg"]
    assert all(f.suffix == ".jpeg" for f in post.files)


@pytest.mark.parametrize("path, error", [("/home", "non-post page"), ("/missing", "HTTP 404")])
async def test_http_rejects_non_post(tiktok_server, tmp_path, path, error):
    with pytest.raises(DownloadError, match=error):
        await HttpDownloader().download(str(tiktok_server.make_url(path)), tmp_path)


async def test_fallback_uses_next_on_failure_and_logs_it(tmp_path, caplog):
    broken, working = FakeDownloader(error=RuntimeError("captcha")), FakeDownloader()
    broken.name, working.name = "http", "firefox"
    with caplog.at_level(logging.WARNING):
        post = await FallbackDownloader([broken, working]).download("u", tmp_path)
    assert post.post_id == "123"
    assert post.fallback is True
    assert broken.calls == working.calls == ["u"]
    assert "http failed for u: captcha; using fallback firefox" in caplog.text
    assert "downloaded u via fallback firefox" in caplog.text


async def test_fallback_stops_at_first_success(tmp_path, caplog):
    first, second = FakeDownloader(), FakeDownloader()
    with caplog.at_level(logging.WARNING):
        post = await FallbackDownloader([first, second]).download("u", tmp_path)
    assert post.fallback is False
    assert second.calls == []
    assert caplog.text == ""


async def test_fallback_all_fail(tmp_path, caplog):
    chain = FallbackDownloader([FakeDownloader(error=RuntimeError("a")), FakeDownloader(error=RuntimeError("b"))])
    with pytest.raises(DownloadError, match="a.*b"):
        await chain.download("u", tmp_path)
    assert "no fallbacks left" in caplog.text


async def test_fallback_does_not_retry_too_large(tmp_path):
    second = FakeDownloader()
    with pytest.raises(MediaTooLarge):
        await FallbackDownloader([FakeDownloader(error=MediaTooLarge("big")), second]).download("u", tmp_path)
    assert second.calls == []


def test_fallback_describe():
    assert FallbackDownloader([HttpDownloader(), FakeDownloader()]).describe() == "http (primary) -> fake (fallback)"


def test_fallback_requires_downloaders():
    with pytest.raises(ValueError):
        FallbackDownloader([])
