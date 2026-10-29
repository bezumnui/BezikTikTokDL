import asyncio
import logging

from aiogram import Bot, Dispatcher

from .cache import JsonPostCache
from .config import Config, load_config
from .downloaders import FallbackDownloader, FirefoxDownloader, HttpDownloader
from .handlers import chat, inline
from .publisher import TelegramPublisher
from .service import MediaService

log = logging.getLogger("bot")


def build_media_service(bot: Bot, config: Config, publisher: TelegramPublisher) -> MediaService:
    downloader = FallbackDownloader([HttpDownloader(), FirefoxDownloader()])
    log.info("downloaders: %s", downloader.describe())
    return MediaService(
        downloader=downloader,
        publisher=publisher,
        cache=JsonPostCache(config.cache_file),
        work_root=config.work_root,
        max_parallel=config.max_parallel,
        timeout=config.download_timeout,
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()

    bot = Bot(config.bot_token)
    publisher = TelegramPublisher(bot, config.storage_chat_id)
    try:
        log.info("storage chat: %s (%s)", await publisher.verify(), config.storage_chat_id)
    except RuntimeError:
        await bot.session.close()
        raise
    me = await bot.me()
    if not me.supports_inline_queries:
        log.warning("inline mode is disabled for @%s: enable it in @BotFather -> /setinline", me.username)
    dp = Dispatcher(media=build_media_service(bot, config, publisher), config=config)
    dp.include_routers(inline.router, chat.router)

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
