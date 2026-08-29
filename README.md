<div align="center">
  <a href="https://github.com/chaichaisi/nonebot-plugin-hsy"><img src="./logo.svg" width="240" height="240" alt="火烧云HSY Logo"></a>
  <br>
  <sub>Logo 版权：Chaichaisi 版权所有，严禁商用</sub>
  <br>
</div>

<div align="center">

# nonebot-plugin-hsy

_✨ 火烧云 / 晚霞 查询与定时提醒插件 ✨_


<a href="https://github.com/chaichaisi/nonebot-plugin-hsy/stargazers">
    <img alt="GitHub stars" src="https://img.shields.io/github/stars/chaichaisi/nonebot-plugin-hsy?color=%2300BFFF&style=flat-square">
</a>
<a href="https://github.com/chaichaisi/nonebot-plugin-hsy/issues">
    <img alt="GitHub issues" src="https://img.shields.io/github/issues/chaichaisi/nonebot-plugin-hsy?color=Emerald%20green&style=flat-square">
</a>
<a href="https://github.com/chaichaisi/nonebot-plugin-hsy/network">
    <img alt="GitHub forks" src="https://img.shields.io/github/forks/chaichaisi/nonebot-plugin-hsy?color=%2300BFFF&style=flat-square">
</a>
<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/chaichaisi/nonebot-plugin-hsy.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-hsy">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-hsy.svg" alt="pypi">
</a>
<a href="https://www.python.org">
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">
</a>

</div>

## 🙏 致谢

- 感谢 [nonebot_plugin_smallapi](https://github.com/chaichaisi/nonebot_plugin_smallapi) 提供的 README 排版参考
- 感谢 [nonebot-plugin-template](https://github.com/A-kirami/nonebot-plugin-template) 项目模板

## 📖 前言及介绍

通过调用日落/晚霞数据接口，获取城市当天的日落时间、晚霞概率与晚霞质量。支持直接查询，也支持订阅城市，在日落前 1 小时、30 分钟自动提醒，让你不错过每一场晚霞。

## 🔧 开发环境

- NoneBot2：2.x
- Python：3.10+
- 操作系统：Linux / Windows / macOS
- 适配器：OneBot V11（NapCat / LLOneBot / Go-CQHTTP 等）

## 💿 安装

### 1. nb-cli 安装（推荐）

在你 bot 工程的文件夹下运行：

```
nb plugin install nonebot-plugin-hsy
```

### 2. pip 安装

```
pip install nonebot-plugin-hsy
```

若是默认 nb-cli 创建的 nonebot2 工程，在 `pyproject.toml` 的 `[tool.nonebot.plugins]` 中添加一行：

```toml
[tool.nonebot.plugins]
nonebot-plugin-hsy = ["nonebot_plugin_hsy"]
```

### 3. 本地安装（不推荐）

下载源码后，将 `nonebot_plugin_hsy` 目录放到 `你的bot/src/plugins/` 下即可。

## ⚙️ 配置

在 nonebot2 项目的 `.env` 文件中添加以下配置项（全部可选，不填用默认值）：

| 配置项 | 默认值 | 说明 |
|:---:|:---:|:---:|
| hsy_data_path | hsy/hsy_data.json | 订阅数据保存路径（相对 bot 运行目录） |
| hsy_refresh_interval | 1 | 提醒任务刷新间隔（分钟） |
| hsy_bot_id | 空 | 多 bot 在线时指定机器人 QQ 号，空则取第一个 |

示例：

```
hsy_data_path="hsy/hsy_data.json"
hsy_refresh_interval=1
```

机器人超管使用 nonebot 内置配置 `SUPERUSERS`，配置后即可使用管理命令。

如果希望命令不带 `/` 前缀直接输入（如 `hsy 重庆` 而不是 `/hsy 重庆`），在 `.env` 中设置 `COMMAND_START=[""]` 即可。

## 🎉 功能

1. 直接查询任意城市当天火烧云情况
2. 订阅城市，日落前 1 小时 / 30 分钟自动提醒（每个用户最多 5 个，超管不限）
3. 一键刷新，立即获取你所有订阅的最新数据
4. 无数据的订阅每 30 分钟自动重试，直至获取到数据后才开始提醒任务
5. 查看订阅：所有用户可查看自己的订阅，超管可查看全部或指定用户
6. 命令写法灵活：支持无空格写法（如 `hsyadd 城市`、`hsy add城市`），多余参数自动忽略

## 👉 命令

PS：命令起始符默认 `/`，若已配置 `COMMAND_START=[""]` 则直接输入命令即可。以下用 `hsy` 举例。

命令可不加空格，以下写法等价：`hsy add 秭归`、`hsy add秭归`、`hsyadd 秭归`、`hsyadd秭归`。多余的参数会被自动忽略（如 `hsy add 重庆 上海` 只订阅重庆）。

### 用户命令

| 命令 | 说明 |
|:---:|:---:|
| `hsy 城市` | 直接查询该城市火烧云情况 |
| `hsy add 城市` | 订阅城市，日落前1小时/30分钟各提醒一次 |
| `hsy rm 城市` | 取消订阅 |
| `hsy 刷新` | 立即获取你所有订阅的最新数据并发送给你 |
| `hsy list` | 查看你的订阅（合并转发，含提醒任务状态） |
| `hsy info` | 插件信息 |
| `hsy help` | 功能菜单 |

例如：`hsy add 重庆`、`hsy 上海`、`hsy 刷新`、`hsyadd秭归`。

### 管理员命令（超管可用）

| 命令 | 说明 |
|:---:|:---:|
| `hsy list 用户id` | 合并转发查看指定用户的订阅（不带参数则查看全部） |
| `hsy uadd 用户id 城市` | 为指定用户添加订阅 |
| `hsy urm 用户id 城市` | 删除指定用户的订阅 |

提醒任务状态：`即将` 还没到提醒时间，`完成` 提醒已发出，`失败` 提醒发出失败。

提醒发送优先级：私聊（好友）→ 临时会话（共同群）→ 群内 @（用户订阅）。管理员代加的订阅仅私聊/临时会话，失败则标记为失败并后台报错。

## 🚀 高阶玩法：数据源与字段模板

插件按「JSON 示例模板」方式访问数据源：模板声明插件需要的字段（`date` / `time` / `quality` / `aod`）在返回 JSON 中的位置，字段值是「路径」，路径用 `.` 分隔，支持嵌套与数组下标。

### 内置接口（开箱即用）

`hsy_api_url` 不配置时，插件使用内置接口 sunsetbot.top，`query_id` 自动生成随机数，`{citys}` 自动替换为 URL 编码的城市名：

```
https://sunsetbot.top/?query_id={query_id}&intend=select_city&query_city={citys}&event_date=None&event=set_1&times=None
```

内置接口返回结构（无该次预报时各字段为 `-`）：

```json
{ "status": "ok", "tb_event_time": "2026-08-29 18:24", "tb_quality": "0.0（不烧）", "tb_aod": "0.197（水晶）" }
```

插件自动从 `tb_event_time` 拆出日期与 `HH:MM` 时间，`-` 视为暂无数据。

### 自定义 API

如果有自己的数据源，配置 `hsy_api_url`（`{city}` 占位符会被替换为 URL 编码的城市名）：

```
hsy_api_url="https://your-api.example.com/sunset?city={city}"
```

自定义接口的返回结构若与内置不同，用 `hsy_field_template` 声明「插件字段 → JSON 路径」模板，值为与返回结构对应的路径示例：

| 配置项 | 说明 |
|:---:|:---:|
| `hsy_api_url` | 数据接口链接，`{city}` / `{citys}` 为城市占位符，`{query_id}` 自动生成随机数；不配置使用内置 sunsetbot.top 接口 |
| `hsy_field_template` | JSON 示例模板，形如 `{"time": "result.sunset_time", ...}`，声明各字段在返回 JSON 中的路径；留空使用内置默认模板（对应 `tb_event_time` / `tb_quality` / `tb_aod`） |

例如你的接口返回：

```json
{ "status": 200, "result": { "date": "2026-08-30", "sunset_time": "2026-08-30 19:20", "rate": 0.72, "desc": "中霞" } }
```

则需配置：

```
hsy_api_url="https://your-api.example.com/sunset?city={city}"
hsy_field_template='{"date":"result.date","time":"result.sunset_time","quality":"result.rate","aod":"result.desc"}'
```

模板字段路径为「示例」写法，插件会按路径从真实响应中取对应位置的值。字段缺失、值为空或 `-` 时，查询会提示「暂无可用数据」，订阅会每 30 分钟自动重试。

数组取下标：`{"time": "list.0.time"}` 表示取 `list[0].time`。

## 📝 更新日志

<details>
<summary>展开/收起</summary>

### 26.8.2

- 新增 `hsy 刷新` 命令：立即获取当前用户所有订阅的最新数据
- 订阅上限：每个用户最多 5 个订阅，超级管理员不限
- `hsy list` 对所有用户开放：普通用户查看自己的订阅，超管可查看全部或指定用户，均合并转发
- 无数据的订阅每 30 分钟自动重试，直至获取到数据后才进入提醒流程
- 命令支持无空格写法（`hsyadd 城市` / `hsy add城市`），多余参数自动忽略
- 订阅数据默认保存至 `hsy/hsy_data.json`（相对 bot 运行目录）
- 数据源改为「JSON 示例模板」方式：内置使用 sunsetbot.top 接口（`query_id` 自动随机、`{citys}` 自动替换城市），自定义接口用 `hsy_field_template` 声明各字段在返回 JSON 中的路径，支持嵌套与数组下标
- Logo 简化重绘

### 0.0.0

- 插件初次发布

</details>

## 版权声明

Logo 与插件本体版权归 Chaichaisi 所有，基于 LGPL-2.1 协议开源，**严禁商用**。
