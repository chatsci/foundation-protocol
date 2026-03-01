"""Async facade for FPServer with native async activity dispatch path."""

from __future__ import annotations

from typing import Any, Callable

from fp.protocol import Activity, ActivityState, Entity, FPEvent, Session, SessionBudget, SessionState
from fp.runtime import AsyncDispatchEngine

from .activity_orchestrator import ActivityStartRequest, AsyncActivityStartOrchestrator
from .server import FPServer, _new_id


class AsyncFPServer:
    def __init__(self, server: FPServer | None = None, **server_kwargs: Any) -> None:
        self._server = server or FPServer(**server_kwargs)
        self._dispatch = AsyncDispatchEngine()
        self._activity_orchestrator = AsyncActivityStartOrchestrator(server=self._server, dispatch=self._dispatch)

    @property
    def sync_server(self) -> FPServer:
        return self._server

    @property
    def fp_version(self) -> str:
        return self._server.fp_version

    def register_operation(self, name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        # Keep sync runtime interoperability (HTTP publish and sync clients)
        # while enabling true async handler execution for async entrypoints.
        self._server.register_operation(name, handler)
        self._dispatch.register(name, handler)

    def set_token_budget_enforcer(self, enforcer: Callable[[dict[str, Any]], None] | None) -> None:
        self._server.set_token_budget_enforcer(enforcer)

    async def initialize(
        self,
        *,
        supported_versions: list[str],
        entity_id: str,
        capabilities: dict[str, Any] | None = None,
        supported_profiles: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._server.initialize(
            supported_versions=supported_versions,
            entity_id=entity_id,
            capabilities=capabilities,
            supported_profiles=supported_profiles,
        )

    async def register_entity(self, entity: Entity) -> Entity:
        return self._server.register_entity(entity)

    async def get_entity(self, entity_id: str) -> Entity:
        return self._server.get_entity(entity_id)

    async def sessions_create(
        self,
        *,
        participants: set[str],
        roles: dict[str, set[str]],
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        session_id: str | None = None,
    ) -> Session:
        return self._server.sessions_create(
            participants=participants,
            roles=roles,
            policy_ref=policy_ref,
            budget=budget,
            session_id=session_id,
        )

    async def sessions_join(self, *, session_id: str, entity_id: str, roles: set[str] | None = None) -> Session:
        return self._server.sessions_join(session_id=session_id, entity_id=entity_id, roles=roles)

    async def sessions_update(
        self,
        *,
        session_id: str,
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        state: SessionState | None = None,
        roles_patch: dict[str, set[str]] | None = None,
    ) -> Session:
        return self._server.sessions_update(
            session_id=session_id,
            policy_ref=policy_ref,
            budget=budget,
            state=state,
            roles_patch=roles_patch,
        )

    async def sessions_get(self, session_id: str) -> Session:
        return self._server.sessions_get(session_id)

    async def sessions_list_page(self, *, limit: int = 100, cursor: str | None = None) -> dict[str, Any]:
        return self._server.sessions_list_page(limit=limit, cursor=cursor)

    async def activities_start(
        self,
        *,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict[str, Any],
        activity_id: str | None = None,
        idempotency_key: str | None = None,
        auto_execute: bool = True,
    ) -> Activity:
        request = ActivityStartRequest(
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
            activity_id=activity_id or _new_id("act"),
            idempotency_key=idempotency_key,
            auto_execute=auto_execute,
        )
        return await self._activity_orchestrator.start(request)

    async def activities_update(
        self,
        *,
        activity_id: str,
        state: ActivityState,
        status_message: str | None = None,
        patch: dict[str, Any] | None = None,
        producer_entity_id: str | None = None,
    ) -> Activity:
        return self._server.activities_update(
            activity_id=activity_id,
            state=state,
            status_message=status_message,
            patch=patch,
            producer_entity_id=producer_entity_id,
        )

    async def activities_cancel(self, *, activity_id: str, reason: str | None = None) -> Activity:
        return self._server.activities_cancel(activity_id=activity_id, reason=reason)

    async def activities_result(self, *, activity_id: str) -> dict[str, Any]:
        return self._server.activities_result(activity_id=activity_id)

    async def activities_list_page(
        self,
        *,
        session_id: str | None = None,
        state: ActivityState | None = None,
        owner_entity_id: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return self._server.activities_list_page(
            session_id=session_id,
            state=state,
            owner_entity_id=owner_entity_id,
            limit=limit,
            cursor=cursor,
        )

    async def events_stream(
        self,
        *,
        session_id: str,
        activity_id: str | None = None,
        from_event_id: str | None = None,
    ) -> dict[str, Any]:
        return self._server.events_stream(
            session_id=session_id,
            activity_id=activity_id,
            from_event_id=from_event_id,
        )

    async def events_read(self, *, stream_id: str, limit: int = 200) -> list[FPEvent]:
        return self._server.events_read(stream_id=stream_id, limit=limit)

    async def events_ack(self, *, stream_id: str, event_ids: list[str]) -> dict[str, bool]:
        return self._server.events_ack(stream_id=stream_id, event_ids=event_ids)
