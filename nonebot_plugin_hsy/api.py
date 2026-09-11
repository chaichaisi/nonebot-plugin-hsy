import json
import random
import re
from urllib.parse import quote

import httpx

from .config import config

DEFAULT_FIELDS = {
    "date": "",
    "time": "tb_event_time",
    "quality": "tb_quality",
    "aod": "tb_aod",
}

_NO_DATA = {
    "date": "",
    "time": "无数据",
    "quality": "无数据",
    "aod": "无数据",
}


def _parse_template(raw) -> dict:
    if isinstance(raw, dict):
        if not raw:
            return dict(DEFAULT_FIELDS)
        return {str(k): str(v) for k, v in raw.items()}
    if not isinstance(raw, str) or not raw.strip():
        return dict(DEFAULT_FIELDS)
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return dict(DEFAULT_FIELDS)
    if not isinstance(obj, dict):
        return dict(DEFAULT_FIELDS)
    fields = {}
    for key, value in obj.items():
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False)
        fields[str(key)] = str(value)
    return fields


def _get_path(data, path: str):
    if not path or not str(path).strip():
        return None
    cur = data
    for part in re.split(r"[./]", str(path).strip().strip(".")):
        if not part:
            continue
        if isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError, TypeError):
                return None
        else:
            return None
    return cur


def _norm_quality(value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 0 <= value <= 1:
            return f"{value * 100:.0f}%"
        return f"{value}"
    return str(value).strip()


def _split_datetime(s: str) -> tuple[str, str]:
    dm = re.search(r"(\d{4}-\d{2}-\d{2})", s)
    tm = re.search(r"(\d{1,2}:\d{2})", s)
    return (
        dm.group(1) if dm else "",
        tm.group(1) if tm else s,
    )


def _to_info(rows: dict) -> dict:
    for key in ("time", "quality", "aod"):
        val = rows.get(key)
        if val is None or str(val).strip() in ("", "-"):
            return dict(_NO_DATA)
    raw_time = str(rows["time"]).strip()
    date_from_time, time = _split_datetime(raw_time)
    date = str(rows.get("date") or "").strip() or date_from_time
    return {
        "date": date,
        "time": time,
        "quality": _norm_quality(rows["quality"]),
        "aod": str(rows["aod"]).strip(),
    }


async def _get_json(url: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def _build_url(url: str, city: str) -> str:
    qid = random.randint(10**9, 10**10 - 1)
    encoded = quote(city, safe="")
    return url.format(query_id=qid, citys=encoded, city=encoded)


async def fetch_sunset(city: str) -> dict:
    fields = _parse_template(config.hsy_field_template)
    url = _build_url(config.hsy_api_url, city)
    try:
        data = await _get_json(url)
    except (httpx.HTTPError, ValueError, KeyError):
        raise RuntimeError("数据源不可用")
    rows = {key: _get_path(data, path) for key, path in fields.items()}
    return _to_info(rows)
