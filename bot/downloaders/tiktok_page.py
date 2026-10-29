import json
import re
from dataclasses import dataclass

from ..models import DownloadError, MediaKind

POST_URL = re.compile(r"/(?:video|photo)/\d+")
REFERER = {"referer": "https://www.tiktok.com/"}
_DATA_SCRIPT = re.compile(r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', re.DOTALL)


@dataclass(frozen=True)
class PostInfo:
    post_id: str
    author: str
    description: str
    kind: MediaKind
    media_urls: tuple[str, ...]

    @property
    def suffix(self) -> str:
        return ".mp4" if self.kind is MediaKind.VIDEO else ".jpeg"


def extract_page_data(html: str) -> str:
    match = _DATA_SCRIPT.search(html)
    if match is None:
        raise DownloadError("page has no post data (captcha or removed post?)")
    return match.group(1)


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
