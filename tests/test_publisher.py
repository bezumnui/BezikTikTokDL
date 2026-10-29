from types import SimpleNamespace

import pytest
from aiogram.exceptions import TelegramBadRequest

from bot.publisher import TelegramPublisher


class FakeBot:
    def __init__(self, chat=None):
        self.chat = chat

    async def get_chat(self, chat_id):
        if self.chat is None:
            raise TelegramBadRequest(method=None, message="Bad Request: chat not found")
        return self.chat


async def test_verify_returns_chat_title():
    publisher = TelegramPublisher(FakeBot(SimpleNamespace(title="Storage", full_name="Storage")), -5549295544)
    assert await publisher.verify() == "Storage"


async def test_verify_explains_unreachable_chat():
    with pytest.raises(RuntimeError, match=r"STORAGE_CHAT_ID=-5549295544 is not reachable \(Bad Request: chat not found\)"):
        await TelegramPublisher(FakeBot(), -5549295544).verify()
