"""Watcher UI — discovery-api のデータを表示・操作する GUI サーバー。"""

import asyncio
import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

DISCOVERY_API_URL = os.getenv("DISCOVERY_API_URL", "http://discovery-api:8765")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

app = FastAPI(title="Watcher UI", description="HomeAssistant サービス管理ダッシュボード")

STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# SSE stream — 5秒ごとに discovery-api のデータを配信
# ---------------------------------------------------------------------------


async def _stream_data():
    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            try:
                services_resp = await client.get(f"{DISCOVERY_API_URL}/api/services")
                gpu_resp = await client.get(f"{DISCOVERY_API_URL}/api/gpu")
                unregistered_resp = await client.get(f"{DISCOVERY_API_URL}/api/unregistered")

                payload = {
                    "services": services_resp.json() if services_resp.is_success else {},
                    "gpu": gpu_resp.json()
                    if gpu_resp.is_success
                    else {"gpus": [], "available": False},
                    "unregistered": unregistered_resp.json()
                    if unregistered_resp.is_success
                    else {"count": 0, "unregistered": []},
                }
            except Exception as e:
                payload = {"error": str(e)}

            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(POLL_INTERVAL)


@app.get("/api/stream")
async def event_stream():
    """SSE エンドポイント — クライアントへリアルタイムデータを配信する。"""
    return StreamingResponse(
        _stream_data(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Proxy endpoints — start/stop/ping を discovery-api に委譲
# ---------------------------------------------------------------------------


@app.post("/api/services/{service_id}/start")
async def start_service(service_id: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{DISCOVERY_API_URL}/api/services/{service_id}/start")
    return resp.json()


@app.post("/api/services/{service_id}/stop")
async def stop_service(service_id: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{DISCOVERY_API_URL}/api/services/{service_id}/stop")
    return resp.json()


@app.post("/api/services/{service_id}/ping")
async def ping_service(service_id: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{DISCOVERY_API_URL}/api/services/{service_id}/ping")
    return resp.json()


# ---------------------------------------------------------------------------
# Static files / SPA
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")
