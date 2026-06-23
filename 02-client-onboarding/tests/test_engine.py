from src.config import BASE_STEPS, DEFAULT_CONFIG
from src.engine import onboard_deal, required_steps
from src.models import WonDeal
from src.provisioning_client import ProvisioningClient


def _deal(plan, deal_id="DEAL-1"):
    return WonDeal(deal_id=deal_id, company="Acme", contact_email="a@acme.com", plan=plan, seats=10)


def test_smb_required_steps_are_base_only():
    steps = required_steps(_deal("smb"))
    assert steps == list(BASE_STEPS)
    assert "assign_csm" not in steps


def test_pro_required_steps_are_base_only():
    steps = required_steps(_deal("pro"))
    assert steps == list(BASE_STEPS)
    assert "assign_csm" not in steps


def test_enterprise_gets_assign_csm():
    steps = required_steps(_deal("enterprise"))
    assert "assign_csm" in steps
    # Base steps preserved and the extra is appended last.
    assert steps[: len(BASE_STEPS)] == list(BASE_STEPS)
    assert steps[-1] == "assign_csm"


def test_unknown_plan_falls_back_to_base():
    steps = required_steps(_deal("startup"))
    assert steps == list(BASE_STEPS)


def test_onboard_provisions_all_steps_first_run(tmp_path):
    prov = ProvisioningClient(tmp_path / "store.json")
    result = onboard_deal(_deal("enterprise"), prov)
    assert result.completed == required_steps(_deal("enterprise"))
    assert result.skipped == []
    assert result.failed == []
    assert result.percent_complete == 100
    assert result.status == "onboarded"


def test_percent_complete_partial(tmp_path):
    """If some steps were already done, percent still reflects total finished / required."""
    prov = ProvisioningClient(tmp_path / "store.json")
    deal = _deal("smb")
    # Pre-provision two of the five base steps.
    prov.provision("provision_account", deal.deal_id)
    prov.provision("create_workspace", deal.deal_id)
    result = onboard_deal(deal, prov)
    assert len(result.skipped) == 2
    assert len(result.completed) == 3
    assert result.percent_complete == 100  # all required steps now finished
    assert result.done_count == 5
