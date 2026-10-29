import asyncio
from types import SimpleNamespace

from aiogram.types import InlineQueryResultArticle, InlineQueryResultCachedVideo, InputMediaVideo

from bot.handlers.inline import PENDING_PREFIX, chosen, inline_query
from bot.models import DownloadError, MediaKind, PublishedPost

URL = "https://vt.tiktok.com/ZSgQ4q459"
POST = PublishedPost("1", "neo", MediaKind.VIDEO, ("vid",))
CONFIG = SimpleNamespace(inline_wait=0.05)


class FakeQuery:
    def __init__(self, text):
        self.query = text
        self.answers = []

    async def answer(self, results, **kwargs):
        self.answers.append((results, kwargs))


class FakeMedia:
    def __init__(self, delay=0.0, error=None):
        self.delay, self.error = delay, error

    async def get(self, url):
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return POST


class FakeBot:
    def __init__(self):
        self.calls = []

    async def edit_message_media(self, **kwargs):
        self.calls.append(("media", kwargs))

    async def edit_message_text(self, **kwargs):
        self.calls.append(("text", kwargs))


async def test_no_link_shows_help():
    query = FakeQuery("hello")
    await inline_query(query, FakeMedia(), CONFIG)
    [result] = query.answers[0][0]
    assert isinstance(result, InlineQueryResultArticle)


async def test_ready_video_is_answered_as_cached_video():
    query = FakeQuery(URL)
    await inline_query(query, FakeMedia(), CONFIG)
    [result] = query.answers[0][0]
    assert isinstance(result, InlineQueryResultCachedVideo) and result.video_file_id == "vid"


async def test_slow_download_answers_placeholder_in_time():
    query = FakeQuery(URL)
    await inline_query(query, FakeMedia(delay=1), CONFIG)
    [result] = query.answers[0][0]
    assert result.id.startswith(PENDING_PREFIX)
    assert result.reply_markup is not None, "inline_message_id is only issued for results with a keyboard"


async def test_download_error_is_answered():
    query = FakeQuery(URL)
    await inline_query(query, FakeMedia(error=DownloadError("x")), CONFIG)
    [result] = query.answers[0][0]
    assert result.title == "Не получилось скачать"


def chosen_result(result_id):
    return SimpleNamespace(result_id=result_id, inline_message_id="imid", query=URL)


async def test_placeholder_is_replaced_with_video():
    bot = FakeBot()
    await chosen(chosen_result(f"{PENDING_PREFIX}:abc"), bot, FakeMedia())
    [(kind, kwargs)] = bot.calls
    assert kind == "media" and kwargs["inline_message_id"] == "imid"
    assert isinstance(kwargs["media"], InputMediaVideo)


async def test_placeholder_reports_failure():
    bot = FakeBot()
    await chosen(chosen_result(f"{PENDING_PREFIX}:abc"), bot, FakeMedia(error=DownloadError("x")))
    assert bot.calls[0][0] == "text"


async def test_ready_results_are_not_edited():
    bot = FakeBot()
    await chosen(chosen_result("v:abc"), bot, FakeMedia())
    assert bot.calls == []
