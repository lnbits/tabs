from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException
from lnbits.core.models import SimpleStatus, User
from lnbits.db import Filters, Page
from lnbits.decorators import check_user_exists, parse_filters
from lnbits.helpers import generate_filter_params_openapi

from .crud import (
    create_tab,
    get_tab_entries,
    get_tab_entries_paginated,
    get_tab_for_wallets,
    get_tab_settlement,
    get_tab_settlements,
    get_tab_settlements_paginated,
    get_tabs,
    get_tabs_paginated,
    update_tab,
)
from .models import (
    CreateTab,
    CreateTabEntry,
    CreateTabSettlement,
    PublicTab,
    PublicTabSettlementRequest,
    SettlementCreateResponse,
    Tab,
    TabEntry,
    TabEntryFilters,
    TabFilters,
    TabSettlement,
    TabSettlementFilters,
    UpdateTab,
    UpdateTabStatus,
)
from .services import (
    archive_tab,
    cancel_settlement,
    complete_settlement,
    create_settlement,
    delete_tab_if_empty,
    ensure_tab_exists_for_public_settlement,
    post_entry,
    update_status,
    validate_tab_payload,
    validate_tab_wallet_ownership,
)

tabs_filters = parse_filters(TabFilters)
tab_entry_filters = parse_filters(TabEntryFilters)
tab_settlement_filters = parse_filters(TabSettlementFilters)

tabs_api_router = APIRouter()


async def _get_owned_tab_or_404(user: User, tab_id: str) -> Tab:
    tab = await get_tab_for_wallets(user.wallet_ids, tab_id)
    if not tab:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Tab not found.")
    return tab


@tabs_api_router.get("/api/v1/tabs", response_model=list[Tab])
async def api_get_tabs(
    include_archived: bool = Query(False),
    user: User = Depends(check_user_exists),
) -> list[Tab]:
    return await get_tabs(user.wallet_ids, include_archived=include_archived)


@tabs_api_router.get(
    "/api/v1/tabs/paginated",
    openapi_extra=generate_filter_params_openapi(TabFilters),
    response_model=Page[Tab],
)
async def api_get_tabs_paginated(
    user: User = Depends(check_user_exists),
    filters: Filters = Depends(tabs_filters),
) -> Page[Tab]:
    return await get_tabs_paginated(user.wallet_ids, filters=filters)


@tabs_api_router.post("/api/v1/tabs", status_code=HTTPStatus.CREATED, response_model=Tab)
async def api_create_tab(
    data: CreateTab,
    user: User = Depends(check_user_exists),
) -> Tab:
    if data.wallet not in user.wallet_ids:
        raise HTTPException(
            HTTPStatus.FORBIDDEN, "Invalid wallet. Must belong to authenticated user."
        )
    await validate_tab_wallet_ownership(user.id, data.wallet)
    tab = Tab(id="pending", status="open", **data.dict())
    validate_tab_payload(tab)
    return await create_tab(data)


@tabs_api_router.get("/api/v1/tabs/{tab_id}", response_model=Tab)
async def api_get_tab(
    tab_id: str,
    user: User = Depends(check_user_exists),
) -> Tab:
    return await _get_owned_tab_or_404(user, tab_id)


@tabs_api_router.put("/api/v1/tabs/{tab_id}", response_model=Tab)
async def api_update_tab(
    tab_id: str,
    data: UpdateTab,
    user: User = Depends(check_user_exists),
) -> Tab:
    tab = await _get_owned_tab_or_404(user, tab_id)
    for field, value in data.dict().items():
        setattr(tab, field, value)
    validate_tab_payload(tab)
    return await update_tab(tab)


@tabs_api_router.post("/api/v1/tabs/{tab_id}/status", response_model=Tab)
async def api_update_tab_status(
    tab_id: str,
    data: UpdateTabStatus,
    user: User = Depends(check_user_exists),
) -> Tab:
    tab = await _get_owned_tab_or_404(user, tab_id)
    return await update_status(tab, data)


@tabs_api_router.post("/api/v1/tabs/{tab_id}/archive", response_model=Tab)
async def api_archive_tab(
    tab_id: str,
    user: User = Depends(check_user_exists),
) -> Tab:
    tab = await _get_owned_tab_or_404(user, tab_id)
    return await archive_tab(tab)


@tabs_api_router.delete("/api/v1/tabs/{tab_id}", response_model=SimpleStatus)
async def api_delete_tab(
    tab_id: str,
    user: User = Depends(check_user_exists),
) -> SimpleStatus:
    tab = await _get_owned_tab_or_404(user, tab_id)
    await delete_tab_if_empty(tab)
    return SimpleStatus(success=True, message="Tab deleted")


@tabs_api_router.get("/api/v1/tabs/{tab_id}/entries", response_model=list[TabEntry])
async def api_get_tab_entries(
    tab_id: str,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(check_user_exists),
) -> list[TabEntry]:
    await _get_owned_tab_or_404(user, tab_id)
    return await get_tab_entries(tab_id, limit=limit)


@tabs_api_router.get(
    "/api/v1/tabs/{tab_id}/entries/paginated",
    openapi_extra=generate_filter_params_openapi(TabEntryFilters),
    response_model=Page[TabEntry],
)
async def api_get_tab_entries_paginated(
    tab_id: str,
    user: User = Depends(check_user_exists),
    filters: Filters = Depends(tab_entry_filters),
) -> Page[TabEntry]:
    await _get_owned_tab_or_404(user, tab_id)
    return await get_tab_entries_paginated(tab_id, filters=filters)


@tabs_api_router.post(
    "/api/v1/tabs/{tab_id}/entries",
    status_code=HTTPStatus.CREATED,
    response_model=TabEntry,
)
async def api_create_tab_entry(
    tab_id: str,
    data: CreateTabEntry,
    user: User = Depends(check_user_exists),
) -> TabEntry:
    tab = await _get_owned_tab_or_404(user, tab_id)
    _, entry = await post_entry(tab, data)
    return entry


@tabs_api_router.get(
    "/api/v1/tabs/{tab_id}/settlements",
    response_model=list[TabSettlement],
)
async def api_get_tab_settlements(
    tab_id: str,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(check_user_exists),
) -> list[TabSettlement]:
    await _get_owned_tab_or_404(user, tab_id)
    return await get_tab_settlements(tab_id, limit=limit)


@tabs_api_router.get(
    "/api/v1/tabs/{tab_id}/settlements/paginated",
    openapi_extra=generate_filter_params_openapi(TabSettlementFilters),
    response_model=Page[TabSettlement],
)
async def api_get_tab_settlements_paginated(
    tab_id: str,
    user: User = Depends(check_user_exists),
    filters: Filters = Depends(tab_settlement_filters),
) -> Page[TabSettlement]:
    await _get_owned_tab_or_404(user, tab_id)
    return await get_tab_settlements_paginated(tab_id, filters=filters)


@tabs_api_router.post(
    "/api/v1/tabs/{tab_id}/settlements",
    status_code=HTTPStatus.CREATED,
    response_model=SettlementCreateResponse,
)
async def api_create_tab_settlement(
    tab_id: str,
    data: CreateTabSettlement,
    user: User = Depends(check_user_exists),
) -> SettlementCreateResponse:
    tab = await _get_owned_tab_or_404(user, tab_id)
    return await create_settlement(tab, data)


@tabs_api_router.get("/api/v1/settlements/{settlement_id}", response_model=TabSettlement)
async def api_get_settlement(
    settlement_id: str,
    user: User = Depends(check_user_exists),
) -> TabSettlement:
    settlement = await get_tab_settlement(settlement_id)
    if not settlement:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Settlement not found.")
    await _get_owned_tab_or_404(user, settlement.tab_id)
    return settlement


@tabs_api_router.post(
    "/api/v1/settlements/{settlement_id}/cancel",
    response_model=TabSettlement,
)
async def api_cancel_settlement(
    settlement_id: str,
    user: User = Depends(check_user_exists),
) -> TabSettlement:
    settlement = await get_tab_settlement(settlement_id)
    if not settlement:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Settlement not found.")
    await _get_owned_tab_or_404(user, settlement.tab_id)
    return await cancel_settlement(settlement)


@tabs_api_router.post(
    "/api/v1/settlements/{settlement_id}/mark-complete",
    response_model=TabSettlement,
)
async def api_mark_settlement_complete(
    settlement_id: str,
    user: User = Depends(check_user_exists),
) -> TabSettlement:
    settlement = await get_tab_settlement(settlement_id)
    if not settlement:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Settlement not found.")
    await _get_owned_tab_or_404(user, settlement.tab_id)
    return await complete_settlement(settlement)


@tabs_api_router.get("/api/v1/public/tabs/{tab_id}", response_model=PublicTab)
async def api_get_public_tab(tab_id: str) -> PublicTab:
    tab = await ensure_tab_exists_for_public_settlement(tab_id)
    return PublicTab(**tab.dict())


@tabs_api_router.post(
    "/api/v1/public/tabs/{tab_id}/settlements",
    status_code=HTTPStatus.CREATED,
    response_model=SettlementCreateResponse,
)
async def api_create_public_tab_settlement(
    tab_id: str,
    data: PublicTabSettlementRequest,
) -> SettlementCreateResponse:
    tab = await ensure_tab_exists_for_public_settlement(tab_id)
    return await create_settlement(
        tab,
        CreateTabSettlement(
            amount=data.amount,
            method="lightning",
            reference=data.reference,
            description="Public settlement",
        ),
    )
