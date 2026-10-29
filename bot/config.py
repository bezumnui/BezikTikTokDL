import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ADMIN_ID = 589283988


@dataclass(frozen=True)
class Config:
    bot_token: str
    storage_chat_id: int
    data_dir: Path
    work_root: Path
    max_parallel: int
    download_timeout: float
    inline_wait: float

    @property
    def cache_file(self) -> Path:
        return self.data_dir / "file_ids.json"

    @property
    def subscriptions_file(self) -> Path:
        return self.data_dir / "subscriptions.json"


def _path(name: str, default: str) -> Path:
    return Path(os.getenv(name) or default).expanduser().resolve()


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")
    return Config(
        bot_token=token,
        storage_chat_id=int(os.getenv("STORAGE_CHAT_ID") or ADMIN_ID),
        data_dir=_path("DATA_DIR", "./data"),
        work_root=_path("WORK_ROOT", "/tmp/bezik-tiktokdl"),
        max_parallel=int(os.getenv("MAX_PARALLEL") or 2),
        download_timeout=float(os.getenv("DOWNLOAD_TIMEOUT_SECONDS") or 90),
        inline_wait=float(os.getenv("INLINE_WAIT_SECONDS") or 8),
    )
