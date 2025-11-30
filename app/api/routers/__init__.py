from .auth import router as auth_router
from .locations import router as locations_router
from .rooms import router as rooms_router

__all__ = [
    auth_router,
    locations_router,
    rooms_router,
]
