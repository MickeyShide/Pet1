import runpy
import sys
import types

import pytest
from fastapi import FastAPI
from starlette.requests import Request

import app.main as main


def test_get_real_ip_prefers_forwarded_for():
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"10.0.0.1, 10.0.0.2")],
            "client": ("127.0.0.1", 0),
        }
    )
    assert main.get_real_ip(request) == "10.0.0.1"


def test_get_real_ip_falls_back_to_real_ip():
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-real-ip", b"192.168.0.5")],
            "client": ("127.0.0.1", 0),
        }
    )
    assert main.get_real_ip(request) == "192.168.0.5"


def test_get_real_ip_uses_client_as_last_resort():
    request = Request({"type": "http", "headers": [], "client": ("8.8.8.8", 0)})
    assert main.get_real_ip(request) == "8.8.8.8"


@pytest.mark.asyncio
async def test_lifespan_calls_init_and_cleanup(monkeypatch):
    calls: list[str] = []

    def fake_init_engine(echo: bool = False):
        calls.append(f"init_engine:{echo}")

    async def fake_init_redis(app: FastAPI):
        calls.append("init_redis")

    async def fake_close_redis(app: FastAPI):
        calls.append("close_redis")

    async def fake_dispose():
        calls.append("dispose_engine")

    monkeypatch.setattr(main, "init_engine", fake_init_engine)
    monkeypatch.setattr(main, "init_redis", fake_init_redis)
    monkeypatch.setattr(main, "close_redis", fake_close_redis)
    monkeypatch.setattr(main, "dispose_engine", fake_dispose)

    app = FastAPI(lifespan=main.lifespan)
    async with main.lifespan(app):
        assert f"init_engine:{main.settings.SQL_ECHO}" in calls
        assert "init_redis" in calls

    assert "close_redis" in calls
    assert "dispose_engine" in calls


@pytest.mark.asyncio
async def test_debug_ip_endpoint_returns_all_ips():
    request = Request(
        {
            "type": "http",
            "headers": [
                (b"x-real-ip", b"5.5.5.5"),
                (b"x-forwarded-for", b"9.9.9.9, 10.0.0.1"),
            ],
            "client": ("1.1.1.1", 0),
        }
    )

    payload = await main.debug_ip(request)

    assert payload["X-Real-IP"] == "5.5.5.5"
    assert payload["X-Forwarded-For"].startswith("9.9.9.9")
    assert payload["real_ip"] == "9.9.9.9"


def test_main_dunder_main_runs_uvicorn(monkeypatch):
    called: dict[str, object] = {}

    def fake_run(app: str, host: str, port: int):
        called["app"] = app
        called["host"] = host
        called["port"] = port

    fake_uvicorn = types.SimpleNamespace(run=fake_run)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    runpy.run_module("app.main", run_name="__main__")

    assert called["app"] == "main:app"
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 4000
