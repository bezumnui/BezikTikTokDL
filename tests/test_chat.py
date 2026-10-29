from types import SimpleNamespace

import pytest

from bot.handlers import chat
from bot.models import DownloadError, MediaKind, MediaTooLarge, PublishedPost


class FakeMessage:
    def __init__(self):
        self.chat = SimpleNamespace(id=-100)
        self.replies, self.videos = [], []

    async def reply(self, text, **kwargs):
        self.replies.append(text)

    async def reply_video(self, file_id, **kwargs):
        self.videos.append(file_id)


class FakeMedia:
    def __init__(self, result):
        self.result = result

    async def get(self, url):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture(autouse=True)
def no_chat_action(monkeypatch):
    class Noop:
        def __init__(self, **kwargs): ...
        async def __aenter__(self): ...
        async def __aexit__(self, *exc): ...
    monkeypatch.setattr(chat, "ChatActionSender", Noop)


async def test_video_goes_under_target():
    message, target = FakeMessage(), FakeMessage()
    post = PublishedPost("1", "neo", MediaKind.VIDEO, ("vid",))
    await chat.download(message, None, "u", target, True, FakeMedia(post))
    assert target.videos == ["vid"] and message.videos == []


@pytest.mark.parametrize("error, text", [(DownloadError("x"), "Couldn't download"), (MediaTooLarge("x"), "50 MB")])
async def test_addressed_failure_is_reported(error, text):
    message = FakeMessage()
    await chat.download(message, None, "u", message, True, FakeMedia(error))
    assert text in message.replies[0]


async def test_auto_download_failure_is_silent():
    message = FakeMessage()
    await chat.download(message, None, "u", message, False, FakeMedia(DownloadError("profile link")))
    assert message.replies == []
