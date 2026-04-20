import pytest
from httpx import AsyncClient

from lnbits.core.services.users import create_user_account_no_ckeck
from lnbits.helpers import create_access_token

from tabs.crud import create_tab  # type: ignore[import]
from tabs.models import CreateTab  # type: ignore[import]


@pytest.mark.asyncio
async def test_tabs_api_happy_flow(client: AsyncClient):
    user = await create_user_account_no_ckeck()
    wallet = user.wallets[0]
    token = create_access_token({"sub": "", "usr": user.id}, token_expire_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/tabs/api/v1/tabs",
        json={
            "wallet": wallet.id,
            "name": "Main Bar",
            "customer_name": "Alice",
            "currency": "sats"
        },
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
async def test_public_tab_entries_returns_404_for_unknown_tab(client: AsyncClient):
    response = await client.get("/tabs/api/v1/public/tabs/nonexistent/entries")
    assert response.status_code == 404
