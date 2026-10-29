import pytest

from bot.links import find_tiktok_url


@pytest.mark.parametrize("text, expected", [
    ("https://vt.tiktok.com/ZSgQ4q459", "https://vt.tiktok.com/ZSgQ4q459"),
    ("смотри https://vt.tiktok.com/ZSbYPdRrr/ ахах", "https://vt.tiktok.com/ZSbYPdRrr/"),
    ("(https://vm.tiktok.com/ZMabc123/).", "https://vm.tiktok.com/ZMabc123/"),
    ("https://www.tiktok.com/@user/video/7106594312292453675?lang=en",
     "https://www.tiktok.com/@user/video/7106594312292453675?lang=en"),
    ("HTTPS://M.TIKTOK.COM/v/123.html", "HTTPS://M.TIKTOK.COM/v/123.html"),
])
def test_finds_url(text, expected):
    assert find_tiktok_url(text) == expected


@pytest.mark.parametrize("text", [None, "", "hello", "https://youtube.com/watch?v=1", "https://nottiktok.com.evil.io/x",
                                  "tiktok.com/@user"])
def test_no_url(text):
    assert find_tiktok_url(text) is None
