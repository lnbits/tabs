from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import HTTPException
from lnbits.core.crud import get_wallet
from lnbits.core.models import Payment
from lnbits.core.services import create_invoice

from .crud import (
    count_tab_entries,
    count_tab_settlements,
    create_tab_entry,
    create_tab_settlement,
    delete_tab,
    get_tab_by_id,
    get_tab_entry_by_idempotency,
    get_tab_settlement,
    get_tab_settlement_by_checking_id,
    get_tab_settlement_by_idempotency,
    get_tab_settlement_by_payment_hash,
    update_tab,
    update_tab_settlement,
)
from .models import (
    CreateTabEntry,
    CreateTabSettlement,
    SETTLEMENT_METHODS,
    SETTLEMENT_STATUSES,
    SettlementCreateResponse,
    TAB_ENTRY_TYPES,
    TAB_LIMIT_TYPES,
    TAB_STATUSES,
    Tab,
    TabEntry,
    TabSettlement,
    UpdateTabStatus,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_sats(currency: str | None) -> bool:
    return (currency or "sats").lower() == "sats"


def _normalize_amount(currency: str, amount: float | int | None) -> float:
    if amount is None:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Amount is required.")
    try:
        numeric = float(amount)
    except (TypeError, ValueError) as exc:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid amount.") from exc
    if _is_sats(currency):
        if numeric != int(numeric):
            raise HTTPException(HTTPStatus.BAD_REQUEST, "Sats amounts must be whole numbers.")
        return float(int(numeric))
    return round(numeric, 2)


def _is_zero(currency: str, amount: float) -> bool:
    return amount == 0 if _is_sats(currency) else abs(amount) < 0.005


def _entry_delta(entry_type: str, amount: float) -> float:
    if entry_type == "charge":
        return amount
    if entry_type in {"credit", "settlement"}:
        return -amount
    if entry_type == "adjustment":
        return amount
    return 0


def _validate_tab_status(status: str) -> None:
    if status not in TAB_STATUSES:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid tab status.")


def _validate_limit_type(limit_type: str) -> None:
    if limit_type not in TAB_LIMIT_TYPES:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid tab limit type.")


def _validate_entry_type(entry_type: str) -> None:
    if entry_type not in TAB_ENTRY_TYPES:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid tab entry type.")


def _validate_settlement_method(method: str) -> None:
    if method not in SETTLEMENT_METHODS:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid settlement method.")


def _validate_settlement_status(status: str) -> None:
    if status not in SETTLEMENT_STATUSES:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid settlement status.")


async def validate_tab_wallet_ownership(user_id: str, wallet_id: str) -> None:
    wallet = await get_wallet(wallet_id)
    if not wallet or wallet.user != user_id:
        raise HTTPException(
            HTTPStatus.FORBIDDEN, "Invalid wallet. Must belong to authenticated user."
        )


def validate_tab_payload(tab: Tab) -> None:
    _validate_tab_status(tab.status)
    _validate_limit_type(tab.limit_type)
    tab.currency = (tab.currency or "sats").lower()
    if tab.limit_type == "hard":
        if tab.limit_amount is None:
            raise HTTPException(
                HTTPStatus.BAD_REQUEST,
                "A hard limit requires a limit amount.",
            )
        tab.limit_amount = _normalize_amount(tab.currency, tab.limit_amount)
        if tab.limit_amount < 0:
            raise HTTPException(
                HTTPStatus.BAD_REQUEST,
                "A hard limit requires a non-negative limit amount.",
            )
    else:
        tab.limit_amount = None


def _validate_entry_amount(tab: Tab, entry_type: str, amount: float | None) -> float:
    if entry_type == "note":
        if amount not in (None, 0):
            raise HTTPException(
                HTTPStatus.BAD_REQUEST, "Note entries cannot change the balance."
            )
        return 0
    normalized = _normalize_amount(tab.currency, amount)
    if normalized <= 0 and entry_type in {"charge", "credit", "settlement"}:
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Amount must be greater than zero."
        )
    return normalized


def _validate_entry_against_tab(tab: Tab, entry: CreateTabEntry, amount: float) -> None:
    if tab.is_archived:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Archived tabs are read-only.")
    if tab.status == "closed" and entry.entry_type != "note":
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Closed tabs cannot accept new entries.")
    if tab.status == "suspended" and entry.entry_type == "charge":
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Suspended tabs cannot accept new charges."
        )

    next_balance = round(tab.balance + _entry_delta(entry.entry_type, amount), 2)
    if next_balance < 0 and not _is_zero(tab.currency, next_balance):
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Entry would make the tab balance negative."
        )
    if (
        entry.entry_type == "charge"
        and tab.limit_type == "hard"
        and tab.limit_amount is not None
        and next_balance > tab.limit_amount
    ):
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Charge would exceed the configured tab limit."
        )


async def post_entry(tab: Tab, data: CreateTabEntry) -> tuple[Tab, TabEntry]:
    _validate_entry_type(data.entry_type)
    amount = _validate_entry_amount(tab, data.entry_type, data.amount)

    if data.idempotency_key:
        existing = await get_tab_entry_by_idempotency(tab.id, data.idempotency_key)
        if existing:
            return tab, existing

    _validate_entry_against_tab(tab, data, amount)
    data.amount = amount

    entry = await create_tab_entry(tab.id, data)
    tab.balance = round(tab.balance + _entry_delta(entry.entry_type, entry.amount), 2)
    if _is_zero(tab.currency, tab.balance):
        tab.balance = 0
    await update_tab(tab)
    return tab, entry


async def update_status(tab: Tab, data: UpdateTabStatus) -> Tab:
    _validate_tab_status(data.status)
    if tab.is_archived:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Archived tabs cannot change status.")
    if tab.status == "closed" and data.status != "closed":
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Closed tabs cannot be reopened.")
    if data.status == "closed" and not _is_zero(tab.currency, tab.balance):
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Tabs can only be closed when the balance is zero."
        )

    tab.status = data.status
    if data.status == "closed":
        tab.closed_at = _utc_now()
        tab.balance = 0
    await update_tab(tab)
    return tab


async def archive_tab(tab: Tab) -> Tab:
    if not _is_zero(tab.currency, tab.balance):
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Only fully settled tabs can be archived."
        )
    tab.is_archived = True
    tab.archived_at = _utc_now()
    await update_tab(tab)
    return tab


async def delete_tab_if_empty(tab: Tab) -> None:
    if not _is_zero(tab.currency, tab.balance):
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Cannot delete a tab with a non-zero balance."
        )
    if await count_tab_entries(tab.id) > 0 or await count_tab_settlements(tab.id) > 0:
        raise HTTPException(
            HTTPStatus.BAD_REQUEST,
            "Cannot delete a tab with financial history. Archive it instead.",
        )
    await delete_tab(tab.id)


async def create_settlement(tab: Tab, data: CreateTabSettlement) -> SettlementCreateResponse:
    _validate_settlement_method(data.method)

    if tab.is_archived:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Archived tabs are read-only.")
    if tab.status == "closed":
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Closed tabs cannot be settled.")
    if _is_zero(tab.currency, tab.balance) or tab.balance <= 0:
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "This tab has no outstanding balance to settle."
        )

    amount = _normalize_amount(tab.currency, data.amount or tab.balance)
    if amount <= 0:
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Settlement amount must be greater than zero."
        )
    if amount > tab.balance:
        raise HTTPException(
            HTTPStatus.BAD_REQUEST,
            "Settlement amount cannot exceed the outstanding balance.",
        )
    data.amount = amount

    if data.idempotency_key:
        existing = await get_tab_settlement_by_idempotency(tab.id, data.idempotency_key)
        if existing:
            return SettlementCreateResponse(
                settlement=existing, payment_request=existing.payment_request
            )

    if data.method == "lightning":
        settlement = await create_tab_settlement(tab.id, data)
        invoice_kwargs = {
            "wallet_id": tab.wallet,
            "amount": settlement.amount,
            "memo": f"Tab settlement: {tab.name}",
            "extra": {
                "tag": "tabs",
                "tab_id": tab.id,
                "settlement_id": settlement.id,
            },
        }
        if not _is_sats(tab.currency):
            invoice_kwargs["currency"] = tab.currency
        payment = await create_invoice(**invoice_kwargs)
        settlement.payment_hash = payment.payment_hash
        settlement.checking_id = payment.checking_id
        settlement.payment_request = payment.bolt11
        settlement = await update_tab_settlement(settlement)
        return SettlementCreateResponse(
            settlement=settlement, payment_request=payment.bolt11
        )

    settlement = await create_tab_settlement(tab.id, data)
    return SettlementCreateResponse(
        settlement=await complete_settlement(settlement, mark_status_only=False)
    )


async def complete_settlement(
    settlement: TabSettlement, mark_status_only: bool = False
) -> TabSettlement:
    _validate_settlement_status(settlement.status)
    if settlement.status == "completed":
        return settlement
    if settlement.status == "cancelled":
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Cancelled settlements cannot be completed."
        )

    tab = await get_tab_by_id(settlement.tab_id)
    if not tab:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Tab not found.")

    settlement.status = "completed"
    settlement.completed_at = _utc_now()
    settlement = await update_tab_settlement(settlement)

    if mark_status_only:
        return settlement

    entry_idempotency_key = f"settlement:{settlement.id}"
    existing_entry = await get_tab_entry_by_idempotency(tab.id, entry_idempotency_key)
    if existing_entry:
        return settlement

    tab, _ = await post_entry(
        tab,
        CreateTabEntry(
            entry_type="settlement",
            amount=settlement.amount,
            description=settlement.description or f"{settlement.method} settlement",
            metadata=settlement.metadata,
            source="tabs",
            source_id=settlement.id,
            source_action="settlement_completed",
            operator_user_id=settlement.operator_user_id,
            idempotency_key=entry_idempotency_key,
        ),
    )

    if _is_zero(tab.currency, tab.balance) and tab.status != "closed":
        tab.status = "closed"
        tab.balance = 0
        tab.closed_at = _utc_now()
        await update_tab(tab)

    return settlement


async def cancel_settlement(settlement: TabSettlement) -> TabSettlement:
    if settlement.status == "completed":
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, "Completed settlements cannot be cancelled."
        )
    settlement.status = "cancelled"
    settlement.cancelled_at = _utc_now()
    return await update_tab_settlement(settlement)


async def payment_received_for_settlement(payment: Payment) -> bool:
    settlement = None
    extra = payment.extra or {}
    if extra.get("settlement_id"):
        settlement = await get_tab_settlement(extra["settlement_id"])
    if not settlement and payment.payment_hash:
        settlement = await get_tab_settlement_by_payment_hash(payment.payment_hash)
    if not settlement and payment.checking_id:
        settlement = await get_tab_settlement_by_checking_id(payment.checking_id)
    if not settlement:
        return False

    await complete_settlement(settlement)
    return True


async def ensure_tab_exists_for_public_settlement(tab_id: str) -> Tab:
    tab = await get_tab_by_id(tab_id)
    if not tab or tab.is_archived:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Tab not found.")
    return tab
