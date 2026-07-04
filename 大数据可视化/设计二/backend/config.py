from __future__ import annotations

import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:wzh2004828@127.0.0.1:3306/traffic_db?charset=utf8mb4",
)
API_PREFIX = "/api"
TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Shanghai")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "30"))
DEEPSEEK_SYSTEM_PROMPT = os.getenv(
    "DEEPSEEK_SYSTEM_PROMPT",
    "你是一个中文交通问答助手，只能根据给定的实时交通数据、预警和绕行推荐回答。回答要简洁、准确、可执行，优先给出结论，再补一句原因或建议。",
)
