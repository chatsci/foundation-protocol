"""Async wrapper for ActivityEngine."""

from __future__ import annotations

from typing import Any

from fp.protocol import Activity, ActivityState
from fp.runtime.activity_engine import ActivityEngine
from fp.stores.interfaces import ActivityStore


class AsyncActivityEngine:
    def __init__(self, store: ActivityStore) -> None:
        self._engine = ActivityEngine(store)

    async def start(
        self,
        *,
        activity_id: str,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict[str, Any],
    ) -> Activity:
        return self._engine.start(
            activity_id=activity_id,
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
        )

    async def get(self, activity_id: str) -> Activity:
        return self._engine.get(activity_id)

    async def transition(
        self,
        activity_id: str,
        *,
        next_state: ActivityState | str,
        status_message: str | None = None,
        patch: dict[str, Any] | None = None,
    ) -> Activity:
        return self._engine.transition(
            activity_id,
            next_state=next_state,
            status_message=status_message,
            patch=patch,
        )

    async def complete(
        self,
        activity_id: str,
        *,
        result_payload: dict[str, Any] | None = None,
        result_ref: str | None = None,
    ) -> Activity:
        return self._engine.complete(
            activity_id,
            result_payload=result_payload,
            result_ref=result_ref,
        )

    async def fail(self, activity_id: str, *, message: str, details: dict[str, Any] | None = None) -> Activity:
        return self._engine.fail(activity_id, message=message, details=details)

    async def cancel(self, activity_id: str, *, reason: str | None = None) -> Activity:
        return self._engine.cancel(activity_id, reason=reason)

    async def list(
        self,
        *,
        session_id: str | None = None,
        state: ActivityState | None = None,
        owner_entity_id: str | None = None,
    ) -> list[Activity]:
        return self._engine.list(
            session_id=session_id,
            state=state,
            owner_entity_id=owner_entity_id,
        )
