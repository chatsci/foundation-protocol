from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.protocol import ActivityState, EntityKind, FPError, FPErrorCode


def _register_basics(server: FPServer) -> str:
    server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
    server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
    session = server.sessions_create(
        participants={"fp:agent:a", "fp:agent:b"},
        roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
    )
    return session.session_id


class CoreConformanceTests(unittest.TestCase):
    def test_invalid_activity_transition_is_rejected(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)
        server.register_operation("task.noop", lambda _: {"ok": True})

        activity = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.noop",
            input_payload={},
            auto_execute=False,
        )

        with self.assertRaises(FPError) as exc:
            server.activities_update(activity_id=activity.activity_id, state=ActivityState.COMPLETED)

        self.assertIs(exc.exception.code, FPErrorCode.INVALID_STATE_TRANSITION)

    def test_resubscribe_replays_from_last_ack_position(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)

        server.emit_event(
            event_type="custom.e1",
            session_id=session_id,
            producer_entity_id="fp:agent:a",
            payload={"n": 1},
        )
        server.emit_event(
            event_type="custom.e2",
            session_id=session_id,
            producer_entity_id="fp:agent:a",
            payload={"n": 2},
        )

        stream = server.events_stream(session_id=session_id)
        first_batch = server.events_read(stream_id=stream["stream_id"], limit=1)
        self.assertEqual(len(first_batch), 1)

        server.events_ack(stream_id=stream["stream_id"], event_ids=[first_batch[0].event_id])
        server.events_resubscribe(stream_id=stream["stream_id"], last_event_id=first_batch[0].event_id)

        second_batch = server.events_read(stream_id=stream["stream_id"], limit=10)
        self.assertTrue(any(event.event_type == "custom.e2" for event in second_batch))

    def test_idempotency_key_returns_same_activity(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)
        server.register_operation("task.idempotent", lambda payload: {"value": payload["v"]})

        a1 = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.idempotent",
            input_payload={"v": 7},
            idempotency_key="idem-1",
        )
        a2 = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.idempotent",
            input_payload={"v": 7},
            idempotency_key="idem-1",
        )

        self.assertEqual(a1.activity_id, a2.activity_id)
        self.assertEqual(a2.result_payload, {"value": 7})

    def test_backpressure_protects_streams(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)

        for i in range(600):
            server.emit_event(
                event_type="custom.spam",
                session_id=session_id,
                producer_entity_id="fp:agent:a",
                payload={"i": i},
            )

        stream = server.events_stream(session_id=session_id)
        with self.assertRaises(FPError) as exc:
            server.events_read(stream_id=stream["stream_id"], limit=600)
        self.assertIs(exc.exception.code, FPErrorCode.BACKPRESSURE)

    def test_idempotency_key_conflict_is_rejected(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)
        server.register_operation("task.idempotent", lambda payload: {"value": payload["v"]})

        server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.idempotent",
            input_payload={"v": 1},
            idempotency_key="idem-conflict",
        )

        with self.assertRaises(FPError) as exc:
            server.activities_start(
                session_id=session_id,
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.idempotent",
                input_payload={"v": 2},
                idempotency_key="idem-conflict",
            )
        self.assertIs(exc.exception.code, FPErrorCode.CONFLICT)

    def test_idempotency_replays_failed_activity_without_reexecution(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)
        calls = {"count": 0}

        def flaky_handler(_: dict) -> dict:
            calls["count"] += 1
            raise RuntimeError("boom")

        server.register_operation("task.flaky", flaky_handler)

        first = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.flaky",
            input_payload={"x": 1},
            idempotency_key="idem-fail",
        )
        second = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.flaky",
            input_payload={"x": 1},
            idempotency_key="idem-fail",
        )

        self.assertEqual(calls["count"], 1)
        self.assertEqual(first.activity_id, second.activity_id)
        self.assertIs(first.state, ActivityState.FAILED)

    def test_server_entity_id_is_used_for_runtime_events(self) -> None:
        server = FPServer(server_entity_id="fp:system:test-runtime")
        session_id = _register_basics(server)

        stream = server.events_stream(session_id=session_id)
        events = server.events_read(stream_id=stream["stream_id"], limit=20)
        session_created = next(event for event in events if event.event_type == "session.created")

        self.assertEqual(session_created.producer_entity_id, "fp:system:test-runtime")

    def test_sessions_create_fills_missing_roles_with_participant(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))

        session = server.sessions_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"coordinator"}},
        )

        self.assertEqual(session.roles["fp:agent:b"], {"participant"})

    def test_sessions_create_rejects_roles_for_non_participants(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))

        with self.assertRaises(FPError) as exc:
            server.sessions_create(
                participants={"fp:agent:a", "fp:agent:b"},
                roles={
                    "fp:agent:a": {"coordinator"},
                    "fp:agent:c": {"observer"},
                },
            )
        self.assertIs(exc.exception.code, FPErrorCode.INVALID_ARGUMENT)

    def test_events_read_rejects_non_positive_limit(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)
        stream = server.events_stream(session_id=session_id)

        with self.assertRaises(FPError) as exc:
            server.events_read(stream_id=stream["stream_id"], limit=0)
        self.assertIs(exc.exception.code, FPErrorCode.INVALID_ARGUMENT)

    def test_idempotency_replays_working_activity_without_reexecution(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)
        calls = {"count": 0}

        def long_running(_: dict) -> dict:
            calls["count"] += 1
            return {"state": "working"}

        server.register_operation("task.long", long_running)

        first = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.long",
            input_payload={"x": 1},
            idempotency_key="idem-working",
        )
        second = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.long",
            input_payload={"x": 1},
            idempotency_key="idem-working",
        )

        self.assertEqual(calls["count"], 1)
        self.assertEqual(first.activity_id, second.activity_id)
        self.assertIs(first.state, ActivityState.WORKING)

    def test_sessions_create_rejects_unregistered_participant(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))

        with self.assertRaises(FPError) as exc:
            server.sessions_create(
                participants={"fp:agent:a", "fp:agent:ghost"},
                roles={"fp:agent:a": {"coordinator"}, "fp:agent:ghost": {"worker"}},
            )
        self.assertIs(exc.exception.code, FPErrorCode.NOT_FOUND)

    def test_activity_start_rejects_unknown_session(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))

        with self.assertRaises(FPError) as exc:
            server.activities_start(
                session_id="sess-missing",
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.any",
                input_payload={},
            )
        self.assertIs(exc.exception.code, FPErrorCode.NOT_FOUND)

    def test_activity_start_rejects_non_participant_owner(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)
        server.register_entity(make_default_entity("fp:agent:c", EntityKind.AGENT))

        with self.assertRaises(FPError) as exc:
            server.activities_start(
                session_id=session_id,
                owner_entity_id="fp:agent:c",
                initiator_entity_id="fp:agent:a",
                operation="task.any",
                input_payload={},
            )
        self.assertIs(exc.exception.code, FPErrorCode.AUTHZ_DENIED)

    def test_events_stream_rejects_unknown_session(self) -> None:
        server = FPServer()
        with self.assertRaises(FPError) as exc:
            server.events_stream(session_id="sess-missing")
        self.assertIs(exc.exception.code, FPErrorCode.NOT_FOUND)

    def test_settlement_rejects_unknown_receipt_refs(self) -> None:
        server = FPServer()
        with self.assertRaises(FPError) as exc:
            server.settlements_create(
                receipt_refs=["rcpt-missing"],
                settlement_ref="payment://missing",
            )
        self.assertIs(exc.exception.code, FPErrorCode.NOT_FOUND)

    def test_sessions_update_rejects_unknown_roles_patch_entity(self) -> None:
        server = FPServer()
        session_id = _register_basics(server)
        with self.assertRaises(FPError) as exc:
            server.sessions_update(
                session_id=session_id,
                roles_patch={"fp:agent:ghost": {"observer"}},
            )
        self.assertIs(exc.exception.code, FPErrorCode.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
