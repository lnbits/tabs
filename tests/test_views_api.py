import asyncio
from types import SimpleNamespace

import pytest
from fastapi.exceptions import HTTPException
from httpx import AsyncClient
from lnbits.core.services.users import create_user_account_no_ckeck
from lnbits.helpers import create_access_token

from tabs.crud import (  # type: ignore[import]
    create_tab,
    create_tab_settlement,
    get_tab_by_id,
    get_tab_entries,
    get_tab_settlement,
    get_tab_settlements,
)
from tabs.models import CreateTab, CreateTabEntry, CreateTabSettlement  # type: ignore[import]
from tabs.services import (  # type: ignore[import]
    complete_manual_settlement,
    create_settlement,
    payment_received_for_settlement,
    post_entry,
)


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

    with pytest.raises(HTTPException):
        await complete_manual_settlement(settlement)

    persisted = await get_tab_settlement(settlement.id)
    assert persisted is not None
    assert persisted.status == "pending"
    assert persisted.completed_at is None


@pytest.mark.asyncio
async def test_lightning_settlements_cannot_be_completed_or_cancelled_manually(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    settlement = await create_tab_settlement(
        tab.id,
        CreateTabSettlement(amount=100, method="lightning"),
    )

    with pytest.raises(HTTPException, match="complete when their invoice is paid"):
        await complete_manual_settlement(settlement)

    token = create_access_token({"sub": "", "usr": user.id}, token_expire_minutes=5)
    response = await client.post(
        f"/tabs/api/v1/settlements/{settlement.id}/mark-complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404

    response = await client.post(
        f"/tabs/api/v1/settlements/{settlement.id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_paid_lightning_invoice_is_completed_by_the_listener():
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    await post_entry(tab, CreateTabEntry(entry_type="charge", amount=100))
    settlement = await create_tab_settlement(
        tab.id,
        CreateTabSettlement(amount=100, method="lightning"),
    )

    assert await payment_received_for_settlement(
        SimpleNamespace(payment_hash="hash-1", checking_id="checking-1", extra={"settlement_id": settlement.id})
    )
    persisted = await get_tab_settlement(settlement.id)
    assert persisted and persisted.status == "completed"


@pytest.mark.asyncio
async def test_concurrent_idempotent_entries_are_stored_once():
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    entry = CreateTabEntry(entry_type="charge", amount=100, idempotency_key="charge-1")

    await asyncio.gather(post_entry(tab, entry), post_entry(tab, entry.copy()))

    entries = await get_tab_entries(tab.id)
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_idempotent_entry_does_not_duplicate_balance():
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))

    await post_entry(tab, CreateTabEntry(entry_type="charge", amount=100, idempotency_key="charge-1"))
    _, entry = await post_entry(
        tab,
        CreateTabEntry(entry_type="charge", amount=100, idempotency_key="charge-1"),
    )

    entries = await get_tab_entries(tab.id)
    updated_tab = await get_tab_by_id(tab.id)
    assert len(entries) == 1
    assert entry.id == entries[0].id
    assert updated_tab is not None
    assert updated_tab.balance == 100


@pytest.mark.asyncio
async def test_lightning_settlement_invoice_failure_does_not_persist_settlement(monkeypatch):
    async def fake_create_invoice(**kwargs):
        raise RuntimeError("invoice failed")

    monkeypatch.setattr("tabs.services.create_invoice", fake_create_invoice)
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    await post_entry(tab, CreateTabEntry(entry_type="charge", amount=100))

    with pytest.raises(RuntimeError):
        await create_settlement(tab, CreateTabSettlement(amount=100, method="lightning"))

    assert await get_tab_settlements(tab.id) == []
    updated_tab = await get_tab_by_id(tab.id)
    assert updated_tab and updated_tab.pending_settlement_amount == 0


@pytest.mark.asyncio
async def test_concurrent_lightning_settlements_cannot_exceed_tab_balance(monkeypatch):
    class FakePayment:
        payment_hash = "hash-1"
        checking_id = "checking-1"
        bolt11 = "bolt11-1"

    invoice_started = asyncio.Event()
    release_invoice = asyncio.Event()

    async def fake_create_invoice(**kwargs):
        invoice_started.set()
        await release_invoice.wait()
        return FakePayment()

    monkeypatch.setattr("tabs.services.create_invoice", fake_create_invoice)
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    await post_entry(tab, CreateTabEntry(entry_type="charge", amount=100))

    first = asyncio.create_task(create_settlement(tab, CreateTabSettlement(amount=100, method="lightning")))
    await invoice_started.wait()
    with pytest.raises(HTTPException, match="no available balance"):
        await create_settlement(tab, CreateTabSettlement(amount=100, method="lightning"))
    release_invoice.set()
    await first


@pytest.mark.asyncio
async def test_public_tab_entries_returns_404_for_unknown_tab(client: AsyncClient):
    response = await client.get("/tabs/api/v1/public/tabs/nonexistent/entries")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_tab_entries_include_line_details_without_internal_audit_fields(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    tab = await create_tab(CreateTab(wallet=wallet.id, name="Patio Tab"))
    await post_entry(
        tab,
        CreateTabEntry(
            entry_type="charge",
            amount=100,
            description="Private item",
            unit_label="drink",
            quantity=2,
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
    assert entry["id"]
    assert entry["entry_type"] == "charge"
    assert entry["amount"] == 100.0
    assert entry["description"] == "Private item"
    assert entry["unit_label"] == "drink"
    assert entry["quantity"] == 2.0
    assert entry["created_at"]
    assert "metadata" not in entry
    assert "source" not in entry
    assert "source_id" not in entry
    assert "source_action" not in entry
    assert "operator_user_id" not in entry
    assert "idempotency_key" not in entry
