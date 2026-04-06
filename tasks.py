import asyncio

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .services import payment_received_for_settlement

#######################################
########## RUN YOUR TASKS HERE ########
#######################################

# The usual task is to listen to invoices related to this extension


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_tabs")
    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


# Do somethhing when an invoice related top this extension is paid


async def on_invoice_paid(payment: Payment) -> None:
    extra = payment.extra or {}
    if extra.get("tag") != "tabs":
        return

    logger.info(f"Invoice paid for tabs: {payment.payment_hash}")

    try:
        await payment_received_for_settlement(payment)
    except Exception as e:
        logger.error(f"Error processing payment for tabs: {e}")
