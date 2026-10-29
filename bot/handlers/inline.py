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
)

from ..config import Config
from ..links import find_tiktok_url
from ..models import DownloadError, MediaTooLarge
from ..presenters import inline_results, result_id, single_media
from ..service import MediaService

log = logging.getLogger(__name__)
router = Router(name="inline")

PENDING_PREFIX = "wait"


def _article(prefix: str, key: str, title: str, text: str, description: str | None = None,
             markup: InlineKeyboardMarkup | None = None) -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id=result_id(prefix, key), title=title, description=description,
        input_message_content=InputTextMessageContent(message_text=text), reply_markup=markup,
    )


@router.inline_query()
async def inline_query(query: InlineQuery, media: MediaService, config: Config) -> None:
    log.info("inline query %s from %s: %r", query.id, query.from_user.id, query.query)
    url = find_tiktok_url(query.query)
    if url is None:
        await query.answer(
            [_article("help", "help", "Вставь ссылку на TikTok", "Использование: @бот https://vt.tiktok.com/…",
                      "vt.tiktok.com, vm.tiktok.com, tiktok.com/@user/video/…")],
            cache_time=300, is_personal=False,
        )
        return

    try:
        post = await asyncio.wait_for(media.get(url), config.inline_wait)
    except TimeoutError:
        # Download keeps running; the placeholder is swapped for the video in chosen_inline_result.
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть в TikTok", url=url)]])
        await query.answer(
            [_article(PENDING_PREFIX, url, "Отправить видео", f"⏳ Загружаю видео…\n{url}",
                      "Скачивание займёт несколько секунд", markup)],
            cache_time=0, is_personal=True,
        )
        return
    except MediaTooLarge:
        await query.answer([_article("err", url, "Файл больше 50 МБ", url)], cache_time=0)
        return
    except DownloadError as e:
        log.warning("inline download failed for %s: %s", url, e)
        await query.answer([_article("err", url, "Не получилось скачать", url, "Проверь ссылку")], cache_time=0)
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
        await bot.edit_message_text(inline_message_id=result.inline_message_id, text=f"Не получилось скачать\n{url}")
        return
    await bot.edit_message_media(inline_message_id=result.inline_message_id, media=single_media(post))
