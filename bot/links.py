import re

_TIKTOK_URL = re.compile(
    r"https?://(?:[a-z0-9-]+\.)?tiktok\.com/[^\s<>\"']+",
    re.IGNORECASE,
)


def find_tiktok_url(text: str | None) -> str | None:
    if not text:
        return None
    match = _TIKTOK_URL.search(text)
    return match.group(0).rstrip(".,!?)]}") if match else None
