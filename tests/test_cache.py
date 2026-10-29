from bot.cache import JsonPostCache
from bot.models import MediaKind, PublishedPost

POST = PublishedPost("42", "author", MediaKind.PHOTOS, ("a", "b"), "описание")


def test_put_get_by_url_and_post_id(tmp_path):
    cache = JsonPostCache(tmp_path / "c.json")
    cache.put(["https://vt.tiktok.com/x"], POST)
    assert cache.get("https://vt.tiktok.com/x") == POST
    assert cache.get("42") == POST
    assert cache.get("missing") is None


def test_persists_between_instances(tmp_path):
    path = tmp_path / "nested" / "c.json"
    JsonPostCache(path).put(["u1"], POST)
    reloaded = JsonPostCache(path)
    assert reloaded.get("u1") == POST
    assert reloaded.get("42").kind is MediaKind.PHOTOS


def test_same_post_from_different_urls(tmp_path):
    cache = JsonPostCache(tmp_path / "c.json")
    cache.put(["u1"], POST)
    updated = PublishedPost("42", "author", MediaKind.PHOTOS, ("c",))
    cache.put(["u2"], updated)
    assert cache.get("u1") == updated
    assert cache.get("u2") == updated
