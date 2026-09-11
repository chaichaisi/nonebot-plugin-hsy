import time
from datetime import datetime, timedelta
from typing import cast

from nonebot import get_bots, logger, require

require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler  # noqa: E402
from nonebot.adapters.onebot.v11 import Bot  # noqa: E402
from nonebot.adapters.onebot.v11.message import Message, MessageSegment  # noqa: E402

from . import api, store  # noqa: E402
from .config import config  # noqa: E402

_friend_cache: tuple[float, set[str]] | None = None


def _get_bot() -> Bot | None:
    bots = get_bots()
    if not bots:
        return None
    if config.hsy_bot_id:
        bot = bots.get(str(config.hsy_bot_id))
        if bot:
            return cast(Bot, bot)
    return cast(Bot, next(iter(bots.values())))


async def _get_friends(bot: Bot) -> set[str]:
    global _friend_cache
    now = time.time()
    if _friend_cache and now - _friend_cache[0] < 300:
        return _friend_cache[1]
    try:
        friends = {str(f["user_id"]) for f in await bot.get_friend_list()}
    except Exception:
        friends = set()
    _friend_cache = (now, friends)
    return friends


async def _find_common_group(bot: Bot, user_id: str) -> str | None:
    try:
        groups = await bot.get_group_list()
        for group in groups:
            try:
                members = await bot.get_group_member_list(
                    group_id=group["group_id"]
                )
                if any(str(m["user_id"]) == user_id for m in members):
                    return str(group["group_id"])
            except Exception:
                continue
    except Exception:
        pass
    return None


async def _send_reminder(
    bot: Bot, user_id: str, text: str, allow_at: bool
) -> bool:
    user_id = str(user_id)
    friends = await _get_friends(bot)
    if user_id in friends:
        try:
            await bot.send_private_msg(user_id=int(user_id), message=text)
            return True
        except Exception as e:
            logger.warning(f"私聊提醒失败 {user_id}: {e}")
    group_id = store.get_last_group(user_id)
    if not group_id:
        group_id = await _find_common_group(bot, user_id)
        if group_id:
            store.set_last_group(user_id, group_id)
    if group_id:
        try:
            await bot.send_private_msg(
                user_id=int(user_id), group_id=int(group_id), message=text
            )
            return True
        except Exception as e:
            logger.warning(f"临时会话提醒失败 {user_id}: {e}")
    if allow_at and group_id:
        try:
            await bot.send_group_msg(
                group_id=int(group_id),
                message=Message(
                    MessageSegment.at(user_id=user_id) + text
                ),
            )
            return True
        except Exception as e:
            logger.warning(f"群 @ 提醒失败 {user_id}: {e}")
    return False


def _parse_sunset(info: dict) -> datetime | None:
    t = info["time"]
    if not t or t in ("-", "无数据") or "无" in t:
        return None
    try:
        hm = datetime.strptime(t, "%H:%M")
    except ValueError:
        return None
    date_part = info.get("date", "")
    if date_part:
        try:
            d = datetime.strptime(date_part, "%Y-%m-%d")
            return d.replace(
                hour=hm.hour, minute=hm.minute, second=0, microsecond=0
            )
        except ValueError:
            pass
    now = datetime.now()
    return now.replace(
        hour=hm.hour, minute=hm.minute, second=0, microsecond=0
    )


def _remind_text(sub: dict, info: dict, when: str) -> str:
    return (
        f"━━ 火烧云提醒 ━━\n"
        f"{sub['city']} · 日落 {info['time']}\n"
        f"晚霞概率  {info['quality']}\n"
        f"晚霞质量  {info['aod']}\n"
        f"约{when}后开场，抬头看天～"
    )


def _refresh_text(sub: dict, info: dict) -> str:
    return (
        f"━━ 火烧云 · {sub['city']} ━━\n"
        f"日落时间  {info['time']}\n"
        f"晚霞概率  {info['quality']}\n"
        f"晚霞质量  {info['aod']}"
    )


async def send_refresh(bot: Bot, user_id: str, sub: dict, info: dict) -> bool:
    allow_at = sub.get("channel", "user") == "user"
    return await _send_reminder(
        bot, user_id, _refresh_text(sub, info), allow_at
    )


_RETRY_MINUTES = 30


async def _process_sub(bot: Bot, sub: dict, today: str, cache: dict) -> None:
    city = sub["city"]
    now = datetime.now()
    if now.timestamp() < sub.get("retry_after", 0):
        return
    if city not in cache:
        cache[city] = await api.fetch_sunset(city)
    info = cache[city]
    sunset = _parse_sunset(info)
    if sunset is None:
        sub["retry_after"] = (now + timedelta(minutes=_RETRY_MINUTES)).timestamp()
        sub["notify_date"] = ""
        sub["remind_1h"] = "pending"
        sub["remind_30m"] = "pending"
        return
    sub.pop("retry_after", None)
    if sub.get("notify_date") != today:
        sub["notify_date"] = today
        sub["remind_1h"] = "pending"
        sub["remind_30m"] = "pending"
    user_id = sub["user_id"]
    allow_at = sub.get("channel", "user") == "user"
    if (
        sub.get("remind_1h") == "pending"
        and now >= sunset - timedelta(hours=1)
        and now < sunset
    ):
        ok = await _send_reminder(
            bot, user_id, _remind_text(sub, info, "1小时"), allow_at
        )
        sub["remind_1h"] = "done" if ok else "failed"
        if not ok:
            logger.error(f"提醒发送失败，用户: {user_id} 城市: {city} 阶段: 1小时")
    if (
        sub.get("remind_30m") == "pending"
        and now >= sunset - timedelta(minutes=30)
        and now < sunset
    ):
        ok = await _send_reminder(
            bot, user_id, _remind_text(sub, info, "30分钟"), allow_at
        )
        sub["remind_30m"] = "done" if ok else "failed"
        if not ok:
            logger.error(f"提醒发送失败，用户: {user_id} 城市: {city} 阶段: 30分钟")


async def _run_reminders() -> None:
    bot = _get_bot()
    if bot is None:
        return
    subs = store.get_subscriptions()
    if not subs:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    cache: dict = {}
    changed = False
    for sub in subs:
        try:
            await _process_sub(bot, sub, today, cache)
            changed = True
        except Exception as e:
            logger.exception(f"订阅处理失败: {sub}")
            sub["retry_after"] = (
                datetime.now() + timedelta(minutes=_RETRY_MINUTES)
            ).timestamp()
            changed = True
    if changed:
        store.save()


@scheduler.scheduled_job(
    "interval", minutes=config.hsy_refresh_interval, id="hsy_reminder"
)
async def hsy_reminder_job() -> None:
    try:
        await _run_reminders()
    except Exception as e:
        logger.exception(f"火烧云提醒任务异常: {e}")
