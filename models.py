from datetime import datetime, timezone

from lnbits.db import FilterModel
from pydantic import BaseModel, Field


TAB_STATUSES = ("open", "suspended", "closed")
TAB_LIMIT_TYPES = ("none", "hard")
TAB_ENTRY_TYPES = ("charge", "credit", "adjustment", "settlement", "note")
SETTLEMENT_METHODS = (
    "lightning",
    "cash",
    "card",
    "bank_transfer",
    "other",
    "writeoff",
)
SETTLEMENT_STATUSES = ("pending", "completed", "failed", "cancelled")


class CreateTab(BaseModel):
    wallet: str
    name: str
    customer_name: str | None = None
    reference: str | None = None
    currency: str = "sats"
    limit_type: str = "none"
    limit_amount: float | None = None


class UpdateTab(BaseModel):
    name: str
    customer_name: str | None = None
    reference: str | None = None
    currency: str = "sats"
    limit_type: str = "none"
    limit_amount: float | None = None


class UpdateTabStatus(BaseModel):
    status: str


class Tab(BaseModel):
    id: str
    wallet: str
    name: str
    customer_name: str | None = None
    reference: str | None = None
    currency: str = "sats"
    status: str = "open"
    limit_type: str = "none"
    limit_amount: float | None = None
    balance: float = 0
    is_archived: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None
    archived_at: datetime | None = None


class PublicTab(BaseModel):
    id: str
    name: str
    customer_name: str | None = None
    currency: str = "sats"
    status: str = "open"
    balance: float = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TabFilters(FilterModel):
    __search_fields__ = [  # noqa: RUF012
        "name",
        "reference",
        "customer_name",
        "currency",
        "status",
    ]

    __sort_fields__ = [  # noqa: RUF012
        "name",
        "currency",
        "status",
        "balance",
        "created_at",
        "updated_at",
    ]

    status: str | None = None
    currency: str | None = None
    is_archived: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CreateTabEntry(BaseModel):
    entry_type: str
    amount: float | None = None
    description: str | None = None
    unit_label: str | None = None
    quantity: float | None = None
    metadata: str | None = None
    source: str | None = None
    source_id: str | None = None
    source_action: str | None = None
    operator_user_id: str | None = None
    idempotency_key: str | None = None


class TabEntry(BaseModel):
    id: str
    tab_id: str
    entry_type: str
    amount: float = 0
    description: str | None = None
    unit_label: str | None = None
    quantity: float | None = None
    metadata: str | None = None
    source: str | None = None
    source_id: str | None = None
    source_action: str | None = None
    operator_user_id: str | None = None
    idempotency_key: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TabEntryFilters(FilterModel):
    __search_fields__ = [  # noqa: RUF012
        "entry_type",
        "description",
        "source",
        "source_id",
        "source_action",
        "operator_user_id",
        "idempotency_key",
    ]

    __sort_fields__ = [  # noqa: RUF012
        "entry_type",
        "amount",
        "created_at",
    ]

    entry_type: str | None = None
    source: str | None = None
    created_at: datetime | None = None


class CreateTabSettlement(BaseModel):
    amount: float | None = None
    method: str = "lightning"
    reference: str | None = None
    description: str | None = None
    metadata: str | None = None
    operator_user_id: str | None = None
    idempotency_key: str | None = None


class PublicTabSettlementRequest(BaseModel):
    amount: float | None = None
    reference: str | None = None


class TabSettlement(BaseModel):
    id: str
    tab_id: str
    amount: float
    method: str
    status: str = "pending"
    payment_hash: str | None = None
    checking_id: str | None = None
    payment_request: str | None = None
    reference: str | None = None
    description: str | None = None
    metadata: str | None = None
    operator_user_id: str | None = None
    idempotency_key: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None


class SettlementCreateResponse(BaseModel):
    settlement: TabSettlement
    payment_request: str | None = None


class TabSettlementFilters(FilterModel):
    __search_fields__ = [  # noqa: RUF012
        "method",
        "status",
        "payment_hash",
        "checking_id",
        "reference",
        "operator_user_id",
        "idempotency_key",
    ]

    __sort_fields__ = [  # noqa: RUF012
        "method",
        "status",
        "amount",
        "created_at",
        "updated_at",
    ]

    method: str | None = None
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
