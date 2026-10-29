from aiogram import Bot
from aiogram.enums import ChatMemberStatus, ChatType, MessageEntityType
from aiogram.filters import Filter
from aiogram.types import Message

from .links import find_tiktok_url
from .subscriptions import SubscriptionStore

_ADMIN_STATUSES = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}


def message_text(message: Message | None) -> str:
    if message is None:
        return ""
    return message.text or message.caption or ""


def find_message_url(message: Message | None) -> str | None:
    """A TikTok link in the text/caption, or hidden behind a text link."""
    if message is None:
        return None
    entities = message.entities or message.caption_entities or []
    hidden = [e.url for e in entities if e.type == MessageEntityType.TEXT_LINK and e.url]
    return find_tiktok_url(" ".join([message_text(message), *hidden]))


async def is_addressed(message: Message, bot: Bot) -> bool:
    """Private chat, a command, or a mention of the bot."""
    text = message_text(message)
    if message.chat.type == ChatType.PRIVATE or text.startswith("/"):
        return True
    me = await bot.me()
    return f"@{me.username}".lower() in text.lower()


class TikTokLink(Filter):
    """Decides whether a message asks for a download.

    - own link: in private chats, subscribed groups, or when the bot is addressed (/dl <link>, @bot <link>);
    - replied message's link: when the bot is addressed (/dl or @bot as a reply).

    Passes `url`, `target` (the message to answer under) and `addressed` to the handler.
    """

    async def __call__(self, message: Message, bot: Bot, subscriptions: SubscriptionStore) -> bool | dict:
        if message.from_user and message.from_user.is_bot:
            return False
        addressed = await is_addressed(message, bot)
        if url := find_message_url(message):
            if addressed or subscriptions.is_subscribed(message.chat.id):
                return {"url": url, "target": message, "addressed": addressed}
            return False
        if addressed and (url := find_message_url(message.reply_to_message)):
            return {"url": url, "target": message.reply_to_message, "addressed": True}
        return False


class GroupAdmin(Filter):
    """Group admins, including anonymous admins posting as the group."""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return False
        if message.sender_chat and message.sender_chat.id == message.chat.id:
            return True
        if message.from_user is None:
            return False
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in _ADMIN_STATUSES
