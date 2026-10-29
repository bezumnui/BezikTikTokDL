import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from .models import MediaKind, PublishedPost


class PostCache(Protocol):
    def get(self, key: str) -> PublishedPost | None: ...

    def put(self, keys: Iterable[str], post: PublishedPost) -> None: ...


class JsonPostCache:
    """URL/post id -> uploaded file_ids, persisted to a JSON file."""

    def __init__(self, path: Path):
        self._path = path
        self._posts: dict[str, PublishedPost] = {}
        self._keys: dict[str, str] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            for post_id, data in raw.get("posts", {}).items():
                self._posts[post_id] = _load_post(data)
            self._keys = {k: v for k, v in raw.get("keys", {}).items() if v in self._posts}

    def get(self, key: str) -> PublishedPost | None:
        post_id = self._keys.get(key)
        return self._posts.get(post_id) if post_id else None

    def put(self, keys: Iterable[str], post: PublishedPost) -> None:
        self._posts[post.post_id] = post
        for key in (*keys, post.post_id):
            self._keys[key] = post.post_id
        self._save()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {"posts": {k: _dump_post(p) for k, p in self._posts.items()}, "keys": self._keys}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)


def _dump_post(post: PublishedPost) -> dict:
    data = asdict(post)
    data["kind"] = post.kind.value
    data["file_ids"] = list(post.file_ids)
    return data


def _load_post(data: dict) -> PublishedPost:
    return PublishedPost(
        post_id=data["post_id"],
        author=data.get("author", ""),
        kind=MediaKind(data["kind"]),
        file_ids=tuple(data["file_ids"]),
        description=data.get("description", ""),
    )
