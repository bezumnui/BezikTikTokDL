import json
import re
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import BrowserContext, async_playwright

from ..models import DownloadedPost, DownloadError, MediaKind

_POST_URL = re.compile(r"/(?:video|photo)/\d+")
_DATA_SELECTOR = "#__UNIVERSAL_DATA_FOR_REHYDRATION__"
_REFERER = {"referer": "https://www.tiktok.com/"}


@dataclass(frozen=True)
class PostInfo:
    post_id: str
    author: str
    description: str
    kind: MediaKind
    media_urls: tuple[str, ...]


def parse_page_data(raw: str) -> PostInfo:
    """Extract the post from TikTok's `__UNIVERSAL_DATA_FOR_REHYDRATION__` JSON."""
    try:
        detail = json.loads(raw)["__DEFAULT_SCOPE__"]["webapp.video-detail"]
        item = detail["itemInfo"]["itemStruct"]
    except (KeyError, TypeError, ValueError) as e:
        raise DownloadError(f"unexpected page data: {e!r}") from e

    image_post = item.get("imagePost")
    if image_post:
        kind = MediaKind.PHOTOS
        urls = tuple(img["imageURL"]["urlList"][0] for img in image_post.get("images", []))
    else:
        kind = MediaKind.VIDEO
        video = item.get("video") or {}
        url = video.get("playAddr") or video.get("downloadAddr")
        urls = (url,) if url else ()
    if not urls:
        raise DownloadError("post has no media urls")
    return PostInfo(
        post_id=str(item["id"]),
        author=(item.get("author") or {}).get("uniqueId", ""),
        description=item.get("desc", ""),
        kind=kind,
        media_urls=urls,
    )


class PageDataDownloader:
    """Reads the post JSON embedded in the page and fetches media with the page's cookies."""

    name = "page-data"

    def __init__(self, timeout: float = 20.0):
        self._timeout_ms = timeout * 1000

    async def download(self, url: str, workdir: Path) -> DownloadedPost:
        async with async_playwright() as playwright:
            browser = await playwright.firefox.launch(headless=True)
            try:
                context = await browser.new_context(**playwright.devices["Desktop Firefox"])
                info = await self._read_post(context, url)
                files = await self._fetch_media(context, info, workdir)
            finally:
                await browser.close()
        return DownloadedPost(info.post_id, info.author, info.kind, files, info.description)

    async def _read_post(self, context: BrowserContext, url: str) -> PostInfo:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
        await page.wait_for_url(_POST_URL, timeout=self._timeout_ms)
        script = await page.wait_for_selector(_DATA_SELECTOR, state="attached", timeout=self._timeout_ms)
        return parse_page_data(await script.text_content() or "")

    async def _fetch_media(self, context: BrowserContext, info: PostInfo, workdir: Path) -> tuple[Path, ...]:
        suffix = ".mp4" if info.kind is MediaKind.VIDEO else ".jpeg"
        files = []
        for idx, media_url in enumerate(info.media_urls, start=1):
            response = await context.request.get(media_url, headers=_REFERER, timeout=self._timeout_ms)
            if not response.ok:
                raise DownloadError(f"media request failed with HTTP {response.status}")
            path = workdir / f"{info.post_id}_{idx}{suffix}"
            path.write_bytes(await response.body())
            files.append(path)
        return tuple(files)
