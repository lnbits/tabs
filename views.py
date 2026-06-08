from fastapi import APIRouter, Depends
from lnbits.core.views.generic import index, index_public
from lnbits.decorators import check_account_exists
from lnbits.helpers import template_renderer

tabs_generic_router = APIRouter()


def tabs_renderer():
    return template_renderer(["tabs/templates"])


tabs_generic_router.add_api_route("/", methods=["GET"], endpoint=index, dependencies=[Depends(check_account_exists)])
tabs_generic_router.add_api_route("/{tabs_id}", methods=["GET"], endpoint=index_public)
