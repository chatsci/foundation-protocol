from __future__ import annotations

import inspect
import unittest
from pathlib import Path

from fp.app import AsyncFPClient, AsyncFPServer


class AsyncTypingSurfaceTests(unittest.TestCase):
    def test_async_server_public_methods_do_not_use_kwargs_only_signatures(self) -> None:
        methods = [
            "initialize",
            "sessions_create",
            "sessions_join",
            "sessions_update",
            "activities_start",
            "activities_update",
            "activities_cancel",
            "activities_result",
            "events_stream",
            "events_read",
            "events_ack",
        ]
        for name in methods:
            signature = inspect.signature(getattr(AsyncFPServer, name))
            has_var_kw = any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
            self.assertFalse(has_var_kw, f"{name} should not expose **kwargs")

    def test_async_client_surface_has_explicit_named_parameters(self) -> None:
        signature = inspect.signature(AsyncFPClient.activity_start)
        expected = {"session_id", "owner_entity_id", "initiator_entity_id", "operation", "input_payload", "auto_execute"}
        self.assertTrue(expected.issubset(set(signature.parameters.keys())))

    def test_async_runtime_path_avoids_thread_bridge_for_core_engines(self) -> None:
        root = Path(__file__).resolve().parents[2]
        files = [
            root / "src/fp/app/async_server.py",
            root / "src/fp/runtime/async_session_engine.py",
            root / "src/fp/runtime/async_activity_engine.py",
            root / "src/fp/runtime/async_event_engine.py",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("to_thread(", text, f"{path.name} should use native async path")


if __name__ == "__main__":
    unittest.main()
