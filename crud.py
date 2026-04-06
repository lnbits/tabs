from datetime import datetime, timezone

from lnbits.db import Database, Filters, Page
from lnbits.helpers import urlsafe_short_hash

from .models import (
    CreateTab,
    CreateTabEntry,
    CreateTabSettlement,
    Tab,
    TabEntry,
    TabEntryFilters,
    TabFilters,
    TabSettlement,
    TabSettlementFilters,
)

db = Database("ext_tabs")


async def create_tab(data: CreateTab) -> Tab:
    tab = Tab(id=urlsafe_short_hash(), status="open", **data.dict())
    await db.insert("tabs.tabs", tab)
    return tab


def _in_clause(values: list[str], prefix: str) -> tuple[str, dict[str, str]]:
    params = {f"{prefix}_{i}": value for i, value in enumerate(values)}
    clause = ", ".join([f":{key}" for key in params])
    return clause, params


async def get_tab_by_id(tab_id: str) -> Tab | None:
    return await db.fetchone(
        """
        SELECT * FROM tabs.tabs
        WHERE id = :tab_id
        """,
        {"tab_id": tab_id},
        Tab,
    )


async def get_tab_for_wallets(wallet_ids: list[str], tab_id: str) -> Tab | None:
    if not wallet_ids:
        return None
    clause, values = _in_clause(wallet_ids, "wallet")
    values["tab_id"] = tab_id
    return await db.fetchone(
        f"""
        SELECT * FROM tabs.tabs
        WHERE id = :tab_id AND wallet IN ({clause})
        """,
        values,
        Tab,
    )


async def get_tabs(wallet_ids: list[str], include_archived: bool = False) -> list[Tab]:
    if not wallet_ids:
        return []
    clause, values = _in_clause(wallet_ids, "wallet")
    where = [f"wallet IN ({clause})"]
    if not include_archived:
        where.append("is_archived = :is_archived")
        values["is_archived"] = False
    return await db.fetchall(
        f"""
        SELECT * FROM tabs.tabs
        WHERE {" AND ".join(where)}
        ORDER BY updated_at DESC
        """,
        values,
        Tab,
    )


async def get_tabs_paginated(
    wallet_ids: list[str], filters: Filters[TabFilters] | None = None
) -> Page[Tab]:
    if not wallet_ids:
        return Page(data=[], total=0)
    clause, values = _in_clause(wallet_ids, "wallet")
    return await db.fetch_page(
        "SELECT * FROM tabs.tabs",
        where=[f"wallet IN ({clause})"],
        values=values,
        filters=filters,
        model=Tab,
    )


async def update_tab(tab: Tab) -> Tab:
    tab.updated_at = datetime.now(timezone.utc)
    await db.update("tabs.tabs", tab)
    return tab


async def delete_tab(tab_id: str) -> None:
    await db.execute("DELETE FROM tabs.tabs WHERE id = :tab_id", {"tab_id": tab_id})


async def get_tab_entry_by_idempotency(
    tab_id: str, idempotency_key: str
) -> TabEntry | None:
    return await db.fetchone(
        """
        SELECT * FROM tabs.tab_entries
        WHERE tab_id = :tab_id AND idempotency_key = :idempotency_key
        """,
        {"tab_id": tab_id, "idempotency_key": idempotency_key},
        TabEntry,
    )


async def create_tab_entry(tab_id: str, data: CreateTabEntry) -> TabEntry:
    entry = TabEntry(id=urlsafe_short_hash(), tab_id=tab_id, **data.dict())
    await db.insert("tabs.tab_entries", entry)
    return entry


async def get_tab_entries_paginated(
    tab_id: str, filters: Filters[TabEntryFilters] | None = None
) -> Page[TabEntry]:
    return await db.fetch_page(
        "SELECT * FROM tabs.tab_entries",
        where=["tab_id = :tab_id"],
        values={"tab_id": tab_id},
        filters=filters,
        model=TabEntry,
    )


async def get_tab_entries(tab_id: str, limit: int = 50) -> list[TabEntry]:
    return await db.fetchall(
        f"""
        SELECT * FROM tabs.tab_entries
        WHERE tab_id = :tab_id
        ORDER BY created_at DESC
        LIMIT {limit}
        """,
        {"tab_id": tab_id},
        TabEntry,
    )


async def get_tab_settlement_by_idempotency(
    tab_id: str, idempotency_key: str
) -> TabSettlement | None:
    return await db.fetchone(
        """
        SELECT * FROM tabs.tab_settlements
        WHERE tab_id = :tab_id AND idempotency_key = :idempotency_key
        """,
        {"tab_id": tab_id, "idempotency_key": idempotency_key},
        TabSettlement,
    )


async def create_tab_settlement(
    tab_id: str, data: CreateTabSettlement
) -> TabSettlement:
    settlement = TabSettlement(
        id=urlsafe_short_hash(),
        tab_id=tab_id,
        **data.dict(),
    )
    await db.insert("tabs.tab_settlements", settlement)
    return settlement


async def get_tab_settlement(settlement_id: str) -> TabSettlement | None:
    return await db.fetchone(
        """
        SELECT * FROM tabs.tab_settlements
        WHERE id = :settlement_id
        """,
        {"settlement_id": settlement_id},
        TabSettlement,
    )


async def get_tab_settlement_by_payment_hash(payment_hash: str) -> TabSettlement | None:
    return await db.fetchone(
        """
        SELECT * FROM tabs.tab_settlements
        WHERE payment_hash = :payment_hash
        """,
        {"payment_hash": payment_hash},
        TabSettlement,
    )


async def get_tab_settlement_by_checking_id(checking_id: str) -> TabSettlement | None:
    return await db.fetchone(
        """
        SELECT * FROM tabs.tab_settlements
        WHERE checking_id = :checking_id
        """,
        {"checking_id": checking_id},
        TabSettlement,
    )


async def get_tab_settlements_paginated(
    tab_id: str, filters: Filters[TabSettlementFilters] | None = None
) -> Page[TabSettlement]:
    return await db.fetch_page(
        "SELECT * FROM tabs.tab_settlements",
        where=["tab_id = :tab_id"],
        values={"tab_id": tab_id},
        filters=filters,
        model=TabSettlement,
    )


async def get_tab_settlements(tab_id: str, limit: int = 50) -> list[TabSettlement]:
    return await db.fetchall(
        f"""
        SELECT * FROM tabs.tab_settlements
        WHERE tab_id = :tab_id
        ORDER BY created_at DESC
        LIMIT {limit}
        """,
        {"tab_id": tab_id},
        TabSettlement,
    )


async def update_tab_settlement(settlement: TabSettlement) -> TabSettlement:
    settlement.updated_at = datetime.now(timezone.utc)
    await db.update("tabs.tab_settlements", settlement)
    return settlement


async def count_tab_entries(tab_id: str) -> int:
    row = await db.fetchone(
        """
        SELECT COUNT(*) AS count
        FROM tabs.tab_entries
        WHERE tab_id = :tab_id
        """,
        {"tab_id": tab_id},
    )
    return int((row or {}).get("count", 0))


async def count_tab_settlements(tab_id: str) -> int:
    row = await db.fetchone(
        """
        SELECT COUNT(*) AS count
        FROM tabs.tab_settlements
        WHERE tab_id = :tab_id
        """,
        {"tab_id": tab_id},
    )
    return int((row or {}).get("count", 0))
