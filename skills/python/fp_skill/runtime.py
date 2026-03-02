"""Runtime bootstrap utilities for integrating skill manifests with FPServer."""

from __future__ import annotations

import importlib
import os
from dataclasses import replace
from typing import Any, Callable
from uuid import uuid4

from fp.app import FPClient, FPServer, make_default_entity
from fp.protocol import CapabilitySummary, EntityKind, FPError, FPErrorCode, SessionBudget

from .errors import SkillRuntimeError
from .manifest import SkillManifest


class SkillRuntime:
    """Bootstrap helper that wires a skill manifest into FP runtime primitives."""

    _ORCHESTRATOR_ID = "fp:system:skill-orchestrator"

    def __init__(self, manifest: SkillManifest, *, server: FPServer | None = None) -> None:
        self.manifest = manifest
        self.server = server or FPServer(server_entity_id=f"{manifest.entity.entity_id}:runtime")
        self.entity_id = manifest.entity.entity_id
        self._session_id: str | None = None

        self._register_orchestrator_entity()
        self._register_manifest_entity()
        self._configure_runtime_defaults()

    def _register_orchestrator_entity(self) -> None:
        self._upsert_entity(self._ORCHESTRATOR_ID, EntityKind.SERVICE, display_name="FP Skill Orchestrator")

    def _register_manifest_entity(self) -> None:
        kind = EntityKind(self.manifest.entity.kind)
        entity = make_default_entity(self.entity_id, kind, display_name=self.manifest.entity.display_name)
        entity = replace(
            entity,
            capability_summary=CapabilitySummary(
                purpose=list(self.manifest.entity.capability_purpose),
                risk_tags=list(entity.capability_summary.risk_tags),
                schema_hashes=list(entity.capability_summary.schema_hashes),
                price_policy_hints=list(entity.capability_summary.price_policy_hints),
            ),
            metadata=dict(self.manifest.entity.metadata),
        )
        self.server.register_entity(entity)

    def _configure_runtime_defaults(self) -> None:
        self.server.set_result_compaction(max_inline_bytes=self.manifest.defaults.result_compaction_bytes)

    def _upsert_entity(self, entity_id: str, kind: EntityKind, *, display_name: str | None = None) -> None:
        try:
            self.server.get_entity(entity_id)
        except FPError as exc:
            if exc.code is not FPErrorCode.NOT_FOUND:
                raise
            self.server.register_entity(make_default_entity(entity_id, kind, display_name=display_name))

    def register_operation(self, name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self.server.register_operation(name, handler)

    def load_manifest_operations(self) -> dict[str, Callable[..., Any]]:
        loaded: dict[str, Callable[..., Any]] = {}
        for op in self.manifest.operations:
            handler = _load_handler(op.handler)
            self.register_operation(op.name, handler)
            loaded[op.name] = handler
        return loaded

    def ensure_session(self, *, extra_participants: set[str] | None = None) -> str:
        if self._session_id is not None:
            return self._session_id

        participants = {self.entity_id, self._ORCHESTRATOR_ID}
        participants.update(extra_participants or set())

        default_roles = {
            entity_id: set(roles)
            for entity_id, roles in self.manifest.defaults.default_roles.items()
        }
        for entity_id in participants:
            default_roles.setdefault(entity_id, {"participant"})
            if entity_id != self.entity_id:
                self._upsert_entity(entity_id, EntityKind.AGENT)

        budget = SessionBudget(token_limit=self.manifest.defaults.token_limit)
        session = self.server.sessions_create(
            participants=participants,
            roles=default_roles,
            policy_ref=self.manifest.defaults.policy_ref,
            budget=budget,
            session_id=f"skill-sess-{uuid4().hex}",
        )
        self._session_id = session.session_id
        return session.session_id

    def invoke(
        self,
        *,
        operation: str,
        input_payload: dict[str, Any],
        owner_entity_id: str | None = None,
        initiator_entity_id: str | None = None,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        owner = owner_entity_id or self.entity_id
        initiator = initiator_entity_id or self._ORCHESTRATOR_ID
        self._upsert_entity(owner, EntityKind.AGENT)
        self._upsert_entity(initiator, EntityKind.AGENT)

        resolved_session_id = session_id
        if resolved_session_id is None and self.manifest.defaults.auto_session:
            resolved_session_id = self.ensure_session(extra_participants={owner, initiator})
        if resolved_session_id is None:
            raise SkillRuntimeError("session_id is required when defaults.auto_session is false")

        activity = self.server.activities_start(
            session_id=resolved_session_id,
            owner_entity_id=owner,
            initiator_entity_id=initiator,
            operation=operation,
            input_payload=input_payload,
            # Idempotency is opt-in: callers must provide a stable key explicitly.
            # A generated random key would not provide replay protection semantics.
            idempotency_key=idempotency_key,
        )
        return self.server.activities_result(activity_id=activity.activity_id)

    def client(self) -> FPClient:
        mode = self.manifest.connection.mode
        if mode == "inproc":
            return FPClient.from_inproc(self.server)
        if mode == "http_jsonrpc":
            headers = _auth_headers(self.manifest)
            return FPClient.from_http_jsonrpc(
                self.manifest.connection.rpc_url or "",
                timeout_seconds=self.manifest.connection.timeout_seconds,
                headers=headers,
                keep_alive=self.manifest.connection.keep_alive,
            )
        raise SkillRuntimeError(f"unsupported connection mode: {mode}")


def _load_handler(handler_ref: str) -> Callable[..., Any]:
    if ":" not in handler_ref:
        raise SkillRuntimeError("handler must be module.path:function_name")
    module_name, func_name = handler_ref.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise SkillRuntimeError(f"failed to import module {module_name}: {exc}") from exc
    handler = getattr(module, func_name, None)
    if not callable(handler):
        raise SkillRuntimeError(f"handler not found or not callable: {handler_ref}")
    return handler


def _auth_headers(manifest: SkillManifest) -> dict[str, str] | None:
    mode = manifest.auth.mode
    if mode == "none":
        return None
    if mode == "bearer_env":
        token_env = manifest.auth.token_env or ""
        token = os.environ.get(token_env)
        if token is None or not token.strip():
            raise SkillRuntimeError(f"missing auth token env var: {token_env}")
        return {"Authorization": f"Bearer {token}"}
    if mode == "bearer_static":
        token = manifest.auth.token or ""
        if not token.strip():
            raise SkillRuntimeError("auth.token must be set for bearer_static")
        return {"Authorization": f"Bearer {token}"}
    raise SkillRuntimeError(f"unsupported auth mode: {mode}")


__all__ = ["SkillRuntime"]
