import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from ..filters import TikTokLink
from ..models import DownloadError, MediaKind, MediaTooLarge
from ..presenters import photo_groups
from ..service import MediaService

log = logging.getLogger(__name__)
router = Router(name="chat")

HELP = (
    "I download TikTok videos and photo slideshows.\n\n"
    "• Send me a link and I'll reply with the video.\n"
    "• In a group: reply to a message with a link using /dl or a mention of me.\n"
    "• In a group, an admin can send /sub and I'll download every TikTok link automatically "
    "(/unsub to stop).\n"
    "• In any chat: <code>@{username} link</code> (inline mode). "
    "<code>@{username} invite</code> sends an invitation to use me."
)


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
@router.message(Command("help"))
async def help_(message: Message, bot: Bot) -> None:
    me = await bot.me()
    await message.reply(HELP.format(username=me.username), parse_mode="HTML")


@router.message(TikTokLink())
async def download(message: Message, bot: Bot, url: str, target: Message, addressed: bool,
                   media: MediaService) -> None:
    try:
        async with ChatActionSender(bot=bot, chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO):
            post = await media.get(url)
    except DownloadError as e:
        log.warning("download failed for %s: %s", url, e)
        # Stay quiet on links picked up automatically in subscribed groups (profiles, removed posts, ...)
        if addressed:
            await message.reply(_error_text(e))
        return

    if post.kind is MediaKind.VIDEO:
        await target.reply_video(post.file_ids[0], caption=post.caption, supports_streaming=True)
    else:
        for group in photo_groups(post):
            await target.reply_media_group(group)


def _error_text(error: DownloadError) -> str:
    if isinstance(error, MediaTooLarge):
        return "The file is larger than 50 MB, and Telegram doesn't let bots send files that big."
    return "Couldn't download it. Check the link or try again later."


@router.message(Command("dl", "tt"))
async def download_usage(message: Message) -> None:
    await message.reply("Reply with this command to a message that has a TikTok link, or put the link after it.")
