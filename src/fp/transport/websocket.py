"""WebSocket message helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from fp.protocol import FPError, FPErrorCode


@dataclass(slots=True)
class WebsocketMessage:
    type: str
    payload: dict[str, Any]


def encode_ws_message(message: WebsocketMessage | dict[str, Any]) -> str:
    if isinstance(message, WebsocketMessage):
        body = {"type": message.type, "payload": message.payload}
    else:
        body = dict(message)
    return json.dumps(body, separators=(",", ":"))


def decode_ws_message(raw: str) -> WebsocketMessage:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FPError(FPErrorCode.INVALID_ARGUMENT, message="websocket message is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise FPError(FPErrorCode.INVALID_ARGUMENT, "websocket message must be an object")
    message_type = parsed.get("type")
    payload = parsed.get("payload", {})
    if not isinstance(message_type, str) or not message_type:
        raise FPError(FPErrorCode.INVALID_ARGUMENT, "websocket message.type must be non-empty string")
    if not isinstance(payload, dict):
        raise FPError(FPErrorCode.INVALID_ARGUMENT, "websocket message.payload must be an object")
    return WebsocketMessage(type=message_type, payload=payload)


__all__ = ["WebsocketMessage", "encode_ws_message", "decode_ws_message"]
