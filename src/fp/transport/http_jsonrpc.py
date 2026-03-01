"""HTTP/JSON-RPC transport adapters for FP app-layer integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Mapping

from fp.protocol import (
    ActivityState,
    CapabilitySummary,
    Delegation,
    DelegationConstraints,
    DelegationSpendLimit,
    Entity,
    EntityKind,
    FPError,
    FPErrorCode,
    Identity,
    Membership,
    MembershipStatus,
    Organization,
    OrganizationGovernance,
    PrivacyControl,
    SessionBudget,
    SessionState,
)

_JSONRPC_VERSION = "2.0"

_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603
_FP_RUNTIME_ERROR = -32000


@dataclass(slots=True)
class JSONRPCRequest:
    method: str
    params: dict[str, Any]
    id: str | int | None = None


@dataclass(slots=True)
class JSONRPCResponse:
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    id: str | int | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"jsonrpc": _JSONRPC_VERSION, "id": self.id}
        if self.error is not None:
            payload["error"] = self.error
        else:
            payload["result"] = self.result
        return payload


@dataclass(slots=True)
class _JSONRPCProtocolError(Exception):
    code: int
    message: str
    request_id: str | int | None
    data: dict[str, Any] | None = None


def _camel_to_snake(name: str) -> str:
    out: list[str] = []
    for ch in name:
        if ch.isupper():
            out.append("_")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out).lstrip("_")


def _normalize_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {_camel_to_snake(str(key)): _normalize_keys(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_keys(item) for item in value]
    return value


def _as_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _as_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _as_jsonable(v) for k, v in value.items()}
    if isinstance(value, set):
        return sorted(_as_jsonable(item) for item in value)
    if isinstance(value, (list, tuple)):
        return [_as_jsonable(item) for item in value]
    return value


def _decode_request(payload: Mapping[str, Any]) -> JSONRPCRequest:
    if not isinstance(payload, Mapping):
        raise _JSONRPCProtocolError(_INVALID_REQUEST, "request payload must be an object", None)
    if payload.get("jsonrpc") != _JSONRPC_VERSION:
        raise _JSONRPCProtocolError(_INVALID_REQUEST, "jsonrpc must be '2.0'", payload.get("id"))
    method = payload.get("method")
    if not isinstance(method, str) or not method:
        raise _JSONRPCProtocolError(_INVALID_REQUEST, "method must be a non-empty string", payload.get("id"))
    params = payload.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise _JSONRPCProtocolError(_INVALID_PARAMS, "params must be an object", payload.get("id"))
    normalized = _normalize_keys(params)
    if set(normalized.keys()) == {"params"} and isinstance(normalized["params"], dict):
        normalized = normalized["params"]
    request_id = payload.get("id")
    if request_id is not None and not isinstance(request_id, (str, int)):
        raise _JSONRPCProtocolError(_INVALID_REQUEST, "id must be string, number, or null", None)
    return JSONRPCRequest(method=method, params=normalized, id=request_id)


def _parse_entity(raw: dict[str, Any]) -> Entity:
    identity_raw = raw.get("identity", {})
    capability_raw = raw.get("capability_summary", {})
    privacy_raw = raw.get("privacy", {})
    kind = raw.get("kind", EntityKind.AGENT.value)
    kind_value = kind if isinstance(kind, EntityKind) else EntityKind(str(kind))

    return Entity(
        entity_id=str(raw["entity_id"]),
        kind=kind_value,
        display_name=raw.get("display_name"),
        identity=Identity(
            method=str(identity_raw.get("method", "did:example")),
            issuer=identity_raw.get("issuer"),
            key_refs=list(identity_raw.get("key_refs") or [f"{raw['entity_id']}#key-1"]),
            version=str(identity_raw.get("version", "v1")),
        ),
        capability_summary=CapabilitySummary(
            purpose=list(capability_raw.get("purpose") or ["general"]),
            risk_tags=list(capability_raw.get("risk_tags", [])),
            schema_hashes=list(capability_raw.get("schema_hashes", [])),
            price_policy_hints=list(capability_raw.get("price_policy_hints", [])),
        ),
        privacy=PrivacyControl(
            owner=str(privacy_raw.get("owner", raw["entity_id"])),
            default_visibility=str(privacy_raw.get("default_visibility", "restricted")),
            delegation_policy_ref=privacy_raw.get("delegation_policy_ref"),
        ),
        capability_refs=list(raw.get("capability_refs", [])),
        trust_refs=list(raw.get("trust_refs", [])),
        metadata=dict(raw.get("metadata", {})),
    )


def _parse_organization(raw: dict[str, Any]) -> Organization:
    governance_raw = dict(raw.get("governance", {}))
    entity_raw = dict(raw.get("entity", {}))
    if "entity_id" not in entity_raw and "organization_id" in raw:
        entity_raw["entity_id"] = raw["organization_id"]
        entity_raw.setdefault("kind", EntityKind.ORGANIZATION.value)
    if "entity_id" not in entity_raw:
        raise FPError(FPErrorCode.INVALID_ARGUMENT, "organization.entity.entity_id is required")

    return Organization(
        organization_id=str(raw.get("organization_id") or entity_raw["entity_id"]),
        entity=_parse_entity(entity_raw),
        governance=OrganizationGovernance(
            policy_refs=list(governance_raw.get("policy_refs", [])),
            role_catalog=list(governance_raw.get("role_catalog", [])),
        ),
    )


def _parse_membership(raw: dict[str, Any]) -> Membership:
    delegation_items: list[Delegation] = []
    for item in raw.get("delegations", []):
        constraints_raw = dict(item.get("constraints", {}))
        spend_raw = constraints_raw.get("spend_limit")
        spend = None
        if isinstance(spend_raw, dict):
            spend = DelegationSpendLimit(currency=str(spend_raw["currency"]), amount=float(spend_raw["amount"]))
        delegation_items.append(
            Delegation(
                scope=list(item.get("scope", [])),
                constraints=DelegationConstraints(
                    spend_limit=spend,
                    max_token_limit=constraints_raw.get("max_token_limit"),
                ),
            )
        )

    status = raw.get("status", MembershipStatus.ACTIVE)
    status_value = status if isinstance(status, MembershipStatus) else MembershipStatus(str(status))
    return Membership(
        membership_id=str(raw["membership_id"]),
        organization_id=str(raw["organization_id"]),
        member_entity_id=str(raw["member_entity_id"]),
        roles=set(raw.get("roles", [])),
        status=status_value,
        delegations=delegation_items,
    )


def _parse_session_budget(raw: dict[str, Any] | None) -> SessionBudget | None:
    if raw is None:
        return None
    spend_limit = None
    spend_raw = raw.get("spend_limit")
    if isinstance(spend_raw, dict):
        spend_limit = DelegationSpendLimit(currency=str(spend_raw["currency"]), amount=float(spend_raw["amount"]))
    return SessionBudget(spend_limit=spend_limit, token_limit=raw.get("token_limit"))


class JSONRPCDispatcher:
    """Minimal JSON-RPC 2.0 dispatcher for FP method handlers."""

    def __init__(self, method_table: dict[str, Callable[[dict[str, Any]], Any]]) -> None:
        self._method_table = dict(method_table)

    @classmethod
    def from_server(cls, server: Any) -> "JSONRPCDispatcher":
        def _as_set(value: Any, *, field_name: str) -> set[str]:
            if value is None:
                return set()
            if isinstance(value, (set, list, tuple)):
                return {str(item) for item in value}
            raise FPError(FPErrorCode.INVALID_ARGUMENT, f"{field_name} must be an array")

        def _as_roles_map(value: Any, *, field_name: str) -> dict[str, set[str]]:
            if value is None:
                return {}
            if not isinstance(value, dict):
                raise FPError(FPErrorCode.INVALID_ARGUMENT, f"{field_name} must be an object")
            return {str(entity_id): _as_set(role_values, field_name=f"{field_name}.{entity_id}") for entity_id, role_values in value.items()}

        def _kind_or_none(value: str | None) -> EntityKind | None:
            if value is None:
                return None
            return EntityKind(value)

        def _session_state_or_none(value: str | None) -> SessionState | None:
            if value is None:
                return None
            return SessionState(value)

        method_table: dict[str, Callable[[dict[str, Any]], Any]] = {
            "fp/initialize": lambda p: server.initialize(**p),
            "fp/initialized": lambda p: {"ok": True},
            "fp/ping": lambda p: {"ok": True, "fp_version": server.fp_version},
            "fp/entities.get": lambda p: server.get_entity(p["entity_id"]),
            "fp/entities.search": lambda p: server.search_entities(
                query=p.get("query", ""),
                kind=_kind_or_none(p.get("kind")),
                limit=int(p.get("limit", 50)),
            ),
            "fp/orgs.create": lambda p: server.create_organization(_parse_organization(p["organization"])),
            "fp/orgs.get": lambda p: server.get_organization(p["organization_id"]),
            "fp/orgs.members.add": lambda p: server.add_membership(
                _parse_membership({**p["membership"], "organization_id": p["organization_id"]}),
                actor_entity_id=p.get("actor_entity_id"),
            ),
            "fp/orgs.members.remove": lambda p: server.remove_membership(
                organization_id=p["organization_id"],
                membership_id=p["membership_id"],
                actor_entity_id=p.get("actor_entity_id"),
            ),
            "fp/orgs.roles.grant": lambda p: server.grant_roles(
                organization_id=p["organization_id"],
                member_entity_id=p["member_entity_id"],
                roles=_as_set(p.get("roles"), field_name="roles"),
                actor_entity_id=p.get("actor_entity_id"),
            ),
            "fp/orgs.roles.revoke": lambda p: server.revoke_roles(
                organization_id=p["organization_id"],
                member_entity_id=p["member_entity_id"],
                roles=_as_set(p.get("roles"), field_name="roles"),
                actor_entity_id=p.get("actor_entity_id"),
            ),
            "fp/sessions.create": lambda p: server.sessions_create(
                participants=_as_set(p.get("participants"), field_name="participants"),
                roles=_as_roles_map(p.get("roles"), field_name="roles"),
                policy_ref=p.get("policy_ref"),
                budget=_parse_session_budget(p.get("budget")),
                session_id=p.get("session_id"),
            ),
            "fp/sessions.join": lambda p: server.sessions_join(
                session_id=p["session_id"],
                entity_id=p["entity_id"],
                roles=_as_set(p["roles"], field_name="roles") if p.get("roles") is not None else None,
            ),
            "fp/sessions.update": lambda p: server.sessions_update(
                session_id=p["session_id"],
                policy_ref=p.get("policy_ref"),
                budget=_parse_session_budget(p.get("budget")),
                state=_session_state_or_none(p.get("state")),
                roles_patch=_as_roles_map(p.get("roles_patch"), field_name="roles_patch") if p.get("roles_patch") else None,
            ),
            "fp/sessions.leave": lambda p: server.sessions_leave(session_id=p["session_id"], entity_id=p["entity_id"]),
            "fp/sessions.close": lambda p: server.sessions_close(session_id=p["session_id"], reason=p.get("reason")),
            "fp/sessions.get": lambda p: server.sessions_get(p["session_id"]),
            "fp/activities.start": lambda p: server.activities_start(
                session_id=p["session_id"],
                owner_entity_id=p["owner_entity_id"],
                initiator_entity_id=p["initiator_entity_id"],
                operation=p.get("operation", ""),
                input_payload=dict(p.get("input_payload", p.get("input", {}))),
                activity_id=p.get("activity_id"),
                idempotency_key=p.get("idempotency_key"),
                auto_execute=bool(p.get("auto_execute", True)),
            ),
            "fp/activities.update": lambda p: server.activities_update(
                activity_id=p["activity_id"],
                state=ActivityState(p["state"]),
                status_message=p.get("status_message"),
                patch=p.get("patch"),
                producer_entity_id=p.get("producer_entity_id"),
            ),
            "fp/activities.get": lambda p: server.activities_get(p["activity_id"]),
            "fp/activities.cancel": lambda p: server.activities_cancel(activity_id=p["activity_id"], reason=p.get("reason")),
            "fp/activities.result": lambda p: server.activities_result(activity_id=p["activity_id"]),
            "fp/activities.list": lambda p: server.activities_list(
                session_id=p.get("session_id"),
                state=ActivityState(p["state"]) if p.get("state") else None,
                owner_entity_id=p.get("owner_entity_id"),
            ),
            "fp/events.stream": lambda p: server.events_stream(
                session_id=p["session_id"],
                activity_id=p.get("activity_id"),
                from_event_id=p.get("from_event_id"),
            ),
            "fp/events.resubscribe": lambda p: server.events_resubscribe(
                stream_id=p["stream_id"],
                last_event_id=p["last_event_id"],
            ),
            "fp/events.ack": lambda p: server.events_ack(stream_id=p["stream_id"], event_ids=list(p.get("event_ids", []))),
            "fp/events.pushConfig.set": lambda p: server.push_config_set(p["config"]),
            "fp/events.pushConfig.get": lambda p: server.push_config_get(p["push_config_id"]),
            "fp/events.pushConfig.list": lambda p: server.push_config_list(
                session_id=p.get("session_id"),
                activity_id=p.get("activity_id"),
            ),
            "fp/events.pushConfig.delete": lambda p: server.push_config_delete(p["push_config_id"]),
        }
        return cls(method_table=method_table)

    def handle(self, payload: Mapping[str, Any]) -> dict[str, Any] | None:
        request_id = payload.get("id") if isinstance(payload, Mapping) else None
        try:
            request = _decode_request(payload)
            handler = self._method_table.get(request.method)
            if handler is None:
                raise _JSONRPCProtocolError(_METHOD_NOT_FOUND, f"method not found: {request.method}", request.id)
            result = handler(request.params)
            if request.id is None:
                return None
            return JSONRPCResponse(result=_as_jsonable(result), id=request.id).to_payload()
        except _JSONRPCProtocolError as exc:
            if exc.request_id is None:
                return JSONRPCResponse(error={"code": exc.code, "message": exc.message, "data": exc.data}, id=None).to_payload()
            return JSONRPCResponse(
                error={"code": exc.code, "message": exc.message, "data": exc.data},
                id=exc.request_id,
            ).to_payload()
        except FPError as exc:
            if request_id is None:
                return None
            return JSONRPCResponse(
                error={
                    "code": _FP_RUNTIME_ERROR,
                    "message": exc.message,
                    "data": {"fp": exc.to_dict()},
                },
                id=request_id,
            ).to_payload()
        except (KeyError, TypeError, ValueError) as exc:
            if request_id is None:
                return None
            return JSONRPCResponse(
                error={
                    "code": _INVALID_PARAMS,
                    "message": "invalid params",
                    "data": {"detail": str(exc)},
                },
                id=request_id,
            ).to_payload()
        except Exception as exc:  # pragma: no cover - defensive path
            if request_id is None:
                return None
            return JSONRPCResponse(
                error={
                    "code": _INTERNAL_ERROR,
                    "message": "internal error",
                    "data": {"detail": str(exc)},
                },
                id=request_id,
            ).to_payload()


__all__ = ["JSONRPCDispatcher", "JSONRPCRequest", "JSONRPCResponse"]
