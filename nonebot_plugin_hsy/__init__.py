import re

from nonebot.plugin import PluginMetadata
from .config import Config

from nonebot import get_driver, on_command, on_message, on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageEvent,
)
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, RegexGroup

from . import api, store
from . import service  # noqa: F401
from .store import STATUS_MAP

__version__ = "26.8.2"

MAX_SUBS = 5

_ACTIONS = (
    "add",
    "添加",
    "rm",
    "删除",
    "refresh",
    "刷新",
    "list",
    "uadd",
    "urm",
    "info",
    "help",
    "菜单",
    "帮助",
)

__plugin_meta__ = PluginMetadata(
    # 基本信息（必填）
    name="火烧云",  # 插件名称
    description="火烧云/晚霞查询与定时提醒插件，支持订阅城市并在日落前 1 小时、30 分钟提醒",  # 插件介绍
    usage="发送【hsy help】获取插件菜单",  # 插件用法

    # 发布额外信息
    type="application",  # 插件分类
    # 发布必填，当前有效类型有：`library`（为其他插件编写提供功能），`application`（向机器人用户提供功能）。

    homepage="https://github.com/chaichaisi/nonebot-plugin-hsy",
    # 发布必填。

    config=Config,
    # 插件配置项类，如果有配置类则必须填写。

    supported_adapters={"~onebot.v11"},
    # 支持的适配器集合，其中 `~` 在此处代表前缀 `nonebot.adapters.`，其余适配器亦按此格式填写。
    # 若插件只使用了 NoneBot 基本抽象，应显式填写 None，否则应该列出插件支持的适配器。

    extra={
        "unique_name": "hsy",
        "author": "Chaichaisi <chaichaisi@qq.com>",
        "version": "26.8.2",
    }
)

_driver = get_driver()
_superusers = _driver.config.superusers

hsy = on_command("hsy", aliases={"火烧云", "晚霞"}, priority=5, block=True)
hsy_no_space = on_regex(
    r"^/?(?:hsy|火烧云|晚霞)(add|添加|rm|删除|refresh|刷新|list|uadd|urm|info|help|菜单|帮助)\s*(.*)$",
    flags=re.I,
    priority=6,
    block=True,
)

_MSG_RECORDER = on_message(priority=10, block=False)


@_MSG_RECORDER.handle()
async def _record_group(event: GroupMessageEvent) -> None:
    store.set_last_group(event.get_user_id(), event.group_id)


def _is_admin(user_id: str) -> bool:
    return user_id in _superusers


def _parse_args(text: str) -> tuple[str | None, str]:
    if not text:
        return None, ""
    for act in _ACTIONS:
        if text.startswith(act):
            return act, text[len(act) :].strip()
    return None, text


def _take_city(rest: str) -> str:
    return rest.split(maxsplit=1)[0] if rest else ""


async def _dispatch(
    matcher: Matcher, event: MessageEvent, bot: Bot, action: str | None, rest: str
) -> None:
    user_id = event.get_user_id()
    if action is None:
        city = _take_city(rest)
        if not city:
            await matcher.finish(
                "用法：hsy 城市 / hsy add 城市 / hsy rm 城市 / hsy 刷新 / hsy list / hsy info / hsy help"
            )
        await _query(matcher, city)
    elif action in ("add", "添加"):
        city = _take_city(rest)
        if not city:
            await matcher.finish("用法：hsy add 城市，例如：hsy add 重庆")
        await _add(matcher, user_id, city)
    elif action in ("rm", "删除"):
        city = _take_city(rest)
        if not city:
            await matcher.finish("用法：hsy rm 城市，例如：hsy rm 重庆")
        await _rm(matcher, user_id, city)
    elif action in ("refresh", "刷新"):
        await _refresh(matcher, bot, user_id)
    elif action == "list":
        await _list(matcher, event, bot, rest, user_id)
    elif action == "uadd":
        if not _is_admin(user_id):
            await matcher.finish("你没有权限使用该命令")
        await _admin_uadd(matcher, rest)
    elif action == "urm":
        if not _is_admin(user_id):
            await matcher.finish("你没有权限使用该命令")
        await _admin_urm(matcher, rest)
    elif action == "info":
        await _info(matcher)
    elif action in ("help", "菜单", "帮助"):
        await _help(matcher, user_id)


@hsy.handle()
async def _handle(
    matcher: Matcher, event: MessageEvent, bot: Bot, args: Message = CommandArg()
) -> None:
    text = args.extract_plain_text().strip()
    action, rest = _parse_args(text)
    await _dispatch(matcher, event, bot, action, rest)


@hsy_no_space.handle()
async def _handle_no_space(
    matcher: Matcher,
    event: MessageEvent,
    bot: Bot,
    matched: RegexGroup = RegexGroup(),
) -> None:
    action = matched.group(1)
    rest = matched.group(2).strip()
    await _dispatch(matcher, event, bot, action, rest)


async def _add(matcher: Matcher, user_id: str, city: str) -> None:
    if not _is_admin(user_id) and len(store.get_subscriptions(user_id)) >= MAX_SUBS:
        await matcher.finish(f"每个用户最多订阅 {MAX_SUBS} 个城市（超级管理员不限）")
    is_new, _ = store.add_subscription(user_id, city, "user")
    if not is_new:
        await matcher.finish(f"{city} 已在你的订阅列表中")
    await matcher.finish(
        f"已订阅 {city}\n日落前 1小时、30分钟 会准时提醒你"
    )


async def _rm(matcher: Matcher, user_id: str, city: str) -> None:
    if not store.remove_subscription(user_id, city):
        await matcher.finish(f"未找到 {city} 的订阅")
    await matcher.finish(f"已删除 {city} 订阅，相关提醒任务已取消")


async def _refresh(matcher: Matcher, bot: Bot, user_id: str) -> None:
    subs = store.get_subscriptions(user_id)
    if not subs:
        await matcher.finish("你还没有任何订阅，先试试 hsy add 城市")
    lines = ["━━ 火烧云 · 刷新 ━━"]
    for sub in subs:
        city = sub["city"]
        try:
            info = await api.fetch_sunset(city)
        except Exception:
            lines.append(f"{city}: 数据源暂时不可用")
            continue
        if not info["time"] or info["time"] == "无数据":
            lines.append(f"{city}: 暂无可用数据")
            continue
        ok = await service.send_refresh(bot, user_id, sub, info)
        lines.append(f"{city}: {'已发送' if ok else '发送失败'}")
    await matcher.finish("\n".join(lines))


async def _query(matcher: Matcher, city: str) -> None:
    try:
        info = await api.fetch_sunset(city)
    except Exception:
        await matcher.finish(
            f"{city} · 今日晚霞\n──────────────\n数据源暂时不可用，稍后再试吧"
        )
    if not info["time"] or info["time"] == "无数据":
        await matcher.finish(
            f"{city} · 今日晚霞\n──────────────\n暂无可用数据，稍后再来试试吧"
        )
    await matcher.finish(
        f"{city} · 今日晚霞\n──────────────\n"
        f"日落时间  {info['time']}\n"
        f"晚霞概率  {info['quality']}\n"
        f"晚霞质量  {info['aod']}\n"
        "──────────────\n抬头看天，别错过这场晚霞"
    )


async def _info(matcher: Matcher) -> None:
    await matcher.finish(
        "火烧云 / 晚霞查询插件\n"
        "──────────────\n"
        "插件名：nonebot-plugin-hsy\n"
        "包名：nonebot_plugin_hsy\n"
        "作者：Chaichaisi\n"
        "项目主页：https://github.com/chaichaisi/nonebot-plugin-hsy\n"
        "──────────────\n"
        "版权所有，严禁商用"
    )


async def _help(matcher: Matcher, user_id: str) -> None:
    text = (
        "火烧云 / 晚霞查询\n"
        "──────────────\n"
        "hsy 城市       直接查询\n"
        "hsy add 城市   订阅提醒(1小时/30分钟前,最多5个)\n"
        "hsy rm 城市    取消订阅\n"
        "hsy 刷新       立即获取所有订阅的最新数据\n"
        "hsy list       查看我的订阅(合并转发)\n"
        "hsy info       插件信息\n"
        "hsy help       本菜单\n"
        "──────────────\n"
        "命令可不加空格，如 hsyadd 城市 / hsy add城市"
    )
    if _is_admin(user_id):
        text += (
            "\n──────────────\n管理员：\n"
            "hsy list 用户id     查看指定用户订阅\n"
            "hsy uadd 用户id 城市  代加订阅\n"
            "hsy urm 用户id 城市   代删订阅"
        )
    await matcher.finish(text)


async def _list(
    matcher: Matcher, event: MessageEvent, bot: Bot, rest: str, user_id: str
) -> None:
    if _is_admin(user_id):
        target = _take_city(rest) if rest else None
    else:
        target = user_id
    subs = store.get_subscriptions(target)
    if not subs:
        if target is None:
            await matcher.finish("没有找到相关订阅")
        await matcher.finish("你还没有任何订阅")
    nodes: list[MessageSegment] = []
    for sub in subs:
        content = (
            f"用户 {sub['user_id']} | {sub['city']}\n"
            f"1小时: {STATUS_MAP.get(sub['remind_1h'], '未知')} | "
            f"30分钟: {STATUS_MAP.get(sub['remind_30m'], '未知')}"
        )
        nodes.append(
            MessageSegment.node_custom(
                user_id=event.self_id, nickname="火烧云", content=content
            )
        )
    for chunk in (nodes[i : i + 100] for i in range(0, len(nodes), 100)):
        if isinstance(event, GroupMessageEvent):
            await bot.call_api(
                "send_group_forward_msg",
                group_id=event.group_id,
                messages=chunk,
            )
        else:
            await bot.call_api(
                "send_private_forward_msg",
                user_id=event.user_id,
                messages=chunk,
            )
    await matcher.finish(f"共 {len(subs)} 条订阅")


async def _admin_uadd(matcher: Matcher, rest: str) -> None:
    parts = rest.split(maxsplit=1)
    if len(parts) != 2 or not parts[0].isdigit():
        await matcher.finish("用法：hsy uadd 用户id 城市")
    target, city = parts[0], _take_city(parts[1])
    if not _is_admin(target) and len(store.get_subscriptions(target)) >= MAX_SUBS:
        await matcher.finish(f"用户 {target} 已达订阅上限（{MAX_SUBS} 个）")
    is_new, _ = store.add_subscription(target, city, "admin")
    if not is_new:
        await matcher.finish(f"用户 {target} 已订阅 {city}")
    await matcher.finish(f"已为 用户 {target} 添加 {city} 订阅，将私聊/临时会话提醒")


async def _admin_urm(matcher: Matcher, rest: str) -> None:
    parts = rest.split(maxsplit=1)
    if len(parts) != 2 or not parts[0].isdigit():
        await matcher.finish("用法：hsy urm 用户id 城市")
    target, city = parts[0], _take_city(parts[1])
    if not store.remove_subscription(target, city):
        await matcher.finish(f"用户 {target} 未订阅 {city}")
    await matcher.finish(f"已删除 用户 {target} 的 {city} 订阅，相关提醒任务已取消")
