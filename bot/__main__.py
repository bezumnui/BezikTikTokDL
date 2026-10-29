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


def build_media_service(bot: Bot, config: Config) -> MediaService:
    downloader = FallbackDownloader([HttpDownloader(), FirefoxDownloader()])
    log.info("downloaders: %s", downloader.describe())
    return MediaService(
        downloader=downloader,
        publisher=TelegramPublisher(bot, config.storage_chat_id),
        cache=JsonPostCache(config.cache_file),
        work_root=config.work_root,
        max_parallel=config.max_parallel,
        timeout=config.download_timeout,
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()

    bot = Bot(config.bot_token)
    dp = Dispatcher(media=build_media_service(bot, config), config=config)
    dp.include_routers(inline.router, chat.router)

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
