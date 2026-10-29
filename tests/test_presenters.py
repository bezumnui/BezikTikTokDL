from aiogram.types import InlineQueryResultCachedPhoto, InlineQueryResultCachedVideo, InputMediaPhoto, InputMediaVideo

from bot.models import MediaKind, PublishedPost
from bot.presenters import inline_results, photo_groups, result_id, single_media

VIDEO = PublishedPost("1", "neo", MediaKind.VIDEO, ("vid",), "desc")
SLIDES = PublishedPost("2", "neo", MediaKind.PHOTOS, tuple(f"p{i}" for i in range(12)))


def test_result_id_is_short_and_stable():
    rid = result_id("wait", "https://vt.tiktok.com/" + "x" * 500)
    assert len(rid.encode()) <= 64
    assert rid == result_id("wait", "https://vt.tiktok.com/" + "x" * 500)


def test_inline_video():
    [result] = inline_results(VIDEO)
    assert isinstance(result, InlineQueryResultCachedVideo)
    assert result.video_file_id == "vid"
    assert result.caption == "@neo"


def test_inline_slides():
    results = inline_results(SLIDES)
    assert len(results) == 12
    assert all(isinstance(r, InlineQueryResultCachedPhoto) for r in results)
    assert len({r.id for r in results}) == 12


def test_fallback_mark_in_caption():
    post = PublishedPost("1", "neo", MediaKind.VIDEO, ("vid",), fallback=True)
    assert post.caption == "@neo\n⚠️fallback"
    assert inline_results(post)[0].caption == "@neo\n⚠️fallback"
    assert PublishedPost("1", "", MediaKind.VIDEO, ("vid",), fallback=True).caption == "⚠️fallback"
    assert VIDEO.caption == "@neo"


def test_single_media():
    assert isinstance(single_media(VIDEO), InputMediaVideo)
    photo = single_media(SLIDES)
    assert isinstance(photo, InputMediaPhoto) and photo.media == "p0"


def test_photo_groups_split_by_ten_with_one_caption():
    groups = photo_groups(SLIDES)
    assert [len(g) for g in groups] == [10, 2]
    captions = [m.caption for g in groups for m in g]
    assert captions[0] == "@neo" and not any(captions[1:])
