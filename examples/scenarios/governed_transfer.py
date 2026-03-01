"""Scenario: policy-governed high-risk transfer."""

from __future__ import annotations

from fp.app import FPServer, make_default_entity
from fp.policy import PolicyContext, PolicyEngine, PolicyHook, allow, deny
from fp.protocol import EntityKind, FPError


class ApprovalPolicyEngine(PolicyEngine):
    def evaluate(self, context: PolicyContext):
        if context.hook is PolicyHook.PRE_INVOKE and context.operation == "funds.transfer":
            if context.payload.get("approved_by") != "fp:human:reviewer":
                return deny("high-risk transfer requires reviewer approval", policy_ref="policy:transfer-approval")
        return allow(policy_ref="policy:default")


def run_example() -> dict[str, str]:
    server = FPServer(policy_engine=ApprovalPolicyEngine())
    server.register_entity(make_default_entity("fp:agent:treasurer", EntityKind.AGENT))
    server.register_entity(make_default_entity("fp:human:reviewer", EntityKind.HUMAN))

    session = server.sessions_create(
        participants={"fp:agent:treasurer", "fp:human:reviewer"},
        roles={"fp:agent:treasurer": {"treasurer"}, "fp:human:reviewer": {"reviewer"}},
        policy_ref="policy:transfer-approval",
    )
    server.register_operation("funds.transfer", lambda payload: {"transfer": "ok", "amount": payload["amount"]})

    denied_code = "UNKNOWN"
    try:
        server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:treasurer",
            initiator_entity_id="fp:agent:treasurer",
            operation="funds.transfer",
            input_payload={"amount": 1000},
        )
    except FPError as exc:
        denied_code = exc.code.value

    approved = server.activities_start(
        session_id=session.session_id,
        owner_entity_id="fp:agent:treasurer",
        initiator_entity_id="fp:agent:treasurer",
        operation="funds.transfer",
        input_payload={"amount": 1000, "approved_by": "fp:human:reviewer"},
    )
    return {"denied_code": denied_code, "approved_state": approved.state.value}


def main() -> None:
    print(run_example())


if __name__ == "__main__":
    main()
