"""Async wrapper for EventEngine."""

from __future__ import annotations

from fp.protocol import EventStreamHandle, FPEvent
from fp.runtime.event_engine import EventEngine
from fp.stores.interfaces import EventStore


class AsyncEventEngine:
    def __init__(self, store: EventStore, *, backpressure_window: int = 500) -> None:
        self._engine = EventEngine(store, backpressure_window=backpressure_window)

    async def publish(self, event: FPEvent) -> FPEvent:
        return self._engine.publish(event)

    async def stream(
        self,
        *,
        session_id: str,
        activity_id: str | None = None,
        from_event_id: str | None = None,
    ) -> EventStreamHandle:
        return self._engine.stream(
            session_id=session_id,
            activity_id=activity_id,
            from_event_id=from_event_id,
        )

    async def read(self, stream_id: str, *, limit: int = 200) -> list[FPEvent]:
        return self._engine.read(stream_id, limit=limit)

    async def resubscribe(self, stream_id: str, *, last_event_id: str) -> EventStreamHandle:
        return self._engine.resubscribe(stream_id, last_event_id=last_event_id)

    async def ack(self, stream_id: str, event_ids: list[str]) -> None:
        self._engine.ack(stream_id, event_ids)

    async def push_config_set(self, config: dict) -> dict:
        return self._engine.push_config_set(config)

    async def push_config_get(self, push_config_id: str) -> dict:
        return self._engine.push_config_get(push_config_id)

    async def push_config_list(self, *, session_id: str | None = None, activity_id: str | None = None) -> list[dict]:
        return self._engine.push_config_list(session_id=session_id, activity_id=activity_id)

    async def push_config_delete(self, push_config_id: str) -> None:
        self._engine.push_config_delete(push_config_id)
