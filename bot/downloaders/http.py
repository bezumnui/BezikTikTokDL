from pathlib import Path

import aiohttp
from yarl import URL

from ..models import DownloadedPost, DownloadError
from .tiktok_page import POST_URL, REFERER, PostInfo, extract_page_data, parse_page_data

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
_CHUNK = 64 * 1024


class HttpDownloader:
    """Fetches the post page over plain HTTP: the embedded JSON holds direct media URLs, no signing needed."""

    name = "http"

    def __init__(self, timeout: float = 30.0):
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def download(self, url: str, workdir: Path) -> DownloadedPost:
        headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
        # Fresh cookie jar per post: the page sets the tokens the media CDN checks.
        jar = aiohttp.CookieJar(unsafe=True, quote_cookie=False)  # TikTok rejects quoted values
        async with aiohttp.ClientSession(headers=headers, timeout=self._timeout, cookie_jar=jar) as session:
            info = await self._read_post(session, url)
            files = await self._fetch_media(session, info, workdir)
        return DownloadedPost(info.post_id, info.author, info.kind, files, info.description)

    async def _read_post(self, session: aiohttp.ClientSession, url: str) -> PostInfo:
        async with session.get(url) as response:
            if response.status != 200:
                raise DownloadError(f"page request failed with HTTP {response.status}")
            if not POST_URL.search(response.url.path):
                raise DownloadError(f"redirected to a non-post page: {response.url}")
            html = await response.text()
        return parse_page_data(extract_page_data(html))

    async def _fetch_media(self, session: aiohttp.ClientSession, info: PostInfo, workdir: Path) -> tuple[Path, ...]:
        files = []
        for idx, media_url in enumerate(info.media_urls, start=1):
            path = workdir / f"{info.post_id}_{idx}{info.suffix}"
            # The CDN URL is signed: send it byte-for-byte, without yarl re-quoting.
            async with session.get(URL(media_url, encoded=True), headers=REFERER) as response:
                if response.status not in (200, 206):
                    raise DownloadError(f"media request failed with HTTP {response.status}")
                with path.open("wb") as file:
                    async for chunk in response.content.iter_chunked(_CHUNK):
                        file.write(chunk)
            files.append(path)
        return tuple(files)
