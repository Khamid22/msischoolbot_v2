from handlers.start import router as start_router
from handlers.account_link import router as account_link_router
from handlers.quick_summary import router as quick_summary_router
from handlers.contact_us import router as contact_us_router

ALL_ROUTERS = [
    start_router,
    account_link_router,
    quick_summary_router,
    contact_us_router,
]