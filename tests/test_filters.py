from types import SimpleNamespace

import pytest

from bot.filters import TikTokLink

URL = "https://vt.tiktok.com/ZSgQ4q459"


class FakeBot:
    async def me(self):
        return SimpleNamespace(username="bezik_bot")


def msg(text, chat="group", reply=None, is_bot=False):
    return SimpleNamespace(
        text=text, caption=None, chat=SimpleNamespace(type=chat),
        from_user=SimpleNamespace(is_bot=is_bot), reply_to_message=reply,
    )


@pytest.mark.parametrize("message, expected", [
    (msg(f"look {URL}"), URL),
    (msg("hi"), False),
    (msg("/dl", reply=msg(URL)), URL),
    (msg("@Bezik_Bot скачай", reply=msg(URL)), URL),
    (msg("скачай", chat="private", reply=msg(URL)), URL),
    (msg("lol", reply=msg(URL)), False),
    (msg(URL, is_bot=True), False),
    (msg("/dl", reply=msg("no link")), False),
])
async def test_tiktok_link(message, expected):
    result = await TikTokLink()(message, FakeBot())
    assert result == ({"url": expected} if expected else False)
