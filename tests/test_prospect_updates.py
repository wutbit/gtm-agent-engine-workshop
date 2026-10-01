import json
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from gtm_agent import data_service
from gtm_agent import gtm_agent as gtm_module
from gtm_agent.gtm_agent import ProspectScore, build_prospect_profile, score_prospect


class ProspectUpdateTests(unittest.TestCase):
    prospect_id = "LEAD-39002"

    def setUp(self):
        self.original_tech_stack = list(data_service.PROSPECTS[self.prospect_id]["tech_stack"])
        data_service._PROFILES.pop(self.prospect_id, None)

    def tearDown(self):
        data_service.PROSPECTS[self.prospect_id]["tech_stack"] = self.original_tech_stack
        data_service._PROFILES.pop(self.prospect_id, None)

    def test_update_persists_and_invalidates_cached_profile(self):
        cached = build_prospect_profile.func(self.prospect_id)["prospect_profile"]

        result = data_service.update_prospect_info(self.prospect_id, "Terraform")

        self.assertTrue(result["updated"])
        self.assertIn("Terraform", data_service.fetch_tech_stack(self.prospect_id))
        rebuilt = build_prospect_profile.func(self.prospect_id)["prospect_profile"]
        self.assertIsNot(rebuilt, cached)
        self.assertIn("Terraform", rebuilt["tech_stack"])

    def test_update_is_reflected_in_scoring(self):
        profile = build_prospect_profile.func(self.prospect_id)["prospect_profile"]
        offering = data_service.get_offering("OFFER-10004")
        scores = []

        def score(messages):
            prospect = json.loads(messages[1]["content"].split("\n\nProspect profile:\n", 1)[1])
            has_terraform = "Terraform" in prospect["tech_stack"]
            scores.append(has_terraform)
            return ProspectScore(
                score=80 if has_terraform else 60,
                justification=(
                    "Terraform is present."
                    if has_terraform
                    else "Terraform is missing."
                ),
                rubric_breakdown={
                    "revenue_fit": 30,
                    "tech_stack_match": 40 if has_terraform else 20,
                    "segment_fit": 10,
                },
            )

        with patch.object(gtm_module, "_scoring_llm", Mock(invoke=score)):
            before = score_prospect.func(profile, offering)
            data_service.update_prospect_info(self.prospect_id, "Terraform")
            after = score_prospect.func(profile, offering)

        self.assertEqual(scores, [False, True])
        self.assertIn("Terraform is missing", before["justification"])
        self.assertNotIn("Terraform is missing", after["justification"])
        self.assertGreaterEqual(
            after["rubric_breakdown"]["tech_stack_match"],
            before["rubric_breakdown"]["tech_stack_match"],
        )


if __name__ == "__main__":
    unittest.main()
