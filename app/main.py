from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.api import routers
from app.config import settings
from app.db.base import init_engine, dispose_engine
from app.graceful_shutdown import get_graceful_shutdown_state, install_graceful_shutdown
from app.observability import RequestObservabilityMiddleware, setup_logging
from app.utils.redis import init_redis, close_redis

setup_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    shutdown_state = get_graceful_shutdown_state(app)
    logger.info("application_startup_begin", extra={"event": "application_startup_begin"})
    init_engine(echo=settings.SQL_ECHO)
    await init_redis(app)
    logger.info("application_startup_ready", extra={"event": "application_startup_ready"})
    try:
        yield
    finally:
        logger.info("application_shutdown_begin", extra={"event": "application_shutdown_begin"})
        shutdown_state.begin_draining("lifespan_shutdown")
        await shutdown_state.wait_for_active_requests(settings.API_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS)
        await close_redis(app)
        await dispose_engine()
        logger.info("application_shutdown_complete", extra={"event": "application_shutdown_complete"})


def add_debug_routes(app: FastAPI) -> None:
    app.get("/debug/ip")(debug_ip)


def create_app() -> FastAPI:
    app = FastAPI(title="Pet 1", lifespan=lifespan)
    install_graceful_shutdown(app, retry_after_seconds=settings.API_SHUTDOWN_RETRY_AFTER_SECONDS)
    for r in routers.__all__:
        app.include_router(r)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://itouch.pw", "https://itouch-pet-project.ru.tuna.am", "https://booking.itouch.pw"],
        allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(RequestObservabilityMiddleware)

    if settings.DEBUG:
        add_debug_routes(app)

    return app


def get_real_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # цепочка: "1.2.3.4, 5.6.7.8"
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


async def debug_ip(request: Request) -> dict[str, str | None]:
    return {
        "X-Real-IP": request.headers.get("X-Real-IP"),
        "X-Forwarded-For": request.headers.get("X-Forwarded-For"),
        "client": request.client.host if request.client else None,
        "real_ip": get_real_ip(request),
    }


app: FastAPI = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=4000,
        timeout_graceful_shutdown=settings.API_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
    )
