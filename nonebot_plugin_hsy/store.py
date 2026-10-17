import json
import threading
from datetime import datetime
from pathlib import Path

from nonebot import require

require("nonebot_plugin_localstore")

import nonebot_plugin_localstore as localstore

from .config import config

_lock = threading.Lock()
_data: dict | None = None

STATUS_MAP = {"pending": "即将", "done": "完成", "failed": "失败"}


def _path() -> Path:
    data_dir = localstore.get_plugin_data_dir()
    return data_dir / (config.hsy_data_path or "hsy_data.json")


def load() -> dict:
    global _data
    with _lock:
        if _data is None:
            p = _path()
            if p.exists():
                try:
                    _data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    _data = {}
            else:
                _data = {}
        return _data


def save() -> None:
    global _data
    with _lock:
        if _data is None:
            return
        p = _path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _key(user_id: str, city: str) -> str:
    return f"{user_id}:{city}"


def add_subscription(user_id: str, city: str, channel: str) -> tuple[bool, dict]:
    data = load()
    subs = data.setdefault("subscriptions", {})
    key = _key(str(user_id), city)
    if key in subs:
        return False, subs[key]
    sub = {
        "user_id": str(user_id),
        "city": city,
        "channel": channel,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notify_date": "",
        "remind_1h": "pending",
        "remind_30m": "pending",
        "retry_after": 0,
    }
    subs[key] = sub
    save()
    return True, sub


def remove_subscription(user_id: str, city: str) -> bool:
    data = load()
    subs = data.get("subscriptions", {})
    key = _key(str(user_id), city)
    if key not in subs:
        return False
    del subs[key]
    save()
    return True


def get_subscriptions(user_id: str | None = None) -> list[dict]:
    data = load()
    subs = data.get("subscriptions", {})
    if user_id is None:
        return list(subs.values())
    uid = str(user_id)
    return [s for s in subs.values() if s["user_id"] == uid]


def set_last_group(user_id: str, group_id: int | str) -> None:
    data = load()
    groups = data.setdefault("user_last_group", {})
    uid = str(user_id)
    if groups.get(uid) != str(group_id):
        groups[uid] = str(group_id)
        save()


def get_last_group(user_id: str) -> str | None:
    data = load()
    return data.get("user_last_group", {}).get(str(user_id))
