# BezikTikTokDL

An inline Telegram bot (aiogram 3) that downloads TikTok videos and photo slideshows.

## Usage

- **Private chat:** send a link. It can be anywhere in the text or caption, or hidden behind a text link.
- **Group:** reply to a message with a link using `/dl` or a mention of the bot, or send `/dl <link>`.
- **Subscribed group:** a group admin sends `/sub`, and the bot downloads every TikTok link posted there.
  `/unsub` turns this off. To read regular messages, the bot must be an admin, or privacy mode must be disabled
  in @BotFather (`/setprivacy` → Disable) and the bot re-added to the group. `/sub` warns when the bot can't read them.
  Failed downloads stay silent in this mode (profile links, removed posts); explicit requests get an error reply.
- **Inline:** `@bot https://vt.tiktok.com/…` in any chat. If the video isn't cached and doesn't download within
  `INLINE_WAIT_SECONDS`, a "⏳ Downloading…" placeholder is sent and later replaced with the video.
  This needs `/setinlinefeedback` enabled in @BotFather.
- **Invite:** `@bot invite` (or just `@bot inv`) sends an invitation to use the bot, with "Add to group" and "Open bot" buttons.

Inline queries can't see the message you are replying to: Telegram only sends the typed text.
To take the link from a replied message, use `/dl` or a mention in a group where the bot is present.

## How downloading works

1. **`http` (primary):** a plain GET of the post page. The page embeds `__UNIVERSAL_DATA_FOR_REHYDRATION__` JSON
   with direct media URLs; the file is fetched with that page's cookies and `Referer: https://www.tiktok.com/`.
   No `X-Bogus`/`msToken` signing is needed, since that is only required by the `/api/...` JSON endpoints. Takes ~1–2 s.
2. **`firefox` (fallback):** the same, via headless Firefox (Playwright), for captchas or JS challenges that plain
   HTTP doesn't pass. Takes ~3–4 s.

On startup the bot logs the chain: `downloaders: http (primary) -> firefox (fallback)`.
When the primary fails, the log shows `WARNING ... http failed for <url>: ...; using fallback firefox`, and on success
`downloaded <url> via fallback firefox`. Frequent lines like these mean TikTok changed something.

## Architecture

| Module | Responsibility |
|---|---|
| `bot/downloaders/` | `Downloader` protocol, `HttpDownloader`, `FirefoxDownloader`, `FallbackDownloader` (chain), `tiktok_page` (page parsing) |
| `bot/publisher.py` | `TelegramPublisher`: uploads files to `STORAGE_CHAT_ID` and returns reusable `file_id`s |
| `bot/cache.py` | `JsonPostCache`: URL/post id → `file_id` |
| `bot/subscriptions.py` | `JsonSubscriptionStore`: groups with automatic downloads |
| `bot/service.py` | `MediaService`: cache, de-duplication of parallel downloads, concurrency limit, timeout, 50 MB limit |
| `bot/filters.py` | When a message asks for a download, and where to answer; group admin check |
| `bot/presenters.py` | Conversion to inline results / `InputMedia` |
| `bot/handlers/` | `chat`, `inline`, `subscriptions` routers: Telegram logic only |
| `bot/__main__.py` | Composition root: dependencies are wired here |

A new download source is a new class with `download(url, workdir)`, added to the chain in `__main__.py`.

## Running

### Docker

```bash
cp .env.example .env   # BOT_TOKEN, STORAGE_CHAT_ID
mkdir -p data && sudo chown 1000:1000 data
docker compose up -d --build
```

### Locally

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m playwright install --with-deps firefox
cp .env.example .env
.venv/bin/python -m bot
```

`STORAGE_CHAT_ID` is the chat the bot uploads files to in order to get a `file_id` (the messages are deleted right away).
For a group, the bot must be a member (and an admin, to delete the messages). For a user, they must send `/start` to the bot.
The bot checks this chat on startup and won't start if it is unreachable.
A group upgraded to a supergroup gets a new id starting with `-100`.
After editing `.env`, run `docker compose up -d`; `restart` doesn't re-read `env_file`.

## Tests

```bash
pytest            # unit tests, no network
pytest -m live    # real TikTok downloads + integrity check with ffmpeg
```
