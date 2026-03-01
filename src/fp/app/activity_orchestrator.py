"""Activity start orchestration extracted from FPServer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, TYPE_CHECKING

from fp.policy import PolicyHook
from fp.protocol import Activity, ActivityState, FPError, FPErrorCode, SessionState
from fp.runtime import AsyncDispatchEngine, DispatchContext

if TYPE_CHECKING:
    from .server import FPServer


@dataclass(slots=True)
class ActivityStartRequest:
    session_id: str
    owner_entity_id: str
    initiator_entity_id: str
    operation: str
    input_payload: dict[str, Any]
    activity_id: str
    idempotency_key: str | None
    auto_execute: bool


class ActivityStartOrchestrator:
    """Coordinates validation, policy, execution, and evidence for activity start."""

    def __init__(self, server: "FPServer") -> None:
        self._server = server

    def start(self, request: ActivityStartRequest) -> Activity:
        session = self._validate_participants_and_session(request)
        self._server._enforce_token_budget(
            session=session,
            operation=request.operation,
            input_payload=request.input_payload,
        )

        cached_activity, fingerprint = self._check_idempotency(request)
        if cached_activity is not None:
            return cached_activity

        self._server._enforce_policy(
            hook=PolicyHook.PRE_INVOKE,
            actor_entity_id=request.initiator_entity_id,
            session_id=request.session_id,
            operation=request.operation,
            payload=request.input_payload,
        )

        activity = self._create_submitted_activity(request)
        activity = self._auto_execute_if_possible(request, activity)

        if request.idempotency_key:
            self._server.idempotency.store(request.idempotency_key, activity, fingerprint=fingerprint)
        return activity

    def _validate_participants_and_session(self, request: ActivityStartRequest):
        self._server._require_entity(request.owner_entity_id)
        self._server._require_entity(request.initiator_entity_id)
        session = self._server.sessions.get(request.session_id)
        if session.state is not SessionState.ACTIVE:
            raise FPError(
                FPErrorCode.INVALID_STATE_TRANSITION,
                message=f"cannot start activity in session state: {session.state.value}",
            )
        if request.owner_entity_id not in session.participants:
            raise FPError(
                FPErrorCode.AUTHZ_DENIED,
                message="activity owner must be a session participant",
                details={"session_id": request.session_id, "owner_entity_id": request.owner_entity_id},
            )
        if request.initiator_entity_id not in session.participants:
            raise FPError(
                FPErrorCode.AUTHZ_DENIED,
                message="activity initiator must be a session participant",
                details={"session_id": request.session_id, "initiator_entity_id": request.initiator_entity_id},
            )
        return session

    def _check_idempotency(self, request: ActivityStartRequest) -> tuple[Activity | None, str]:
        fingerprint = self._server._idempotency_fingerprint(
            session_id=request.session_id,
            owner_entity_id=request.owner_entity_id,
            initiator_entity_id=request.initiator_entity_id,
            operation=request.operation,
            input_payload=request.input_payload,
        )
        if not request.idempotency_key:
            return None, fingerprint

        cached = self._server.idempotency.check(request.idempotency_key, fingerprint=fingerprint)
        if cached is None:
            return None, fingerprint
        value = cached.value
        if isinstance(value, Activity):
            return value, fingerprint
        return None, fingerprint

    def _create_submitted_activity(self, request: ActivityStartRequest) -> Activity:
        activity = self._server.activities.start(
            activity_id=request.activity_id,
            session_id=request.session_id,
            owner_entity_id=request.owner_entity_id,
            initiator_entity_id=request.initiator_entity_id,
            operation=request.operation,
            input_payload=request.input_payload,
        )
        self._server._emit_event(
            event_type="activity.submitted",
            session_id=request.session_id,
            activity_id=activity.activity_id,
            producer_entity_id=request.initiator_entity_id,
            payload={"operation": request.operation},
        )
        return activity

    def _auto_execute_if_possible(self, request: ActivityStartRequest, activity: Activity) -> Activity:
        if not request.auto_execute:
            return activity
        if not self._server.dispatch.has_handler(request.operation):
            return activity

        activity = self._server.activities.transition(activity.activity_id, next_state=ActivityState.WORKING)
        self._server._emit_event(
            event_type="activity.working",
            session_id=request.session_id,
            activity_id=activity.activity_id,
            producer_entity_id=request.owner_entity_id,
            payload={"operation": request.operation},
        )

        context = DispatchContext(
            session_id=request.session_id,
            activity_id=activity.activity_id,
            operation=request.operation,
            actor_entity_id=request.initiator_entity_id,
        )
        try:
            output = self._server.dispatch.execute(context=context, input_payload=request.input_payload)
        except Exception as exc:  # pragma: no cover - defensive path
            activity = self._server.activities.fail(activity.activity_id, message=str(exc))
            self._server._emit_event(
                event_type="activity.failed",
                session_id=request.session_id,
                activity_id=activity.activity_id,
                producer_entity_id=request.owner_entity_id,
                payload={"error": str(exc)},
            )
            return activity

        if isinstance(output, dict) and output.get("state") == "working":
            return activity

        result_payload = output if isinstance(output, dict) else {"value": output}
        compacted = self._server._context_compactor.compact(result_payload)
        activity = self._server.activities.complete(
            activity.activity_id,
            result_payload=compacted.inline_payload,
            result_ref=compacted.result_ref,
        )
        usage = self._server.token_meter.measure(
            input_payload=request.input_payload,
            output_payload=compacted.inline_payload or {},
        )
        estimated_cost = self._server.cost_meter.estimate(usage)
        self._server._emit_event(
            event_type="activity.completed",
            session_id=request.session_id,
            activity_id=activity.activity_id,
            producer_entity_id=request.owner_entity_id,
            payload={
                "usage": asdict(usage),
                "estimated_cost": round(estimated_cost, 8),
                "result_ref": compacted.result_ref,
                "compacted": compacted.compacted,
            },
        )
        return activity


class AsyncActivityStartOrchestrator:
    """Async activity start orchestration for native async server paths."""

    def __init__(self, *, server: "FPServer", dispatch: AsyncDispatchEngine) -> None:
        self._server = server
        self._dispatch = dispatch

    async def start(self, request: ActivityStartRequest) -> Activity:
        session = self._validate_participants_and_session(request)
        self._server._enforce_token_budget(
            session=session,
            operation=request.operation,
            input_payload=request.input_payload,
        )

        cached_activity, fingerprint = self._check_idempotency(request)
        if cached_activity is not None:
            return cached_activity

        self._server._enforce_policy(
            hook=PolicyHook.PRE_INVOKE,
            actor_entity_id=request.initiator_entity_id,
            session_id=request.session_id,
            operation=request.operation,
            payload=request.input_payload,
        )

        activity = self._create_submitted_activity(request)
        activity = await self._auto_execute_if_possible(request, activity)

        if request.idempotency_key:
            self._server.idempotency.store(request.idempotency_key, activity, fingerprint=fingerprint)
        return activity

    def _validate_participants_and_session(self, request: ActivityStartRequest):
        self._server._require_entity(request.owner_entity_id)
        self._server._require_entity(request.initiator_entity_id)
        session = self._server.sessions.get(request.session_id)
        if session.state is not SessionState.ACTIVE:
            raise FPError(
                FPErrorCode.INVALID_STATE_TRANSITION,
                message=f"cannot start activity in session state: {session.state.value}",
            )
        if request.owner_entity_id not in session.participants:
            raise FPError(
                FPErrorCode.AUTHZ_DENIED,
                message="activity owner must be a session participant",
                details={"session_id": request.session_id, "owner_entity_id": request.owner_entity_id},
            )
        if request.initiator_entity_id not in session.participants:
            raise FPError(
                FPErrorCode.AUTHZ_DENIED,
                message="activity initiator must be a session participant",
                details={"session_id": request.session_id, "initiator_entity_id": request.initiator_entity_id},
            )
        return session

    def _check_idempotency(self, request: ActivityStartRequest) -> tuple[Activity | None, str]:
        fingerprint = self._server._idempotency_fingerprint(
            session_id=request.session_id,
            owner_entity_id=request.owner_entity_id,
            initiator_entity_id=request.initiator_entity_id,
            operation=request.operation,
            input_payload=request.input_payload,
        )
        if not request.idempotency_key:
            return None, fingerprint

        cached = self._server.idempotency.check(request.idempotency_key, fingerprint=fingerprint)
        if cached is None:
            return None, fingerprint
        value = cached.value
        if isinstance(value, Activity):
            return value, fingerprint
        return None, fingerprint

    def _create_submitted_activity(self, request: ActivityStartRequest) -> Activity:
        activity = self._server.activities.start(
            activity_id=request.activity_id,
            session_id=request.session_id,
            owner_entity_id=request.owner_entity_id,
            initiator_entity_id=request.initiator_entity_id,
            operation=request.operation,
            input_payload=request.input_payload,
        )
        self._server._emit_event(
            event_type="activity.submitted",
            session_id=request.session_id,
            activity_id=activity.activity_id,
            producer_entity_id=request.initiator_entity_id,
            payload={"operation": request.operation},
        )
        return activity

    async def _auto_execute_if_possible(self, request: ActivityStartRequest, activity: Activity) -> Activity:
        if not request.auto_execute:
            return activity
        if not self._dispatch.has_handler(request.operation):
            return activity

        activity = self._server.activities.transition(activity.activity_id, next_state=ActivityState.WORKING)
        self._server._emit_event(
            event_type="activity.working",
            session_id=request.session_id,
            activity_id=activity.activity_id,
            producer_entity_id=request.owner_entity_id,
            payload={"operation": request.operation},
        )

        context = DispatchContext(
            session_id=request.session_id,
            activity_id=activity.activity_id,
            operation=request.operation,
            actor_entity_id=request.initiator_entity_id,
        )
        try:
            output = await self._dispatch.execute(context=context, input_payload=request.input_payload)
        except Exception as exc:  # pragma: no cover - defensive path
            activity = self._server.activities.fail(activity.activity_id, message=str(exc))
            self._server._emit_event(
                event_type="activity.failed",
                session_id=request.session_id,
                activity_id=activity.activity_id,
                producer_entity_id=request.owner_entity_id,
                payload={"error": str(exc)},
            )
            return activity

        if isinstance(output, dict) and output.get("state") == "working":
            return activity

        result_payload = output if isinstance(output, dict) else {"value": output}
        compacted = self._server._context_compactor.compact(result_payload)
        activity = self._server.activities.complete(
            activity.activity_id,
            result_payload=compacted.inline_payload,
            result_ref=compacted.result_ref,
        )
        usage = self._server.token_meter.measure(
            input_payload=request.input_payload,
            output_payload=compacted.inline_payload or {},
        )
        estimated_cost = self._server.cost_meter.estimate(usage)
        self._server._emit_event(
            event_type="activity.completed",
            session_id=request.session_id,
            activity_id=activity.activity_id,
            producer_entity_id=request.owner_entity_id,
            payload={
                "usage": asdict(usage),
                "estimated_cost": round(estimated_cost, 8),
                "result_ref": compacted.result_ref,
                "compacted": compacted.compacted,
            },
        )
        return activity


__all__ = ["ActivityStartOrchestrator", "ActivityStartRequest", "AsyncActivityStartOrchestrator"]
