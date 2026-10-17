import json

from pydantic import BaseModel, field_validator

from nonebot import get_plugin_config

DEFAULT_API_URL = (
    "https://sunsetbot.top/?query_id={query_id}"
    "&intend=select_city&query_city={citys}"
    "&event_date=None&event=set_1&times=None"
)


class Config(BaseModel):
    hsy_data_path: str = "hsy_data.json"
    hsy_refresh_interval: int = 1
    hsy_bot_id: str = ""
    hsy_api_url: str = DEFAULT_API_URL
    hsy_field_template: dict[str, str] = {}

    @field_validator("hsy_bot_id", "hsy_data_path", "hsy_api_url", mode="before")
    @classmethod
    def _to_str(cls, v: object) -> object:
        if v is None:
            return ""
        return str(v)

    @field_validator("hsy_field_template", mode="before")
    @classmethod
    def _parse_field_template(cls, v: object) -> dict[str, str]:
        if not v:
            return {}
        if isinstance(v, dict):
            return {str(k): str(x) for k, x in v.items()}
        if isinstance(v, str):
            try:
                d = json.loads(v)
            except json.JSONDecodeError:
                return {}
            if isinstance(d, dict):
                return {str(k): str(x) for k, x in d.items()}
        return {}


config = get_plugin_config(Config)
