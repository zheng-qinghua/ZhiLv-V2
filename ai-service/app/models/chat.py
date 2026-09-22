"""对话式规划的 HTTP 入参(M2)。状态机与默认值解析在 M3/M4 落到 /chat 处理逻辑里。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChatTurnInput(BaseModel):
    thread_id: str                 # Java 侧 chat_sessions.id
    message: str = ""              # 用户文本;action=confirm 时可为空
    action: Literal["chat", "confirm"] = "chat"
