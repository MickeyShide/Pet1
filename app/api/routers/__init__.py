from .auth import router as auth_router
from .bookings import router as bookings_router
from .features import router as features_router
from .images import router as images_router
from .locations import router as locations_router
from .payments import router as payments_router
from .rooms import router as rooms_router
from .timeslots import router as timeslots_router

__all__ = [
    auth_router,
    features_router,
    images_router,
    locations_router,
    rooms_router,
    timeslots_router,
    bookings_router,
    payments_router
]
