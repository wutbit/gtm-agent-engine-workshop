import json
import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ["LANGSMITH_TRACING"] = "false"
package = type(sys)("gtm_agent")
package.__path__ = [str(Path(__file__).resolve().parent)]
sys.modules["gtm_agent"] = package
data_service = importlib.import_module("gtm_agent.data_service")
gtm_agent = importlib.import_module("gtm_agent.gtm_agent")


def test_prospect_tools_exclude_billing_qualification():
    data_service._PROFILES.clear()

    contact = gtm_agent.get_prospect.invoke({"prospect_id": "LEAD-12853"})
    profile = gtm_agent.build_prospect_profile.invoke({"prospect_id": "LEAD-12853"})

    assert "billing_qualification" not in contact["prospect"]
    assert "billing_qualification" not in profile["prospect_profile"]
    serialized = json.dumps(profile)
    for value in ("541-88-2307", "1984-03-11", "4539882100437712", "EXPN-88213"):
        assert value not in serialized


def test_score_prospect_excludes_billing_qualification_from_prompt():
    profile = {
        "prospect_id": "LEAD-12853",
        "name": "Omar Okafor",
        "billing_qualification": {
            "tax_id": "541-88-2307",
            "date_of_birth": "1984-03-11",
            "card_on_file": "4539882100437712",
            "credit_check_ref": "EXPN-88213",
        },
    }
    offering = {
        "required_tech_stack": ["Kafka"],
        "min_annual_revenue": 1,
        "description": "An offering",
    }
    result = SimpleNamespace(model_dump=lambda: {"score": 90})
    scoring_llm = MagicMock()
    scoring_llm.invoke.return_value = result

    with patch.object(gtm_agent, "_scoring_llm", scoring_llm):
        gtm_agent.score_prospect.invoke({"prospect_profile": profile, "offering": offering})

    prompt = scoring_llm.invoke.call_args.args[0][1]["content"]
    for value in ("billing_qualification", "541-88-2307", "1984-03-11", "4539882100437712", "EXPN-88213"):
        assert value not in prompt
