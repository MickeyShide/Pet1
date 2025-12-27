from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.api import routers
from app.db.base import init_engine, dispose_engine
from app.config import settings
from app.utils.redis import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine(echo=settings.SQL_ECHO)
    await init_redis(app)
    try:
        yield
    finally:
        await close_redis(app)
        await dispose_engine()


def add_debug_routes(app: FastAPI) -> None:
    app.get("/debug/ip")(debug_ip)


def create_app() -> FastAPI:
    app = FastAPI(title="Pet 1", lifespan=lifespan)
    for r in routers.__all__:
        app.include_router(r)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://itouch-pet-project.ru.tuna.am"],
        allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
        "main:app",
        host="0.0.0.0",
        port=4000,
    )
