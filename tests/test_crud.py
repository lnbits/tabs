import pytest

from tabs.crud import (  # type: ignore[import]
    create_tab,
    create_tab_entry,
    get_tab_by_id,
    get_tab_entries,
    get_tab_for_wallets,
    get_tabs,
    get_tabs_paginated,
    update_tab,
)
from tabs.models import CreateTab, CreateTabEntry  # type: ignore[import]


@pytest.mark.asyncio
async def test_create_and_list_tabs():
    wallet = "wallet_A"
    other_wallet = "wallet_B"

    tab_one = await create_tab(
        CreateTab(
            wallet=wallet,
            name="Morning tab",
            customer_name="Alice",
        )
    )
    tab_two = await create_tab(
        CreateTab(
            wallet=wallet,
            name="Evening tab",
            customer_name="Bob",
        )
    )

    assert tab_one.wallet == wallet
    assert tab_two.wallet == wallet

    owned = await get_tabs([wallet])
    assert len(owned) == 2

    owned_page = await get_tabs_paginated([wallet])
    assert owned_page.total == 2
    assert len(owned_page.data) == 2

    not_owned = await get_tabs([other_wallet])
    assert not not_owned
    assert await get_tab_for_wallets([wallet], tab_one.id) is not None
    assert await get_tab_for_wallets([other_wallet], tab_one.id) is None


@pytest.mark.asyncio
async def test_update_tab_and_entries():
    wallet = "wallet_C"
    tab = await create_tab(CreateTab(wallet=wallet, name="Staff meals"))

    tab.reference = "staff-001"
    tab.currency = "eur"
    tab.limit_type = "hard"
    tab.limit_amount = 25.5
    updated = await update_tab(tab)
    fetched = await get_tab_by_id(updated.id)

    assert fetched is not None
    assert fetched.reference == "staff-001"
    assert fetched.currency == "eur"
    assert fetched.limit_amount == 25.5

    entry = await create_tab_entry(
        tab.id,
        CreateTabEntry(
            entry_type="charge",
            amount=12.5,
            description="Lunch",
            source="test",
            idempotency_key="charge-1",
        ),
    )
    entries = await get_tab_entries(tab.id)

    assert entry.tab_id == tab.id
    assert len(entries) == 1
    assert entries[0].description == "Lunch"
