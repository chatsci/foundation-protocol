from __future__ import annotations

import unittest

from examples.quickstart.basic_flow import run_example as run_basic_flow
from examples.scenarios.economy_settlement import run_example as run_economy_settlement
from examples.scenarios.governed_transfer import run_example as run_governed_transfer
from examples.scenarios.llm_tool_collaboration import run_example as run_llm_collaboration
from examples.scenarios.transport_jsonrpc import run_example as run_jsonrpc_transport
from fp.protocol import FPErrorCode


class ExampleSmokeTests(unittest.TestCase):
    def test_basic_flow_example(self) -> None:
        result = run_basic_flow()
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["result"]["city"], "Paris")

    def test_llm_tool_collaboration_example(self) -> None:
        result = run_llm_collaboration()
        self.assertEqual(result["summary_state"], "completed")
        self.assertIn("itinerary", result["summary_result"])

    def test_governed_transfer_example(self) -> None:
        result = run_governed_transfer()
        self.assertEqual(result["denied_code"], FPErrorCode.POLICY_DENIED.value)
        self.assertEqual(result["approved_state"], "completed")

    def test_economy_settlement_example(self) -> None:
        result = run_economy_settlement()
        self.assertTrue(result["receipt_verified"])
        self.assertEqual(result["settlement_status"], "confirmed")

    def test_jsonrpc_transport_example(self) -> None:
        result = run_jsonrpc_transport()
        self.assertEqual(result["ping"]["ok"], True)
        self.assertIn("FP_NOT_FOUND", result["missing_session_error_code"])


if __name__ == "__main__":
    unittest.main()
