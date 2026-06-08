import pytest
from httpx import AsyncClient
from lnbits.core.services.users import create_user_account_no_ckeck
from lnbits.helpers import create_access_token

from tabs.crud import create_tab, create_tab_settlement, get_tab_settlement  # type: ignore[import]
from tabs.models import CreateTab, CreateTabEntry, CreateTabSettlement  # type: ignore[import]
from tabs.services import complete_settlement, post_entry  # type: ignore[import]


@pytest.mark.asyncio
async def test_tabs_api_happy_flow(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    token = create_access_token({"sub": "", "usr": user.id}, token_expire_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/tabs/api/v1/tabs",
        json={"wallet": wallet.id, "name": "Main Bar", "customer_name": "Alice", "currency": "sats"},
        headers=headers,
    )
    assert create_response.status_code == 201
    tab = create_response.json()
    assert tab["wallet"] == wallet.id
    assert tab["status"] == "open"
    assert tab["balance"] == 0

    charge_response = await client.post(
        f"/tabs/api/v1/tabs/{tab['id']}/entries",
        json={
            "entry_type": "charge",
            "amount": 25000,
            "description": "Drinks",
            "source": "tpos",
            "idempotency_key": "charge-1",
        },
        headers=headers,
    )
    assert charge_response.status_code == 201
    charge = charge_response.json()
    assert charge["entry_type"] == "charge"
    assert charge["amount"] == 25000

    settlement_response = await client.post(
        f"/tabs/api/v1/tabs/{tab['id']}/settlements",
        json={
            "amount": 25000,
            "method": "cash",
            "reference": "till-close",
        },
        headers=headers,
    )
    assert settlement_response.status_code == 201
    settlement = settlement_response.json()["settlement"]
    assert settlement["status"] == "completed"
    assert settlement["amount"] == 25000
    assert settlement["method"] == "cash"

    get_response = await client.get(f"/tabs/api/v1/tabs/{tab['id']}", headers=headers)
    assert get_response.status_code == 200
    updated_tab = get_response.json()
    assert updated_tab["balance"] == 0
    assert updated_tab["status"] == "closed"


@pytest.mark.asyncio
async def test_create_tab_persists_normalized_payload(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    token = create_access_token({"sub": "", "usr": user.id}, token_expire_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/tabs/api/v1/tabs",
        json={
            "wallet": wallet.id,
            "name": "Cafe",
            "currency": "SATS",
            "limit_type": "none",
            "limit_amount": 100,
        },
        headers=headers,
    )

    assert response.status_code == 201
    tab = response.json()
    assert tab["currency"] == "sats"
    assert tab["limit_amount"] is None


@pytest.mark.asyncio
async def test_public_tab_endpoint_exposes_only_public_fields(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(
        CreateTab(
            wallet=wallet.id,
            name="Patio Tab",
            customer_name="Bob",
            reference="Fat Joe",
        )
    )

    response = await client.get(f"/tabs/api/v1/public/tabs/{tab.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == tab.id
    assert payload["name"] == "Patio Tab"
    assert payload["customer_name"] == "Bob"
    assert "wallet" not in payload
    assert "reference" not in payload


@pytest.mark.asyncio
async def test_update_tab_rejects_currency_change_after_history(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    token = create_access_token({"sub": "", "usr": user.id}, token_expire_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Staff"))
    await post_entry(tab, CreateTabEntry(entry_type="charge", amount=100))

    response = await client.put(
        f"/tabs/api/v1/tabs/{tab.id}",
        json={
            "name": "Staff",
            "currency": "eur",
            "limit_type": "none",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot change currency after tab history exists."


@pytest.mark.asyncio
async def test_update_tab_rejects_archived_tabs(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    token = create_access_token({"sub": "", "usr": user.id}, token_expire_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Quiet"))

    archive_response = await client.post(f"/tabs/api/v1/tabs/{tab.id}/archive", headers=headers)
    assert archive_response.status_code == 200

    response = await client.put(
        f"/tabs/api/v1/tabs/{tab.id}",
        json={
            "name": "Changed",
            "currency": "sats",
            "limit_type": "none",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Archived tabs are read-only."


@pytest.mark.asyncio
async def test_public_settlement_rejects_when_pending_settlement_covers_balance(client: AsyncClient, monkeypatch):
    class FakePayment:
        payment_hash = "hash-1"
        checking_id = "checking-1"
        bolt11 = "bolt11-1"

    async def fake_create_invoice(**kwargs):
        return FakePayment()

    monkeypatch.setattr("tabs.services.create_invoice", fake_create_invoice)
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    await post_entry(tab, CreateTabEntry(entry_type="charge", amount=100))

    first_response = await client.post(f"/tabs/api/v1/public/tabs/{tab.id}/settlements", json={})
    assert first_response.status_code == 201

    second_response = await client.post(f"/tabs/api/v1/public/tabs/{tab.id}/settlements", json={})
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "This tab has no available balance to settle."


@pytest.mark.asyncio
async def test_complete_settlement_does_not_mark_completed_when_entry_fails():
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    settlement = await create_tab_settlement(
        tab.id,
        CreateTabSettlement(amount=100, method="cash"),
    )

    with pytest.raises(Exception):
        await complete_settlement(settlement)

    persisted = await get_tab_settlement(settlement.id)
    assert persisted is not None
    assert persisted.status == "pending"
    assert persisted.completed_at is None


@pytest.mark.asyncio
async def test_public_tab_entries_returns_404_for_unknown_tab(client: AsyncClient):
    response = await client.get("/tabs/api/v1/public/tabs/nonexistent/entries")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_tab_entries_omit_internal_audit_fields(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    await post_entry(
        tab,
        CreateTabEntry(
            entry_type="charge",
            amount=100,
            description="Private item",
            metadata='{"operator": "alice"}',
            source="tpos",
            source_id="sale-1",
            source_action="cart",
            operator_user_id=user.id,
            idempotency_key="charge-1",
        ),
    )

    response = await client.get(f"/tabs/api/v1/public/tabs/{tab.id}/entries")

    assert response.status_code == 200
    entry = response.json()[0]
    assert entry == {
        "entry_type": "charge",
        "amount": 100.0,
        "created_at": entry["created_at"],
    }
