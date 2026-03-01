from __future__ import annotations

import unittest

from fp.protocol import FPError, FPErrorCode
from fp.transport import (
    WebsocketMessage,
    decode_message,
    decode_ws_message,
    encode_message,
    encode_ws_message,
    format_sse,
)


class StreamTransportTests(unittest.TestCase):
    def test_stdio_roundtrip(self) -> None:
        payload = {"a": 1, "b": "x"}
        encoded = encode_message(payload)
        decoded = decode_message(encoded)
        self.assertEqual(decoded, payload)

    def test_sse_format(self) -> None:
        out = format_sse("activity.completed", {"ok": True}, event_id="evt-1")
        self.assertIn("id: evt-1", out)
        self.assertIn("event: activity.completed", out)
        self.assertIn("data:", out)
        self.assertTrue(out.endswith("\n\n"))

    def test_websocket_roundtrip(self) -> None:
        encoded = encode_ws_message(WebsocketMessage(type="ping", payload={"n": 1}))
        decoded = decode_ws_message(encoded)
        self.assertEqual(decoded.type, "ping")
        self.assertEqual(decoded.payload["n"], 1)

    def test_websocket_decode_rejects_invalid_json(self) -> None:
        with self.assertRaises(FPError) as exc:
            decode_ws_message("not-json")
        self.assertIs(exc.exception.code, FPErrorCode.INVALID_ARGUMENT)


if __name__ == "__main__":
    unittest.main()
