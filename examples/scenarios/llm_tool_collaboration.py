"""Scenario: LLM + tool collaboration in one FP session."""

from __future__ import annotations

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind


def run_example() -> dict[str, object]:
    server = FPServer()
    server.register_entity(make_default_entity("fp:agent:planner", EntityKind.AGENT))
    server.register_entity(make_default_entity("fp:tool:weather", EntityKind.TOOL))
    server.register_entity(make_default_entity("fp:tool:llm", EntityKind.TOOL))

    session = server.sessions_create(
        participants={"fp:agent:planner", "fp:tool:weather", "fp:tool:llm"},
        roles={
            "fp:agent:planner": {"coordinator"},
            "fp:tool:weather": {"provider"},
            "fp:tool:llm": {"provider"},
        },
        policy_ref="policy:travel-planning",
    )

    server.register_operation("weather.lookup", lambda payload: {"city": payload["city"], "forecast": "sunny"})
    server.register_operation(
        "llm.summarize",
        lambda payload: {"itinerary": f"{payload['city']} is {payload['forecast']}; bring light clothes."},
    )

    weather = server.activities_start(
        session_id=session.session_id,
        owner_entity_id="fp:tool:weather",
        initiator_entity_id="fp:agent:planner",
        operation="weather.lookup",
        input_payload={"city": "San Francisco"},
    )
    weather_result = server.activities_result(activity_id=weather.activity_id)["result"]

    summary = server.activities_start(
        session_id=session.session_id,
        owner_entity_id="fp:tool:llm",
        initiator_entity_id="fp:agent:planner",
        operation="llm.summarize",
        input_payload={
            "city": weather_result["city"],
            "forecast": weather_result["forecast"],
        },
    )
    summary_result = server.activities_result(activity_id=summary.activity_id)["result"]

    return {
        "weather_state": weather.state.value,
        "summary_state": summary.state.value,
        "summary_result": summary_result,
    }


def main() -> None:
    output = run_example()
    print(output)


if __name__ == "__main__":
    main()
