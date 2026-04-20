import asyncio

from fastapi import APIRouter
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import tabs_generic_router
from .views_api import tabs_api_router

tabs_ext: APIRouter = APIRouter(prefix="/tabs", tags=["Tabs"])
tabs_ext.include_router(tabs_generic_router)
tabs_ext.include_router(tabs_api_router)


tabs_static_files = [
    {
        "path": "/tabs/static",
        "name": "tabs_static",
    }
]

scheduled_tasks: list[asyncio.Task] = []


def tabs_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def tabs_start():
    task = create_permanent_unique_task("ext_tabs", wait_for_paid_invoices)
    scheduled_tasks.append(task)


__all__ = [
    "db",
    "tabs_ext",
    "tabs_start",
    "tabs_static_files",
    "tabs_stop",
]
