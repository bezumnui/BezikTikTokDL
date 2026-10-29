import asyncio
import logging

from aiogram import Bot, Router
from aiogram.types import (
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    LinkPreviewOptions,
)

from ..config import Config
from ..links import find_tiktok_url
from ..models import DownloadError, MediaTooLarge
from ..presenters import inline_results, result_id, single_media
from ..service import MediaService

log = logging.getLogger(__name__)
router = Router(name="inline")

PENDING_PREFIX = "wait"
INVITE_KEYWORD = "invite"

INVITE_TEXT = (
    "📥 I download TikTok videos right in Telegram with @{username}\n\n"
    "• Type <code>@{username} TikTok link</code> in any chat\n"
    "• Or add the bot to a group and send /sub: it will download every TikTok link automatically\n\n"
    "My sources: {source_url}"
)
SOURCE_URL = "https://github.com/bezumnui/BezikTikTokDL"


def _article(prefix: str, key: str, title: str, text: str, description: str | None = None,
             markup: InlineKeyboardMarkup | None = None, html: bool = False) -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id=result_id(prefix, key), title=title, description=description,
        input_message_content=InputTextMessageContent(
            message_text=text, parse_mode="HTML" if html else None,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        ),
        reply_markup=markup,
    )


def invite_article(username: str) -> InlineQueryResultArticle:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add to group", url=f"https://t.me/{username}?startgroup=true")],
        [InlineKeyboardButton(text="Open bot", url=f"https://t.me/{username}")],
    ])
    text = INVITE_TEXT.format(username=username, source_url=SOURCE_URL)
    return _article("invite", username, "Invite to use the bot", text, "Send an invitation to this chat", markup, html=True)


def help_article(username: str) -> InlineQueryResultArticle:
    return _article("help", username, "Paste a TikTok link", f"Usage: @{username} https://vt.tiktok.com/…",
                    "vt.tiktok.com, vm.tiktok.com, tiktok.com/@user/video/…")


def _is_invite(text: str) -> bool:
    text = text.strip().lower()
    return bool(text) and INVITE_KEYWORD.startswith(text)


@router.inline_query()
async def inline_query(query: InlineQuery, bot: Bot, media: MediaService, config: Config) -> None:
    log.info("inline query %s from %s: %r", query.id, query.from_user.id, query.query)
    username = (await bot.me()).username
    if _is_invite(query.query):
        await query.answer([invite_article(username)], cache_time=300, is_personal=False)
        return
    url = find_tiktok_url(query.query)
    if url is None:
        await query.answer([help_article(username), invite_article(username)], cache_time=300, is_personal=False)
        return

    try:
        post = await asyncio.wait_for(media.get(url), config.inline_wait)
    except TimeoutError:
        # Download keeps running; the placeholder is swapped for the video in chosen_inline_result.
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Open in TikTok", url=url)]])
        await query.answer(
            [_article(PENDING_PREFIX, url, "Send video", f"⏳ Downloading the video…\n{url}",
                      "It takes a few seconds", markup)],
            cache_time=0, is_personal=True,
        )
        return
    except MediaTooLarge:
        await query.answer([_article("err", url, "The file is larger than 50 MB", url)], cache_time=0)
        return
    except DownloadError as e:
        log.warning("inline download failed for %s: %s", url, e)
        await query.answer([_article("err", url, "Couldn't download it", url, "Check the link")], cache_time=0)
        return

    await query.answer(inline_results(post), cache_time=3600, is_personal=False)


@router.chosen_inline_result()
async def chosen(result: ChosenInlineResult, bot: Bot, media: MediaService) -> None:
    log.info("chosen inline result %s from %s", result.result_id, result.from_user.id)
    if not result.result_id.startswith(PENDING_PREFIX) or not result.inline_message_id:
        return
    url = find_tiktok_url(result.query)
    if url is None:
        return
    try:
        post = await media.get(url)
    except DownloadError as e:
        log.warning("deferred inline download failed for %s: %s", url, e)
        await bot.edit_message_text(inline_message_id=result.inline_message_id, text=f"Couldn't download it\n{url}")
        return
    await bot.edit_message_media(inline_message_id=result.inline_message_id, media=single_media(post))
