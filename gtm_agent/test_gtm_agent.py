import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

package = types.ModuleType("gtm_agent")
package.__path__ = [str(Path(__file__).parent)]
sys.modules.setdefault("gtm_agent", package)
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent import data_service
from gtm_agent.gtm_agent import send_prospect_email


def _send(prospect):
    return send_prospect_email.func(
        prospect=prospect,
        subject="A quick introduction",
        body="Would you be open to a conversation?",
        runtime=SimpleNamespace(config={}),
        from_rep={"email": "rep@example.com", "name": "Sales Rep"},
    )


def test_send_to_disqualified_prospect_is_blocked():
    prospect = {"prospect_id": "LEAD-50001", "email": "priya@example.com", "name": "Priya Nair"}

    result = _send(prospect)

    assert result == {
        "status": "blocked",
        "error": "Prospect is disqualified; email not sent.",
    }


def test_send_to_qualified_prospect_succeeds():
    prospect = {"prospect_id": "LEAD-12853", "email": "omar@example.com", "name": "Omar Okafor"}

    result = _send(prospect)

    assert result["status"] == "sent"
    assert result["to"] == prospect["email"]
    assert result["to_name"] == prospect["name"]
