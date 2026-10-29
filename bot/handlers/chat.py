import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from ..filters import TikTokLink, message_text
from ..models import DownloadError, MediaKind, MediaTooLarge
from ..presenters import photo_groups
from ..service import MediaService

log = logging.getLogger(__name__)
router = Router(name="chat")

HELP = (
    "Скачиваю видео и фото-слайды из TikTok.\n\n"
    "• Пришли ссылку — отвечу видео.\n"
    "• В группе: ответь на сообщение со ссылкой командой /dl или упоминанием бота.\n"
    "• В любом чате: <code>@{username} ссылка</code> — inline-режим."
)


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
@router.message(Command("help"))
async def help_(message: Message, bot: Bot) -> None:
    me = await bot.me()
    await message.reply(HELP.format(username=me.username), parse_mode="HTML")


@router.message(TikTokLink())
async def download(message: Message, bot: Bot, url: str, media: MediaService) -> None:
    # Link taken from the replied message -> answer under that message
    target = message if url in message_text(message) else message.reply_to_message
    try:
        async with ChatActionSender(bot=bot, chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO):
            post = await media.get(url)
    except MediaTooLarge:
        await message.reply("Файл больше 50 МБ — Telegram не даёт ботам отправлять такие.")
        return
    except DownloadError as e:
        log.warning("download failed for %s: %s", url, e)
        await message.reply("Не получилось скачать. Проверь ссылку или попробуй позже.")
        return

    if post.kind is MediaKind.VIDEO:
        await target.reply_video(post.file_ids[0], caption=post.caption, supports_streaming=True)
    else:
        for group in photo_groups(post):
            await target.reply_media_group(group)


@router.message(Command("dl", "tt"))
async def download_usage(message: Message) -> None:
    await message.reply("Ответь этой командой на сообщение со ссылкой TikTok или укажи ссылку после команды.")
