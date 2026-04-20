import asyncio

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .services import payment_received_for_settlement

#######################################
########## RUN YOUR TASKS HERE ########
#######################################

# Listen to invoices related to this extension.


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_tabs")
    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


# Handle invoices paid for this extension.


async def on_invoice_paid(payment: Payment) -> None:
    extra = payment.extra or {}
    if extra.get("tag") != "tabs":
        return

    logger.info(f"Invoice paid for tabs: {payment.payment_hash}")

    try:
        await payment_received_for_settlement(payment)
    except Exception:
        logger.exception("Error processing payment for tabs.")
