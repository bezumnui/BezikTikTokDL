import json
from pathlib import Path
from typing import Protocol


class SubscriptionStore(Protocol):
    def is_subscribed(self, chat_id: int) -> bool: ...

    def add(self, chat_id: int, title: str) -> bool: ...

    def remove(self, chat_id: int) -> bool: ...


class JsonSubscriptionStore:
    """Groups where every TikTok link is downloaded automatically, persisted as {chat_id: title}."""

    def __init__(self, path: Path):
        self._path = path
        self._chats: dict[int, str] = {}
        if path.exists():
            self._chats = {int(k): v for k, v in json.loads(path.read_text(encoding="utf-8")).items()}

    def is_subscribed(self, chat_id: int) -> bool:
        return chat_id in self._chats

    def add(self, chat_id: int, title: str) -> bool:
        existed = chat_id in self._chats
        self._chats[chat_id] = title
        self._save()
        return not existed

    def remove(self, chat_id: int) -> bool:
        if self._chats.pop(chat_id, None) is None:
            return False
        self._save()
        return True

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._chats, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)
