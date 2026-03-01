"""Scenario: metering, receipt issuance, and settlement confirmation."""

from __future__ import annotations

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind


def run_example() -> dict[str, object]:
    server = FPServer()
    server.register_entity(make_default_entity("fp:agent:buyer", EntityKind.AGENT))
    server.register_entity(make_default_entity("fp:agent:seller", EntityKind.AGENT))

    session = server.sessions_create(
        participants={"fp:agent:buyer", "fp:agent:seller"},
        roles={"fp:agent:buyer": {"consumer"}, "fp:agent:seller": {"provider"}},
        policy_ref="policy:procurement",
    )

    server.register_operation("service.provision", lambda _: {"state": "working"})

    activity = server.activities_start(
        session_id=session.session_id,
        owner_entity_id="fp:agent:seller",
        initiator_entity_id="fp:agent:buyer",
        operation="service.provision",
        input_payload={"terms_ref": "terms://signed/v1"},
    )
    server.activities_complete(
        activity_id=activity.activity_id,
        result_ref="deliverable://svc/alpha",
        producer_entity_id="fp:agent:seller",
    )

    meter = server.meter_record(
        subject_ref=activity.activity_id,
        unit="call",
        quantity=1,
        metering_policy_ref="policy:metering",
    )
    receipt = server.receipts_issue(
        activity_id=activity.activity_id,
        provider_entity_id="fp:agent:seller",
        meter_records=[meter],
    )

    settlement = server.settlements_create(
        receipt_refs=[receipt.receipt_id],
        settlement_ref="payment://network/txn-001",
        amount=49.99,
        currency="USD",
        actor_entity_id="fp:agent:buyer",
    )
    confirmed = server.settlements_confirm(settlement.settlement_id)
    return {
        "receipt_verified": server.receipts.verify(receipt),
        "settlement_status": confirmed.status.value,
        "amount": confirmed.amount,
    }


def main() -> None:
    print(run_example())


if __name__ == "__main__":
    main()
