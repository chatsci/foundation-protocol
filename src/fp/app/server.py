"""FP server implementation (in-memory reference runtime)."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Callable
from uuid import uuid4

from fp.economy import DisputeService, MeteringService, ReceiptService, SettlementService
from fp.graph import EntityRegistry, MembershipRegistry, OrganizationRegistry
from fp.observability import CostMeter, CostModel, MetricsRegistry, TokenMeter, export_audit_bundle, new_trace_id
from fp.policy import AllowAllPolicyEngine, PolicyContext, PolicyEngine, PolicyHook
from fp.protocol import (
    Activity,
    ActivityState,
    CapabilitySummary,
    Dispute,
    Entity,
    EntityKind,
    FPError,
    FPErrorCode,
    FPEvent,
    Identity,
    Membership,
    Organization,
    OrganizationGovernance,
    PrivacyControl,
    ProvenanceRecord,
    Session,
    SessionBudget,
    SessionState,
    Settlement,
)
from fp.runtime import ActivityEngine, DispatchContext, DispatchEngine, EventEngine, SessionEngine
from fp.runtime.idempotency import IdempotencyGuard
from fp.stores.memory import InMemoryStoreBundle


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


class FPServer:
    """Reference FP runtime that keeps core semantics explicit and testable."""

    SUPPORTED_VERSIONS = ("0.1.0",)

    def __init__(
        self,
        *,
        fp_version: str = "0.1.0",
        server_entity_id: str = "fp:system:runtime",
        stores: InMemoryStoreBundle | None = None,
        policy_engine: PolicyEngine | None = None,
        receipt_secret: str = "fp-local-secret",
    ) -> None:
        if fp_version not in self.SUPPORTED_VERSIONS:
            raise FPError(FPErrorCode.VERSION_UNSUPPORTED, f"unsupported fp version: {fp_version}")

        self.fp_version = fp_version
        self.server_entity_id = server_entity_id
        self.stores = stores or InMemoryStoreBundle()
        self.policy_engine = policy_engine or AllowAllPolicyEngine()

        self.entities = EntityRegistry(self.stores.entities)
        self.organizations = OrganizationRegistry(self.stores.entities, self.stores.organizations)
        self.memberships = MembershipRegistry(self.stores.organizations, self.stores.memberships)

        self.sessions = SessionEngine(self.stores.sessions)
        self.activities = ActivityEngine(self.stores.activities)
        self.dispatch = DispatchEngine()
        self.events = EventEngine(self.stores.events)
        self.idempotency = IdempotencyGuard()

        self.metering = MeteringService()
        self.receipts = ReceiptService(secret=receipt_secret)
        self.settlements = SettlementService()
        self.disputes = DisputeService()

        self.metrics = MetricsRegistry()
        self.token_meter = TokenMeter()
        self.cost_meter = CostMeter(CostModel(input_per_1k_tokens=0.001, output_per_1k_tokens=0.002))

    # -------- Handshake --------

    def initialize(
        self,
        *,
        supported_versions: list[str],
        entity_id: str,
        capabilities: dict[str, Any] | None = None,
        supported_profiles: list[str] | None = None,
    ) -> dict[str, Any]:
        intersection = [version for version in supported_versions if version in self.SUPPORTED_VERSIONS]
        if not intersection:
            raise FPError(
                FPErrorCode.VERSION_UNSUPPORTED,
                details={
                    "supported_versions": list(self.SUPPORTED_VERSIONS),
                    "requested_versions": supported_versions,
                },
            )
        version = sorted(intersection)[-1]
        self.metrics.inc("initialize.ok")
        return {
            "negotiated_version": version,
            "server_entity_ref": self.server_entity_id,
            "capabilities": capabilities or {},
            "supported_profiles": supported_profiles or [],
        }

    # -------- Entity / Organization --------

    def register_entity(self, entity: Entity) -> Entity:
        out = self.entities.upsert(entity)
        self.metrics.inc("entities.register")
        return out

    def get_entity(self, entity_id: str) -> Entity:
        return self.entities.get(entity_id)

    def search_entities(self, *, query: str, kind: EntityKind | None = None, limit: int = 50) -> list[Entity]:
        return self.entities.search(query=query, kind=kind.value if kind else None, limit=limit)

    def create_organization(self, organization: Organization) -> Organization:
        out = self.organizations.create(organization)
        self.metrics.inc("organizations.create")
        return out

    def get_organization(self, organization_id: str) -> Organization:
        return self.organizations.get(organization_id)

    def add_membership(self, membership: Membership, *, actor_entity_id: str | None = None) -> Membership:
        self._enforce_policy(
            hook=PolicyHook.PRE_ROLE_CHANGE,
            actor_entity_id=actor_entity_id,
            payload={"organization_id": membership.organization_id, "member_entity_id": membership.member_entity_id},
        )
        out = self.memberships.add(membership)
        self.metrics.inc("memberships.add")
        self._emit_org_event(membership.organization_id, "membership.added", payload={"membership_id": membership.membership_id})
        return out

    def remove_membership(self, *, organization_id: str, membership_id: str, actor_entity_id: str | None = None) -> Membership:
        self._enforce_policy(
            hook=PolicyHook.PRE_ROLE_CHANGE,
            actor_entity_id=actor_entity_id,
            payload={"organization_id": organization_id, "membership_id": membership_id},
        )
        out = self.memberships.remove(organization_id, membership_id)
        self.metrics.inc("memberships.remove")
        self._emit_org_event(organization_id, "membership.removed", payload={"membership_id": membership_id})
        return out

    def grant_roles(
        self,
        *,
        organization_id: str,
        member_entity_id: str,
        roles: set[str],
        actor_entity_id: str | None = None,
    ) -> Membership:
        self._enforce_policy(
            hook=PolicyHook.PRE_ROLE_CHANGE,
            actor_entity_id=actor_entity_id,
            payload={"organization_id": organization_id, "member_entity_id": member_entity_id, "roles": sorted(roles)},
        )
        out = self.memberships.grant_roles(organization_id, member_entity_id, roles)
        self.metrics.inc("memberships.roles.grant")
        self._emit_org_event(organization_id, "membership.roles.granted", payload={"member_entity_id": member_entity_id})
        return out

    def revoke_roles(
        self,
        *,
        organization_id: str,
        member_entity_id: str,
        roles: set[str],
        actor_entity_id: str | None = None,
    ) -> Membership:
        self._enforce_policy(
            hook=PolicyHook.PRE_ROLE_CHANGE,
            actor_entity_id=actor_entity_id,
            payload={"organization_id": organization_id, "member_entity_id": member_entity_id, "roles": sorted(roles)},
        )
        out = self.memberships.revoke_roles(organization_id, member_entity_id, roles)
        self.metrics.inc("memberships.roles.revoke")
        self._emit_org_event(organization_id, "membership.roles.revoked", payload={"member_entity_id": member_entity_id})
        return out

    # -------- Session --------

    def sessions_create(
        self,
        *,
        participants: set[str],
        roles: dict[str, set[str]],
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        session_id: str | None = None,
    ) -> Session:
        for participant in participants:
            self._require_entity(participant)
        created = self.sessions.create(
            session_id=session_id or _new_id("sess"),
            participants=participants,
            roles=roles,
            policy_ref=policy_ref,
            budget=budget,
        )
        self.metrics.inc("sessions.create")
        self._emit_event(
            event_type="session.created",
            session_id=created.session_id,
            producer_entity_id=self.server_entity_id,
            payload={"participants": sorted(created.participants)},
        )
        return created

    def sessions_join(self, *, session_id: str, entity_id: str, roles: set[str] | None = None) -> Session:
        self._require_entity(entity_id)
        updated = self.sessions.join(session_id, entity_id, roles)
        self._emit_event(
            event_type="session.joined",
            session_id=session_id,
            producer_entity_id=entity_id,
            payload={"roles": sorted(updated.roles.get(entity_id, set()))},
        )
        return updated

    def sessions_update(
        self,
        *,
        session_id: str,
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        state: SessionState | None = None,
        roles_patch: dict[str, set[str]] | None = None,
    ) -> Session:
        if roles_patch:
            for entity_id in roles_patch:
                self._require_entity(entity_id)
        updated = self.sessions.update(
            session_id,
            policy_ref=policy_ref,
            budget=budget,
            state=state,
            roles_patch=roles_patch,
        )
        self._emit_event(
            event_type="session.updated",
            session_id=session_id,
            producer_entity_id=self.server_entity_id,
            payload={"state": updated.state.value},
        )
        return updated

    def sessions_leave(self, *, session_id: str, entity_id: str) -> Session:
        updated = self.sessions.leave(session_id, entity_id)
        self._emit_event(
            event_type="session.left",
            session_id=session_id,
            producer_entity_id=entity_id,
            payload={},
        )
        return updated

    def sessions_close(self, *, session_id: str, reason: str | None = None) -> Session:
        closed = self.sessions.close(session_id, reason)
        self._emit_event(
            event_type="session.closed",
            session_id=session_id,
            producer_entity_id=self.server_entity_id,
            payload={"reason": reason},
        )
        return closed

    def sessions_get(self, session_id: str) -> Session:
        return self.sessions.get(session_id)

    # -------- Activity --------

    def register_operation(self, name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self.dispatch.register(name, handler)

    def activities_start(
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
        self._require_entity(owner_entity_id)
        self._require_entity(initiator_entity_id)
        session = self.sessions.get(session_id)
        if session.state is not SessionState.ACTIVE:
            raise FPError(
                FPErrorCode.INVALID_STATE_TRANSITION,
                message=f"cannot start activity in session state: {session.state.value}",
            )
        if owner_entity_id not in session.participants:
            raise FPError(
                FPErrorCode.AUTHZ_DENIED,
                message="activity owner must be a session participant",
                details={"session_id": session_id, "owner_entity_id": owner_entity_id},
            )
        if initiator_entity_id not in session.participants:
            raise FPError(
                FPErrorCode.AUTHZ_DENIED,
                message="activity initiator must be a session participant",
                details={"session_id": session_id, "initiator_entity_id": initiator_entity_id},
            )

        request_fingerprint = self._idempotency_fingerprint(
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
        )
        if idempotency_key:
            cached = self.idempotency.check(idempotency_key, fingerprint=request_fingerprint)
            if cached is not None:
                value = cached.value
                if isinstance(value, Activity):
                    return value

        self._enforce_policy(
            hook=PolicyHook.PRE_INVOKE,
            actor_entity_id=initiator_entity_id,
            session_id=session_id,
            operation=operation,
            payload=input_payload,
        )

        activity = self.activities.start(
            activity_id=activity_id or _new_id("act"),
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
        )
        self._emit_event(
            event_type="activity.submitted",
            session_id=session_id,
            activity_id=activity.activity_id,
            producer_entity_id=initiator_entity_id,
            payload={"operation": operation},
        )

        if auto_execute and self.dispatch.has_handler(operation):
            activity = self.activities.transition(activity.activity_id, next_state=ActivityState.WORKING)
            self._emit_event(
                event_type="activity.working",
                session_id=session_id,
                activity_id=activity.activity_id,
                producer_entity_id=owner_entity_id,
                payload={"operation": operation},
            )
            ctx = DispatchContext(
                session_id=session_id,
                activity_id=activity.activity_id,
                operation=operation,
                actor_entity_id=initiator_entity_id,
            )
            try:
                output = self.dispatch.execute(context=ctx, input_payload=input_payload)
            except Exception as exc:  # pragma: no cover - defensive path
                activity = self.activities.fail(activity.activity_id, message=str(exc))
                self._emit_event(
                    event_type="activity.failed",
                    session_id=session_id,
                    activity_id=activity.activity_id,
                    producer_entity_id=owner_entity_id,
                    payload={"error": str(exc)},
                )
            else:
                if not (isinstance(output, dict) and output.get("state") == "working"):
                    result_payload = output if isinstance(output, dict) else {"value": output}
                    activity = self.activities.complete(activity.activity_id, result_payload=result_payload)
                    usage = self.token_meter.measure(input_payload=input_payload, output_payload=result_payload)
                    estimated_cost = self.cost_meter.estimate(usage)
                    self._emit_event(
                        event_type="activity.completed",
                        session_id=session_id,
                        activity_id=activity.activity_id,
                        producer_entity_id=owner_entity_id,
                        payload={
                            "usage": asdict(usage),
                            "estimated_cost": round(estimated_cost, 8),
                        },
                    )

        if idempotency_key:
            self.idempotency.store(idempotency_key, activity, fingerprint=request_fingerprint)
        return activity

    def activities_update(
        self,
        *,
        activity_id: str,
        state: ActivityState,
        status_message: str | None = None,
        patch: dict[str, Any] | None = None,
        producer_entity_id: str | None = None,
    ) -> Activity:
        source_entity_id = producer_entity_id or self.server_entity_id
        updated = self.activities.transition(activity_id, next_state=state, status_message=status_message, patch=patch)
        self._emit_event(
            event_type=f"activity.{state.value}",
            session_id=updated.session_id,
            activity_id=updated.activity_id,
            producer_entity_id=source_entity_id,
            payload={"status_message": status_message, "patch": patch or {}},
        )
        return updated

    def activities_get(self, activity_id: str) -> Activity:
        return self.activities.get(activity_id)

    def activities_cancel(self, *, activity_id: str, reason: str | None = None) -> Activity:
        canceled = self.activities.cancel(activity_id, reason=reason)
        self._emit_event(
            event_type="activity.canceled",
            session_id=canceled.session_id,
            activity_id=canceled.activity_id,
            producer_entity_id=self.server_entity_id,
            payload={"reason": reason},
        )
        return canceled

    def activities_complete(
        self,
        *,
        activity_id: str,
        result_payload: dict[str, Any] | None = None,
        result_ref: str | None = None,
        producer_entity_id: str | None = None,
    ) -> Activity:
        source_entity_id = producer_entity_id or self.server_entity_id
        completed = self.activities.complete(activity_id, result_payload=result_payload, result_ref=result_ref)
        self._emit_event(
            event_type="activity.completed",
            session_id=completed.session_id,
            activity_id=completed.activity_id,
            producer_entity_id=source_entity_id,
            payload={"result_ref": result_ref},
        )
        return completed

    def activities_result(self, *, activity_id: str) -> dict[str, Any]:
        activity = self.activities.get(activity_id)
        return {
            "activity": activity,
            "result": activity.result_payload,
            "result_ref": activity.result_ref,
        }

    def activities_list(
        self,
        *,
        session_id: str | None = None,
        state: ActivityState | None = None,
        owner_entity_id: str | None = None,
    ) -> list[Activity]:
        return self.activities.list(session_id=session_id, state=state, owner_entity_id=owner_entity_id)

    # -------- Event streams --------

    def events_stream(
        self,
        *,
        session_id: str,
        activity_id: str | None = None,
        from_event_id: str | None = None,
    ) -> dict[str, Any]:
        self.sessions.get(session_id)
        handle = self.events.stream(session_id=session_id, activity_id=activity_id, from_event_id=from_event_id)
        return asdict(handle)

    def events_read(self, *, stream_id: str, limit: int = 200) -> list[FPEvent]:
        return self.events.read(stream_id, limit=limit)

    def events_resubscribe(self, *, stream_id: str, last_event_id: str) -> dict[str, Any]:
        return asdict(self.events.resubscribe(stream_id, last_event_id=last_event_id))

    def events_ack(self, *, stream_id: str, event_ids: list[str]) -> dict[str, bool]:
        self.events.ack(stream_id, event_ids)
        return {"ok": True}

    def emit_event(
        self,
        *,
        event_type: str,
        session_id: str,
        producer_entity_id: str,
        activity_id: str | None = None,
        payload: dict[str, Any] | None = None,
        policy_ref: str | None = None,
    ) -> FPEvent:
        return self._emit_event(
            event_type=event_type,
            session_id=session_id,
            producer_entity_id=producer_entity_id,
            activity_id=activity_id,
            payload=payload,
            policy_ref=policy_ref,
        )

    def push_config_set(self, config: dict) -> dict:
        return self.events.push_config_set(config)

    def push_config_get(self, push_config_id: str) -> dict:
        return self.events.push_config_get(push_config_id)

    def push_config_list(self, *, session_id: str | None = None, activity_id: str | None = None) -> list[dict]:
        return self.events.push_config_list(session_id=session_id, activity_id=activity_id)

    def push_config_delete(self, push_config_id: str) -> dict[str, bool]:
        self.events.push_config_delete(push_config_id)
        return {"ok": True}

    # -------- Economy --------

    def meter_record(
        self,
        *,
        subject_ref: str,
        unit: str,
        quantity: float,
        metering_policy_ref: str,
        metadata: dict[str, str] | None = None,
    ):
        return self.metering.record(
            subject_ref=subject_ref,
            unit=unit,
            quantity=quantity,
            metering_policy_ref=metering_policy_ref,
            metadata=metadata,
        )

    def receipts_issue(self, *, activity_id: str, provider_entity_id: str, meter_records: list) -> Any:
        receipt = self.receipts.issue(
            activity_id=activity_id,
            provider_entity_id=provider_entity_id,
            meter_records=meter_records,
        )
        self.stores.receipts.put(receipt)
        activity = self.activities.get(activity_id)
        self._emit_event(
            event_type="receipt.issued",
            session_id=activity.session_id,
            activity_id=activity_id,
            producer_entity_id=provider_entity_id,
            payload={"receipt_id": receipt.receipt_id},
        )
        return receipt

    def settlements_create(
        self,
        *,
        receipt_refs: list[str],
        settlement_ref: str,
        amount: float | None = None,
        currency: str | None = None,
        actor_entity_id: str | None = None,
    ) -> Settlement:
        for receipt_ref in receipt_refs:
            if self.stores.receipts.get(receipt_ref) is None:
                raise FPError(FPErrorCode.NOT_FOUND, f"receipt not found: {receipt_ref}")
        self._enforce_policy(
            hook=PolicyHook.PRE_SETTLE,
            actor_entity_id=actor_entity_id,
            payload={"receipt_refs": receipt_refs, "amount": amount, "currency": currency},
        )
        settlement = self.settlements.create(
            receipt_refs=receipt_refs,
            settlement_ref=settlement_ref,
            amount=amount,
            currency=currency,
        )
        self.stores.settlements.put(settlement)
        self.metrics.inc("settlements.create")
        return settlement

    def settlements_confirm(self, settlement_id: str) -> Settlement:
        settlement = self.stores.settlements.get(settlement_id)
        if settlement is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"settlement not found: {settlement_id}")
        settlement = self.settlements.confirm(settlement)
        self.stores.settlements.put(settlement)
        return settlement

    def disputes_open(
        self,
        *,
        target_ref: str,
        reason_code: str,
        claimant_entity_id: str,
        evidence_refs: list[str] | None = None,
    ) -> Dispute:
        dispute = self.disputes.open(
            target_ref=target_ref,
            reason_code=reason_code,
            claimant_entity_id=claimant_entity_id,
            evidence_refs=evidence_refs,
        )
        self.stores.disputes.put(dispute)
        self.metrics.inc("disputes.open")
        return dispute

    # -------- Provenance / audit --------

    def provenance_record(
        self,
        *,
        subject_refs: list[str],
        policy_refs: list[str],
        outcome: str,
        signer_ref: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProvenanceRecord:
        record = ProvenanceRecord(
            record_id=_new_id("prov"),
            subject_refs=subject_refs,
            policy_refs=policy_refs,
            outcome=outcome,
            signer_ref=signer_ref,
            metadata=metadata or {},
        )
        self.stores.provenance.put(record)
        return record

    def provenance_list(self) -> list[ProvenanceRecord]:
        return self.stores.provenance.list()

    def receipts_list(self) -> list:
        return self.stores.receipts.list()

    def settlements_list(self) -> list:
        return self.stores.settlements.list()

    def disputes_list(self) -> list:
        return self.stores.disputes.list()

    def audit_bundle(self, *, session_id: str) -> dict[str, Any]:
        events = self.stores.events.replay_from(f"{session_id}:*", None, limit=10_000)
        return export_audit_bundle(
            session_id=session_id,
            events=events,
            provenance=self.stores.provenance.list(),
            receipts=self.stores.receipts.list(),
            settlements=self.stores.settlements.list(),
        )

    # -------- Internal helpers --------

    def _enforce_policy(
        self,
        *,
        hook: PolicyHook,
        actor_entity_id: str | None,
        session_id: str | None = None,
        activity_id: str | None = None,
        operation: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        context = PolicyContext(
            hook=hook,
            actor_entity_id=actor_entity_id,
            session_id=session_id,
            activity_id=activity_id,
            operation=operation,
            payload=payload or {},
        )
        decision = self.policy_engine.evaluate(context)
        subject_refs = [s for s in [session_id, activity_id, actor_entity_id] if s]
        if not subject_refs and payload:
            for key, value in payload.items():
                if key.endswith("_id") or key.endswith("_ref"):
                    if isinstance(value, str) and value:
                        subject_refs.append(value)
                elif key.endswith("_refs") and isinstance(value, list):
                    subject_refs.extend(str(item) for item in value if item)
        if not subject_refs:
            subject_refs = [f"policy-hook:{hook.value}"]
        self.provenance_record(
            subject_refs=subject_refs,
            policy_refs=[decision.policy_ref or "policy:default"],
            outcome="allowed" if decision.allowed else "denied",
            signer_ref="fp:system:policy-engine",
            metadata={"decision_id": decision.decision_id, "reason": decision.reason, "hook": hook.value},
        )
        if not decision.allowed:
            raise FPError(
                FPErrorCode.POLICY_DENIED,
                message=decision.reason,
                details={
                    "decision_id": decision.decision_id,
                    "policy_ref": decision.policy_ref,
                    "hook": hook.value,
                },
            )

    def _emit_event(
        self,
        *,
        event_type: str,
        session_id: str,
        producer_entity_id: str,
        activity_id: str | None = None,
        payload: dict[str, Any] | None = None,
        policy_ref: str | None = None,
    ) -> FPEvent:
        event = FPEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            session_id=session_id,
            activity_id=activity_id,
            producer_entity_id=producer_entity_id,
            trace_id=new_trace_id(),
            payload=payload or {},
            policy_ref=policy_ref,
        )
        self.events.publish(event)
        self.metrics.inc("events.emitted")
        return event

    def _emit_org_event(self, organization_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self._emit_event(
            event_type=event_type,
            session_id=f"org:{organization_id}",
            producer_entity_id="fp:system:org-registry",
            payload=payload,
        )

    def _require_entity(self, entity_id: str) -> Entity:
        return self.entities.get(entity_id)

    @staticmethod
    def _idempotency_fingerprint(
        *,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict[str, Any],
    ) -> str:
        stable_payload = {
            "session_id": session_id,
            "owner_entity_id": owner_entity_id,
            "initiator_entity_id": initiator_entity_id,
            "operation": operation,
            "input_payload": input_payload,
        }
        return json.dumps(stable_payload, sort_keys=True, separators=(",", ":"))


def make_default_entity(entity_id: str, kind: EntityKind, display_name: str | None = None) -> Entity:
    return Entity(
        entity_id=entity_id,
        kind=kind,
        display_name=display_name,
        identity=Identity(method="did:example", issuer="fp.local", key_refs=[f"{entity_id}#key-1"], version="v1"),
        capability_summary=CapabilitySummary(purpose=["general"]),
        privacy=PrivacyControl(owner=entity_id),
    )
