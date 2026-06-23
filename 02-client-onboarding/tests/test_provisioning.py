from src.provisioning_client import ProvisioningClient, _key


def test_provision_is_new_first_time(tmp_path):
    prov = ProvisioningClient(tmp_path / "store.json")
    assert prov.provision("provision_account", "DEAL-1") is True
    assert prov.is_done("provision_account", "DEAL-1") is True


def test_provision_is_idempotent(tmp_path):
    prov = ProvisioningClient(tmp_path / "store.json")
    assert prov.provision("create_workspace", "DEAL-1") is True
    # Second call: already done, no new work.
    assert prov.provision("create_workspace", "DEAL-1") is False
    assert prov.count() == 1


def test_key_is_per_deal_and_step():
    assert _key("DEAL-1", "add_to_billing") == "DEAL-1:add_to_billing"
    # Same step, different deal -> different key (no cross-deal collision).
    assert _key("DEAL-1", "add_to_billing") != _key("DEAL-2", "add_to_billing")


def test_provision_requires_deal_id(tmp_path):
    prov = ProvisioningClient(tmp_path / "store.json")
    try:
        prov.provision("provision_account", "")
        assert False, "expected ValueError"
    except ValueError:
        pass
