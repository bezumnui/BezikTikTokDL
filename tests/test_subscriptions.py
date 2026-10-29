from types import SimpleNamespace

from aiogram.enums import ChatMemberStatus

from bot.handlers.subscriptions import subscribe, unsubscribe
from bot.subscriptions import JsonSubscriptionStore


def test_store_add_remove_persist(tmp_path):
    path = tmp_path / "subs.json"
    store = JsonSubscriptionStore(path)
    assert store.add(-100, "Group") is True
    assert store.add(-100, "Group") is False
    assert JsonSubscriptionStore(path).is_subscribed(-100)
    assert store.remove(-100) is True
    assert store.remove(-100) is False
    assert not JsonSubscriptionStore(path).is_subscribed(-100)


class FakeMessage:
    def __init__(self):
        self.chat = SimpleNamespace(id=-100, title="Group")
        self.replies = []

    async def reply(self, text):
        self.replies.append(text)


class FakeBot:
    def __init__(self, reads_all=False, status=ChatMemberStatus.MEMBER):
        self.reads_all, self.status = reads_all, status

    async def me(self):
        return SimpleNamespace(id=1, can_read_all_group_messages=self.reads_all)

    async def get_chat_member(self, chat_id, user_id):
        return SimpleNamespace(status=self.status)


async def test_subscribe_and_unsubscribe(tmp_path):
    store = JsonSubscriptionStore(tmp_path / "s.json")
    message = FakeMessage()
    await subscribe(message, FakeBot(reads_all=True), store)
    assert store.is_subscribed(-100)
    assert message.replies[-1].startswith("Subscribed.") and "⚠️" not in message.replies[-1]
    await subscribe(message, FakeBot(reads_all=True), store)
    assert "already" in message.replies[-1]
    await unsubscribe(message, store)
    assert not store.is_subscribed(-100)
    await unsubscribe(message, store)
    assert "isn't subscribed" in message.replies[-1]


async def test_subscribe_warns_when_bot_cannot_read_messages(tmp_path):
    message = FakeMessage()
    await subscribe(message, FakeBot(), JsonSubscriptionStore(tmp_path / "s.json"))
    assert "privacy mode" in message.replies[-1]


async def test_admin_bot_reads_messages_despite_privacy_mode(tmp_path):
    message = FakeMessage()
    await subscribe(message, FakeBot(status=ChatMemberStatus.ADMINISTRATOR), JsonSubscriptionStore(tmp_path / "s.json"))
    assert "⚠️" not in message.replies[-1]
