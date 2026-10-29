# BezikTikTokDL

Inline Telegram-бот на aiogram 3 для скачивания видео и фото-слайдов из TikTok.
Основа — [Fluxticks/TikTokDL](https://github.com/Fluxticks/TikTokDL) (`tiktok-dlpy`), с запасным загрузчиком на Playwright,
который читает `__UNIVERSAL_DATA_FOR_REHYDRATION__` со страницы (TikTok перестал отдавать `/api/reflow/item/detail/` для многих постов).

## Использование

- **Личка:** прислать ссылку.
- **Группа:** сообщение со ссылкой; или ответ на сообщение со ссылкой командой `/dl` / упоминанием бота.
  Чтобы бот видел обычные сообщения в группах — выключить privacy mode в @BotFather (`/setprivacy`).
- **Inline:** `@bot https://vt.tiktok.com/…` в любом чате. Если видео ещё не в кэше и не скачалось за
  `INLINE_WAIT_SECONDS`, отправляется заглушка «⏳ Загружаю…», которая заменяется видео.
  Для этого в @BotFather нужно включить `/setinlinefeedback` (100%).

## Архитектура

| Модуль | Ответственность |
|---|---|
| `bot/downloaders/` | `Downloader` (протокол), `TikTokDLDownloader` (адаптер библиотеки), `PageDataDownloader`, `FallbackDownloader` (цепочка) |
| `bot/publisher.py` | `TelegramPublisher` — загружает файлы в `STORAGE_CHAT_ID`, возвращает переиспользуемые `file_id` |
| `bot/cache.py` | `JsonPostCache` — URL/id поста → `file_id` |
| `bot/service.py` | `MediaService` — кэш, дедупликация параллельных загрузок, лимит параллелизма, таймаут, лимит 50 МБ |
| `bot/presenters.py` | Преобразование в inline-результаты / `InputMedia` |
| `bot/handlers/` | `chat` и `inline` роутеры — только Telegram-логика |
| `bot/__main__.py` | Composition root: здесь собираются зависимости |

Новый источник загрузки — новый класс с методом `download(url, workdir)`, добавляется в цепочку в `__main__.py`.

## Запуск

### Docker

```bash
cp .env.example .env   # BOT_TOKEN, STORAGE_CHAT_ID
mkdir -p data && sudo chown 1000:1000 data
docker compose up -d --build
```

### Локально

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m playwright install --with-deps firefox
cp .env.example .env
.venv/bin/python -m bot
```

`STORAGE_CHAT_ID` — чат, куда бот загружает файлы, чтобы получить `file_id` (сообщения сразу удаляются).
Этот чат должен хотя бы раз написать боту `/start`.

## Тесты

```bash
pytest            # unit-тесты, без сети
pytest -m live    # реальные загрузки из TikTok + проверка целостности через ffmpeg
```
