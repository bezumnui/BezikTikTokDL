from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.filters import Filter
from aiogram.types import Message

from .links import find_tiktok_url


def message_text(message: Message | None) -> str:
    if message is None:
        return ""
    return message.text or message.caption or ""


class TikTokLink(Filter):
    """Matches a TikTok link in the message itself, or in the replied message when the bot is addressed.

    Passes the link to the handler as `url`.
    """

    async def __call__(self, message: Message, bot: Bot) -> bool | dict:
        if message.from_user and message.from_user.is_bot:
            return False
        text = message_text(message)
        url = find_tiktok_url(text)
        if url is None and message.reply_to_message and await self._addressed(message, text, bot):
            url = find_tiktok_url(message_text(message.reply_to_message))
        return {"url": url} if url else False

    @staticmethod
    async def _addressed(message: Message, text: str, bot: Bot) -> bool:
        if message.chat.type == ChatType.PRIVATE or text.startswith("/"):
            return True
        me = await bot.me()
        return f"@{me.username}".lower() in text.lower()
