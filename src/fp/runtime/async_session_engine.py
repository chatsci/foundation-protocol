"""Async wrapper for SessionEngine."""

from __future__ import annotations

from fp.protocol import Session, SessionBudget, SessionState
from fp.runtime.session_engine import SessionEngine
from fp.stores.interfaces import SessionStore


class AsyncSessionEngine:
    def __init__(self, store: SessionStore) -> None:
        self._engine = SessionEngine(store)

    async def create(
        self,
        *,
        session_id: str,
        participants: set[str],
        roles: dict[str, set[str]],
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Session:
        return self._engine.create(
            session_id=session_id,
            participants=participants,
            roles=roles,
            policy_ref=policy_ref,
            budget=budget,
            metadata=metadata,
        )

    async def get(self, session_id: str) -> Session:
        return self._engine.get(session_id)

    async def join(self, session_id: str, entity_id: str, roles: set[str] | None = None) -> Session:
        return self._engine.join(session_id, entity_id, roles)

    async def leave(self, session_id: str, entity_id: str) -> Session:
        return self._engine.leave(session_id, entity_id)

    async def update(
        self,
        session_id: str,
        *,
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        state: SessionState | None = None,
        roles_patch: dict[str, set[str]] | None = None,
    ) -> Session:
        return self._engine.update(
            session_id,
            policy_ref=policy_ref,
            budget=budget,
            state=state,
            roles_patch=roles_patch,
        )

    async def close(self, session_id: str, reason: str | None = None) -> Session:
        return self._engine.close(session_id, reason)

    async def list(self) -> list[Session]:
        return self._engine.list()
