from tgbot.handlers.start import router as start_router
from tgbot.handlers.account_link import router as account_link_router
from tgbot.handlers.quick_summary import router as quick_summary_router
from tgbot.handlers.contact_us import router as contact_us_router

ALL_ROUTERS = [
    start_router,
    account_link_router,
    quick_summary_router,
    contact_us_router,
]