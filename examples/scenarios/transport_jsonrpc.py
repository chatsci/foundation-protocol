"""Scenario: in-process JSON-RPC dispatcher integration."""

from __future__ import annotations

from fp.app import FPServer
from fp.transport import JSONRPCDispatcher


def run_example() -> dict[str, object]:
    server = FPServer()
    dispatcher = JSONRPCDispatcher.from_server(server)

    ping_response = dispatcher.handle(
        {
            "jsonrpc": "2.0",
            "id": "ping-1",
            "method": "fp/ping",
            "params": {},
        }
    )
    missing_session_response = dispatcher.handle(
        {
            "jsonrpc": "2.0",
            "id": "sess-1",
            "method": "fp/sessions.get",
            "params": {"session_id": "sess-missing"},
        }
    )
    assert ping_response is not None
    assert missing_session_response is not None
    return {
        "ping": ping_response["result"],
        "missing_session_error_code": missing_session_response["error"]["data"]["fp"]["code"],
    }


def main() -> None:
    print(run_example())


if __name__ == "__main__":
    main()
