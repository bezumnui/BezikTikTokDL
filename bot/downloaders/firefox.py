from pathlib import Path

from playwright.async_api import BrowserContext, async_playwright

from ..models import DownloadedPost, DownloadError
from .tiktok_page import POST_URL, REFERER, PostInfo, parse_page_data

_DATA_SELECTOR = "#__UNIVERSAL_DATA_FOR_REHYDRATION__"


class FirefoxDownloader:
    """Opens the post in headless Firefox; slower, but survives JS challenges that plain HTTP does not."""

    name = "firefox"

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
        await page.wait_for_url(POST_URL, timeout=self._timeout_ms)
        script = await page.wait_for_selector(_DATA_SELECTOR, state="attached", timeout=self._timeout_ms)
        return parse_page_data(await script.text_content() or "")

    async def _fetch_media(self, context: BrowserContext, info: PostInfo, workdir: Path) -> tuple[Path, ...]:
        files = []
        for idx, media_url in enumerate(info.media_urls, start=1):
            response = await context.request.get(media_url, headers=REFERER, timeout=self._timeout_ms)
            if not response.ok:
                raise DownloadError(f"media request failed with HTTP {response.status}")
            path = workdir / f"{info.post_id}_{idx}{info.suffix}"
            path.write_bytes(await response.body())
            files.append(path)
        return tuple(files)
