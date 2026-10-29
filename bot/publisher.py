from typing import Protocol

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile, InputMediaPhoto

from .models import DownloadedPost, MediaKind, PublishedPost
from .presenters import MEDIA_GROUP_LIMIT


class Publisher(Protocol):
    async def publish(self, post: DownloadedPost) -> PublishedPost: ...


class TelegramPublisher:
    """Uploads files to a storage chat once to obtain file_ids reusable in any chat or inline result."""

    def __init__(self, bot: Bot, storage_chat_id: int):
        self._bot = bot
        self._chat_id = storage_chat_id

    async def verify(self) -> str:
        """Fail fast at startup if the storage chat is unreachable. Returns its title for logging."""
        try:
            chat = await self._bot.get_chat(self._chat_id)
        except TelegramAPIError as e:
            raise RuntimeError(
                f"STORAGE_CHAT_ID={self._chat_id} is not reachable ({e.message}). "
                "Add the bot to that group, or for a user id: send /start to the bot. "
                "A group upgraded to a supergroup gets a new id starting with -100."
            ) from e
        return chat.title or chat.full_name

    async def publish(self, post: DownloadedPost) -> PublishedPost:
        if post.kind is MediaKind.VIDEO:
            file_ids = (await self._upload_video(post),)
        else:
            file_ids = await self._upload_photos(post)
        return PublishedPost(post.post_id, post.author, post.kind, file_ids, post.description, post.fallback)

    async def _upload_video(self, post: DownloadedPost) -> str:
        message = await self._bot.send_video(
            self._chat_id, FSInputFile(post.files[0]), supports_streaming=True, disable_notification=True
        )
        await self._cleanup([message.message_id])
        return message.video.file_id

    async def _upload_photos(self, post: DownloadedPost) -> tuple[str, ...]:
        file_ids: list[str] = []
        for start in range(0, len(post.files), MEDIA_GROUP_LIMIT):
            chunk = post.files[start:start + MEDIA_GROUP_LIMIT]
            messages = await self._bot.send_media_group(
                self._chat_id, [InputMediaPhoto(media=FSInputFile(p)) for p in chunk], disable_notification=True
            )
            await self._cleanup([m.message_id for m in messages])
            file_ids.extend(m.photo[-1].file_id for m in messages)
        return tuple(file_ids)

    async def _cleanup(self, message_ids: list[int]) -> None:
        # file_ids stay valid after the storage message is deleted
        try:
            await self._bot.delete_messages(self._chat_id, message_ids)
        except Exception:
            pass
