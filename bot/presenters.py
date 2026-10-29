import hashlib

from aiogram.types import (
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedVideo,
    InputMediaPhoto,
    InputMediaVideo,
)

from .models import MediaKind, PublishedPost

MEDIA_GROUP_LIMIT = 10


def result_id(prefix: str, value: str) -> str:
    return f"{prefix}:{hashlib.sha1(value.encode()).hexdigest()[:32]}"


def inline_results(post: PublishedPost) -> list[InlineQueryResultCachedVideo | InlineQueryResultCachedPhoto]:
    title = post.caption or "TikTok"
    if post.kind is MediaKind.VIDEO:
        return [InlineQueryResultCachedVideo(
            id=result_id("v", post.post_id), video_file_id=post.file_ids[0], title=title, caption=post.caption,
            description=post.description[:100] or None,
        )]
    return [
        InlineQueryResultCachedPhoto(
            id=result_id("p", f"{post.post_id}:{idx}"), photo_file_id=file_id, title=title, caption=post.caption,
        )
        for idx, file_id in enumerate(post.file_ids[:50])
    ]


def single_media(post: PublishedPost) -> InputMediaVideo | InputMediaPhoto:
    """An inline message holds one media, so slideshows show their first image."""
    if post.kind is MediaKind.VIDEO:
        return InputMediaVideo(media=post.file_ids[0], caption=post.caption, supports_streaming=True)
    return InputMediaPhoto(media=post.file_ids[0], caption=post.caption)


def photo_groups(post: PublishedPost) -> list[list[InputMediaPhoto]]:
    groups = []
    for start in range(0, len(post.file_ids), MEDIA_GROUP_LIMIT):
        chunk = post.file_ids[start:start + MEDIA_GROUP_LIMIT]
        groups.append([
            InputMediaPhoto(media=file_id, caption=post.caption if start == idx == 0 else None)
            for idx, file_id in enumerate(chunk)
        ])
    return groups
