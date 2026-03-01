"""Async FP client API."""

from __future__ import annotations

import asyncio
import ssl
from dataclasses import asdict, is_dataclass
from typing import Any

from fp.app.client import FPClient
from fp.protocol import ActivityState, SessionBudget
from fp.transport.reliability import CircuitBreaker, RetryPolicy

from .async_server import AsyncFPServer


def _to_payload(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


class AsyncFPClient:
    def __init__(self, *, server: AsyncFPServer | None = None, client: FPClient | None = None) -> None:
        if server is None and client is None:
            raise ValueError("AsyncFPClient requires server or client")
        self._server = server
        self._client = client

    @classmethod
    def from_inproc(cls, server: AsyncFPServer | Any) -> "AsyncFPClient":
        if isinstance(server, AsyncFPServer):
            return cls(server=server)
        return cls(client=FPClient.from_inproc(server))

    @classmethod
    def from_http_jsonrpc(
        cls,
        rpc_url: str,
        *,
        timeout_seconds: float = 10.0,
        headers: dict[str, str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        keep_alive: bool = True,
    ) -> "AsyncFPClient":
        return cls(
            client=FPClient.from_http_jsonrpc(
                rpc_url,
                timeout_seconds=timeout_seconds,
                headers=headers,
                ssl_context=ssl_context,
                retry_policy=retry_policy,
                circuit_breaker=circuit_breaker,
                keep_alive=keep_alive,
            )
        )

    def close(self) -> None:
        if self._client is None:
            return
        transport = getattr(self._client, "_transport", None)
        close_fn = getattr(transport, "close", None) if transport is not None else None
        if callable(close_fn):
            close_fn()

    async def aclose(self) -> None:
        await asyncio.to_thread(self.close)

    async def initialize(self, *, supported_versions: list[str], entity_id: str, profile: str | None = None) -> dict[str, Any]:
        if self._server is not None:
            return await self._server.initialize(
                supported_versions=supported_versions,
                entity_id=entity_id,
                capabilities={},
                supported_profiles=[profile] if profile else [],
            )
        assert self._client is not None
        return await asyncio.to_thread(
            self._client.initialize,
            supported_versions=supported_versions,
            entity_id=entity_id,
            profile=profile,
        )

    async def ping(self) -> dict[str, Any]:
        if self._server is not None:
            return {"ok": True, "fp_version": self._server.fp_version}
        assert self._client is not None
        return await asyncio.to_thread(self._client.ping)

    async def register_entity(self, entity: Any) -> dict[str, Any]:
        if self._server is not None:
            value = await self._server.register_entity(entity)
            return _to_payload(value)
        assert self._client is not None
        return await asyncio.to_thread(self._client.register_entity, entity)

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        if self._server is not None:
            value = await self._server.get_entity(entity_id)
            return _to_payload(value)
        assert self._client is not None
        return await asyncio.to_thread(self._client.get_entity, entity_id)

    async def session_create(
        self,
        *,
        participants: set[str],
        roles: dict[str, set[str]],
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        if self._server is not None:
            value = await self._server.sessions_create(
                participants=participants,
                roles=roles,
                policy_ref=policy_ref,
                budget=budget,
                session_id=session_id,
            )
            return {
                "session_id": value.session_id,
                "participants": sorted(value.participants),
                "roles": {k: sorted(v) for k, v in value.roles.items()},
                "state": value.state.value,
                "policy_ref": value.policy_ref,
                "budget": {
                    "token_limit": value.budget.token_limit,
                    "spend_limit": (
                        None
                        if value.budget.spend_limit is None
                        else {
                            "currency": value.budget.spend_limit.currency,
                            "amount": value.budget.spend_limit.amount,
                        }
                    ),
                },
            }
        assert self._client is not None
        return await asyncio.to_thread(
            self._client.session_create,
            participants=participants,
            roles=roles,
            policy_ref=policy_ref,
            budget=budget,
            session_id=session_id,
        )

    async def session_get(self, session_id: str) -> dict[str, Any]:
        if self._server is not None:
            value = await self._server.sessions_get(session_id)
            return {
                "session_id": value.session_id,
                "participants": sorted(value.participants),
                "roles": {k: sorted(v) for k, v in value.roles.items()},
                "state": value.state.value,
            }
        assert self._client is not None
        return await asyncio.to_thread(self._client.session_get, session_id)

    async def session_list_page(self, *, limit: int = 100, cursor: str | None = None) -> dict[str, Any]:
        if self._server is not None:
            page = await self._server.sessions_list_page(limit=limit, cursor=cursor)
            return {
                "items": [
                    {
                        "session_id": item.session_id,
                        "participants": sorted(item.participants),
                        "roles": {k: sorted(v) for k, v in item.roles.items()},
                        "state": item.state.value,
                    }
                    for item in page["items"]
                ],
                "next_cursor": page["next_cursor"],
            }
        assert self._client is not None
        return await asyncio.to_thread(self._client.session_list_page, limit=limit, cursor=cursor)

    async def activity_start(
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
    ) -> dict[str, Any]:
        if self._server is not None:
            value = await self._server.activities_start(
                session_id=session_id,
                owner_entity_id=owner_entity_id,
                initiator_entity_id=initiator_entity_id,
                operation=operation,
                input_payload=input_payload,
                activity_id=activity_id,
                idempotency_key=idempotency_key,
                auto_execute=auto_execute,
            )
            return {
                "activity_id": value.activity_id,
                "session_id": value.session_id,
                "owner_entity_id": value.owner_entity_id,
                "initiator_entity_id": value.initiator_entity_id,
                "state": value.state.value,
                "operation": value.operation,
                "input_payload": value.input_payload,
                "result_payload": value.result_payload,
                "result_ref": value.result_ref,
                "status_message": value.status_message,
                "error": value.error,
            }
        assert self._client is not None
        return await asyncio.to_thread(
            self._client.activity_start,
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
            activity_id=activity_id,
            idempotency_key=idempotency_key,
            auto_execute=auto_execute,
        )

    async def activity_result(self, *, activity_id: str) -> dict[str, Any]:
        if self._server is not None:
            value = await self._server.activities_result(activity_id=activity_id)
            activity = value["activity"]
            return {
                "activity": {
                    "activity_id": activity.activity_id,
                    "state": activity.state.value,
                },
                "result": value["result"],
                "result_ref": value["result_ref"],
            }
        assert self._client is not None
        return await asyncio.to_thread(self._client.activity_result, activity_id=activity_id)

    async def activity_list_page(
        self,
        *,
        session_id: str | None = None,
        state: str | None = None,
        owner_entity_id: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        if self._server is not None:
            state_value = ActivityState(state) if state else None
            page = await self._server.activities_list_page(
                session_id=session_id,
                state=state_value,
                owner_entity_id=owner_entity_id,
                limit=limit,
                cursor=cursor,
            )
            return {
                "items": [
                    {
                        "activity_id": item.activity_id,
                        "session_id": item.session_id,
                        "state": item.state.value,
                        "owner_entity_id": item.owner_entity_id,
                        "initiator_entity_id": item.initiator_entity_id,
                        "operation": item.operation,
                        "input_payload": item.input_payload,
                        "result_payload": item.result_payload,
                        "result_ref": item.result_ref,
                    }
                    for item in page["items"]
                ],
                "next_cursor": page["next_cursor"],
            }
        assert self._client is not None
        return await asyncio.to_thread(
            self._client.activity_list_page,
            session_id=session_id,
            state=state,
            owner_entity_id=owner_entity_id,
            limit=limit,
            cursor=cursor,
        )

    async def activity_update(
        self,
        *,
        activity_id: str,
        state: ActivityState,
        status_message: str | None = None,
        patch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._server is not None:
            value = await self._server.activities_update(
                activity_id=activity_id,
                state=state,
                status_message=status_message,
                patch=patch,
            )
            return {
                "activity_id": value.activity_id,
                "state": value.state.value,
                "status_message": value.status_message,
            }
        assert self._client is not None
        return await asyncio.to_thread(
            self._client.activity_update,
            activity_id=activity_id,
            state=state,
            status_message=status_message,
            patch=patch,
        )

    async def activity_cancel(self, *, activity_id: str, reason: str | None = None) -> dict[str, Any]:
        if self._server is not None:
            value = await self._server.activities_cancel(activity_id=activity_id, reason=reason)
            return {
                "activity_id": value.activity_id,
                "state": value.state.value,
                "status_message": value.status_message,
            }
        assert self._client is not None
        return await asyncio.to_thread(self._client.activity_cancel, activity_id=activity_id, reason=reason)

    async def events_stream(
        self,
        *,
        session_id: str,
        activity_id: str | None = None,
        from_event_id: str | None = None,
    ) -> dict[str, Any]:
        if self._server is not None:
            return await self._server.events_stream(
                session_id=session_id,
                activity_id=activity_id,
                from_event_id=from_event_id,
            )
        assert self._client is not None
        return await asyncio.to_thread(
            self._client.events_stream,
            session_id=session_id,
            activity_id=activity_id,
            from_event_id=from_event_id,
        )

    async def events_read(self, *, stream_id: str, limit: int = 200) -> list[dict[str, Any]]:
        if self._server is not None:
            events = await self._server.events_read(stream_id=stream_id, limit=limit)
            return [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "session_id": event.session_id,
                    "activity_id": event.activity_id,
                    "producer_entity_id": event.producer_entity_id,
                    "payload": event.payload,
                }
                for event in events
            ]
        assert self._client is not None
        return await asyncio.to_thread(self._client.events_read, stream_id=stream_id, limit=limit)

    async def events_ack(self, *, stream_id: str, event_ids: list[str]) -> dict[str, Any]:
        if self._server is not None:
            return await self._server.events_ack(stream_id=stream_id, event_ids=event_ids)
        assert self._client is not None
        return await asyncio.to_thread(self._client.events_ack, stream_id=stream_id, event_ids=event_ids)
