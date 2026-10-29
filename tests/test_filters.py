from types import SimpleNamespace

import pytest
from aiogram.enums import ChatMemberStatus, MessageEntityType

from bot.filters import GroupAdmin, TikTokLink, find_message_url

URL = "https://vt.tiktok.com/ZSgQ4q459"
GROUP, SUBSCRIBED = -1, -2


class FakeBot:
    def __init__(self, status=ChatMemberStatus.MEMBER):
        self.status = status

    async def me(self):
        return SimpleNamespace(username="bezik_bot")

    async def get_chat_member(self, chat_id, user_id):
        return SimpleNamespace(status=self.status)


class Subs:
    def is_subscribed(self, chat_id):
        return chat_id == SUBSCRIBED


def msg(text, chat="group", chat_id=GROUP, reply=None, is_bot=False, entities=None, sender_chat=None):
    return SimpleNamespace(
        text=text, caption=None, entities=entities, caption_entities=None,
        chat=SimpleNamespace(type=chat, id=chat_id), sender_chat=sender_chat,
        from_user=SimpleNamespace(is_bot=is_bot, id=7), reply_to_message=reply,
    )


def hidden_link(url):
    return [SimpleNamespace(type=MessageEntityType.TEXT_LINK, url=url)]


@pytest.mark.parametrize("message, expected_url, answers_reply", [
    # private: any link anywhere in the text
    (msg(f"look {URL} lol", chat="private"), URL, False),
    (msg("скачай", chat="private", reply=msg(URL)), URL, True),
    # subscribed group: every link, caught by regex
    (msg(f"look {URL} lol", chat_id=SUBSCRIBED), URL, False),
    (msg("this one", chat_id=SUBSCRIBED, entities=hidden_link(URL)), URL, False),
    # regular group: only when addressed
    (msg(f"look {URL}"), None, None),
    (msg(f"/dl {URL}"), URL, False),
    (msg(f"@Bezik_Bot {URL}"), URL, False),
    (msg("/dl", reply=msg(URL)), URL, True),
    (msg("@bezik_bot get it", reply=msg(URL)), URL, True),
    (msg("/dl", reply=msg("open", entities=hidden_link(URL))), URL, True),
    (msg("lol", reply=msg(URL)), None, None),
    (msg("lol", chat_id=SUBSCRIBED, reply=msg(URL)), None, None),
    (msg("/dl", reply=msg("no link")), None, None),
    (msg(URL, chat="private", is_bot=True), None, None),
])
async def test_tiktok_link(message, expected_url, answers_reply):
    result = await TikTokLink()(message, FakeBot(), Subs())
    if expected_url is None:
        assert result is False
        return
    assert result["url"] == expected_url
    assert result["target"] is (message.reply_to_message if answers_reply else message)


async def test_auto_download_is_not_addressed():
    result = await TikTokLink()(msg(URL, chat_id=SUBSCRIBED), FakeBot(), Subs())
    assert result["addressed"] is False


def test_find_message_url_ignores_other_hidden_links():
    assert find_message_url(msg("x", entities=hidden_link("https://youtube.com/x"))) is None


@pytest.mark.parametrize("status, chat, sender_chat, expected", [
    (ChatMemberStatus.ADMINISTRATOR, "supergroup", None, True),
    (ChatMemberStatus.CREATOR, "group", None, True),
    (ChatMemberStatus.MEMBER, "supergroup", None, False),
    (ChatMemberStatus.MEMBER, "supergroup", SimpleNamespace(id=GROUP), True),  # anonymous admin
    (ChatMemberStatus.ADMINISTRATOR, "private", None, False),
])
async def test_group_admin(status, chat, sender_chat, expected):
    assert await GroupAdmin()(msg("/sub", chat=chat, sender_chat=sender_chat), FakeBot(status)) is expected
