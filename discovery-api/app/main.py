import asyncio
import json
import os
import socket
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import docker
import httpx
import pynvml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

MANIFESTS_DIR = Path(os.getenv("MANIFESTS_DIR", "/manifests"))
LABEL_PREFIX = "homeassistant"
IDLE_CHECK_INTERVAL = 30  # seconds

docker_client: docker.DockerClient | None = None

# on-demand コンテナの最終アクセス時刻 {service_id: float}
last_access: dict[str, float] = {}


# ---------------------------------------------------------------------------
# Lifespan — start idle monitor on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_idle_monitor_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HomeAssistant Service Discovery API",
    description="稼働中のコンテナサービスの一覧・ポート・ヘルス状態を返す API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------


def get_docker_client() -> docker.DockerClient | None:
    global docker_client
    if docker_client is None:
        try:
            docker_client = docker.from_env()
        except Exception:
            return None
    return docker_client


def _find_container(service_id: str):
    """service_id に一致するコンテナを返す（名前 or homeassistant.name ラベルで検索）。"""
    client = get_docker_client()
    if client is None:
        return None
    try:
        # ラベルで検索
        for c in client.containers.list(
            all=True, filters={"label": f"{LABEL_PREFIX}.name={service_id}"}
        ):
            return c
        # コンテナ名で検索
        return client.containers.get(service_id)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------


def load_manifests() -> dict[str, dict]:
    """services/*/manifest.json を読み込んで id をキーとした辞書を返す。"""
    manifests: dict[str, dict] = {}
    if not MANIFESTS_DIR.exists():
        return manifests
    for manifest_path in MANIFESTS_DIR.glob("**/manifest.json"):
        try:
            data = json.loads(manifest_path.read_text())
            if "id" in data:
                manifests[data["id"]] = data
        except Exception:
            pass
    return manifests


# ---------------------------------------------------------------------------
# Container listing
# ---------------------------------------------------------------------------


def get_running_containers() -> dict[str, dict]:
    """homeassistant.service=true ラベルを持つコンテナを返す。"""
    client = get_docker_client()
    if client is None:
        return {}

    containers: dict[str, dict] = {}
    try:
        for container in client.containers.list(filters={"label": f"{LABEL_PREFIX}.service=true"}):
            labels = container.labels
            service_id = labels.get(f"{LABEL_PREFIX}.name", container.name)
            started_at = None
            try:
                started_at = container.attrs.get("State", {}).get("StartedAt")
            except Exception:
                pass

            uptime_seconds = None
            if started_at:
                try:
                    start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    uptime_seconds = int((datetime.now(UTC) - start_dt).total_seconds())
                except Exception:
                    pass

            containers[service_id] = {
                "id": container.short_id,
                "name": container.name,
                "image": (
                    container.image.tags[0] if container.image.tags else container.image.short_id
                ),
                "status": container.status,
                "started_at": started_at,
                "uptime_seconds": uptime_seconds,
                "labels": labels,
            }
    except Exception:
        pass
    return containers


# ---------------------------------------------------------------------------
# Health probe
# ---------------------------------------------------------------------------


async def probe_health(
    service_id: str, port: int, health_path: str, expected_status: int = 200
) -> dict:
    url = f"http://{service_id}:{port}{health_path}"
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            status = "healthy" if resp.status_code == expected_status else "unhealthy"
            return {
                "status": status,
                "last_checked": datetime.now(UTC).isoformat(),
                "response_time_ms": elapsed_ms,
            }
    except Exception:
        return {
            "status": "unreachable",
            "last_checked": datetime.now(UTC).isoformat(),
            "response_time_ms": None,
        }


# ---------------------------------------------------------------------------
# Service entry builder
# ---------------------------------------------------------------------------


def build_service_entry(service_id: str, manifest: dict, container: dict | None) -> dict:
    entry = {
        "id": service_id,
        "display_name": manifest.get("display_name", service_id),
        "description": manifest.get("description", ""),
        "category": manifest.get("category", "other"),
        "port": manifest.get("port"),
        "tags": manifest.get("tags", []),
        "docs_url": manifest.get("docs_url"),
        "icon": manifest.get("icon"),
        "on_demand": manifest.get("on_demand", False),
        "gpu_required": manifest.get("gpu_required", False),
        "idle_timeout_seconds": manifest.get("idle_timeout_seconds"),
    }

    if container:
        entry["status"] = "running" if container["status"] == "running" else container["status"]
        entry["uptime_seconds"] = container.get("uptime_seconds")
        entry["container"] = {
            "id": container["id"],
            "image": container["image"],
            "started_at": container.get("started_at"),
        }
    else:
        entry["status"] = "stopped"
        entry["uptime_seconds"] = None
        entry["container"] = None

    return entry


# ---------------------------------------------------------------------------
# Idle monitor
# ---------------------------------------------------------------------------


async def _idle_monitor_loop() -> None:
    """30秒ごとに on-demand コンテナのアイドル時間をチェックし、タイムアウトで停止する。"""
    # 起動直後は猶予を与える（既に稼働中のコンテナを即停止しない）
    await asyncio.sleep(IDLE_CHECK_INTERVAL)

    while True:
        client = get_docker_client()
        if client is not None:
            now = time.time()
            try:
                for container in client.containers.list(
                    filters={"label": f"{LABEL_PREFIX}.on-demand=true"}
                ):
                    sid = container.labels.get(f"{LABEL_PREFIX}.name", container.name)
                    timeout = int(container.labels.get(f"{LABEL_PREFIX}.idle-timeout", "3600"))
                    if sid not in last_access:
                        # 初回検知: タイマー開始（即停止しない）
                        last_access[sid] = now
                    elif now - last_access[sid] > timeout:
                        try:
                            container.stop(timeout=10)
                            last_access.pop(sid, None)
                        except Exception:
                            pass
            except Exception:
                pass

        await asyncio.sleep(IDLE_CHECK_INTERVAL)


# ---------------------------------------------------------------------------
# GPU stats helper
# ---------------------------------------------------------------------------


def _get_gpu_stats() -> list[dict]:
    """pynvml で GPU 情報を取得する。利用不可の場合は空リストを返す。
    GB10 (Grace-Hopper) など統合メモリ GPU も安全に扱う。
    """
    try:
        pynvml.nvmlInit()
    except pynvml.NVMLError:
        return []

    gpus = []
    try:
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode()

            # 使用率
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                utilization_percent: int | None = util.gpu
            except pynvml.NVMLError:
                utilization_percent = None

            # メモリ（GB10 等の統合メモリ GPU は NVML_ERROR_NOT_SUPPORTED）
            unified_memory = False
            memory_used_mb: int | None = None
            memory_total_mb: int | None = None
            try:
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                memory_used_mb = mem.used // (1024 * 1024)
                memory_total_mb = mem.total // (1024 * 1024)
            except pynvml.NVMLError:
                unified_memory = True

            # 温度
            try:
                temperature_c: int | None = pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                )
            except pynvml.NVMLError:
                temperature_c = None

            gpus.append(
                {
                    "index": i,
                    "name": name,
                    "utilization_percent": utilization_percent,
                    "memory_used_mb": memory_used_mb,
                    "memory_total_mb": memory_total_mb,
                    "temperature_c": temperature_c,
                    "unified_memory": unified_memory,
                }
            )
    except pynvml.NVMLError:
        pass
    finally:
        try:
            pynvml.nvmlShutdown()
        except pynvml.NVMLError:
            pass

    return gpus


# ===========================================================================
# Endpoints — read
# ===========================================================================


@app.get("/api/health")
async def api_health():
    """API 自身の死活確認。"""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/api/services")
async def list_services():
    """全サービスの一覧（稼働状態・ポート・ヘルス含む）。"""
    manifests = load_manifests()
    containers = get_running_containers()

    all_ids = set(manifests.keys()) | set(containers.keys())

    services = []
    for service_id in sorted(all_ids):
        manifest = manifests.get(service_id, {"id": service_id, "display_name": service_id})
        container = containers.get(service_id)
        entry = build_service_entry(service_id, manifest, container)

        health_check = manifest.get("health_check")
        if container and container["status"] == "running" and health_check:
            entry["health"] = await probe_health(
                service_id,
                manifest.get("port", 80),
                health_check.get("path", "/"),
                health_check.get("expected_status", 200),
            )
        elif container and container["status"] == "running":
            entry["health"] = {
                "status": "unknown",
                "last_checked": None,
                "response_time_ms": None,
            }
        else:
            entry["health"] = {
                "status": "unreachable",
                "last_checked": None,
                "response_time_ms": None,
            }

        # アイドル情報を付加
        if manifest.get("on_demand") and service_id in last_access:
            timeout = manifest.get("idle_timeout_seconds", 3600)
            elapsed = time.time() - last_access[service_id]
            entry["idle_remaining_seconds"] = max(0, int(timeout - elapsed))
        else:
            entry["idle_remaining_seconds"] = None

        services.append(entry)

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "host": socket.gethostname(),
        "services": services,
    }


@app.get("/api/services/{service_id}")
async def get_service(service_id: str):
    """単体サービスの詳細。"""
    manifests = load_manifests()
    containers = get_running_containers()

    manifest = manifests.get(service_id)
    container = containers.get(service_id)

    if manifest is None and container is None:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

    if manifest is None:
        manifest = {"id": service_id, "display_name": service_id}

    entry = build_service_entry(service_id, manifest, container)

    health_check = manifest.get("health_check")
    if container and container["status"] == "running" and health_check:
        entry["health"] = await probe_health(
            service_id,
            manifest.get("port", 80),
            health_check.get("path", "/"),
            health_check.get("expected_status", 200),
        )
    elif container and container["status"] == "running":
        entry["health"] = {"status": "unknown", "last_checked": None, "response_time_ms": None}
    else:
        entry["health"] = {
            "status": "unreachable",
            "last_checked": None,
            "response_time_ms": None,
        }

    if manifest.get("on_demand") and service_id in last_access:
        timeout = manifest.get("idle_timeout_seconds", 3600)
        elapsed = time.time() - last_access[service_id]
        entry["idle_remaining_seconds"] = max(0, int(timeout - elapsed))
    else:
        entry["idle_remaining_seconds"] = None

    return entry


@app.get("/api/services/{service_id}/health")
async def get_service_health(service_id: str):
    """単体サービスのヘルスを強制プローブ。"""
    manifests = load_manifests()
    manifest = manifests.get(service_id)
    if manifest is None:
        raise HTTPException(
            status_code=404, detail=f"Service '{service_id}' not found in manifests"
        )

    health_check = manifest.get("health_check")
    if not health_check:
        raise HTTPException(
            status_code=422, detail=f"Service '{service_id}' has no health_check configured"
        )

    result = await probe_health(
        service_id,
        manifest.get("port", 80),
        health_check.get("path", "/"),
        health_check.get("expected_status", 200),
    )
    return {"service_id": service_id, **result}


@app.get("/api/services/{service_id}/stats")
async def get_service_stats(service_id: str):
    """コンテナの CPU・メモリ使用率を返す（docker stats API）。"""
    container = _find_container(service_id)
    if container is None:
        raise HTTPException(status_code=404, detail=f"Container '{service_id}' not found")
    if container.status != "running":
        raise HTTPException(status_code=409, detail=f"Container '{service_id}' is not running")

    try:
        raw = container.stats(stream=False)
        cpu_delta = (
            raw["cpu_stats"]["cpu_usage"]["total_usage"]
            - raw["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            raw["cpu_stats"]["system_cpu_usage"] - raw["precpu_stats"]["system_cpu_usage"]
        )
        num_cpus = raw["cpu_stats"].get("online_cpus") or len(
            raw["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])
        )
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0 if system_delta > 0 else 0.0

        mem = raw["memory_stats"]
        mem_usage = mem.get("usage", 0)
        mem_limit = mem.get("limit", 1)
        mem_percent = (mem_usage / mem_limit) * 100.0

        return {
            "service_id": service_id,
            "cpu_percent": round(cpu_percent, 2),
            "memory_usage_bytes": mem_usage,
            "memory_limit_bytes": mem_limit,
            "memory_percent": round(mem_percent, 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/gpu")
async def get_gpu_stats():
    """ホストの GPU 使用率・メモリを nvidia-smi 経由で返す。"""
    gpus = _get_gpu_stats()
    return {"gpus": gpus, "available": len(gpus) > 0}


@app.get("/api/unregistered")
async def list_unregistered():
    """homeassistant ラベルも manifest にも登録されていないコンテナを列挙する。"""
    client = get_docker_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Docker client unavailable")

    manifests = load_manifests()
    registered_ids = set(manifests.keys())

    unregistered = []
    try:
        for container in client.containers.list():
            has_label = container.labels.get(f"{LABEL_PREFIX}.service") == "true"
            service_name = container.labels.get(f"{LABEL_PREFIX}.name", container.name)
            if not has_label and service_name not in registered_ids:
                ports = {}
                try:
                    ports = container.ports or {}
                except Exception:
                    pass
                unregistered.append(
                    {
                        "name": container.name,
                        "image": (
                            container.image.tags[0]
                            if container.image.tags
                            else container.image.short_id
                        ),
                        "status": container.status,
                        "ports": ports,
                        "hint": (f"make add-service NAME={container.name} PORT=<port>"),
                    }
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "count": len(unregistered),
        "unregistered": unregistered,
    }


# ===========================================================================
# Endpoints — control (on-demand)
# ===========================================================================


@app.post("/api/services/{service_id}/start", status_code=202)
async def start_service(service_id: str):
    """on-demand コンテナを起動する。202 を返しクライアントは status をポーリングする。"""
    container = _find_container(service_id)
    if container is None:
        raise HTTPException(status_code=404, detail=f"Container '{service_id}' not found")

    if container.status == "running":
        last_access[service_id] = time.time()
        return {"status": "already_running", "service_id": service_id}

    try:
        container.start()
        last_access[service_id] = time.time()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "status": "starting",
        "service_id": service_id,
        "poll_url": f"/api/services/{service_id}",
    }


@app.post("/api/services/{service_id}/stop", status_code=202)
async def stop_service(service_id: str):
    """コンテナを停止する。"""
    container = _find_container(service_id)
    if container is None:
        raise HTTPException(status_code=404, detail=f"Container '{service_id}' not found")

    if container.status != "running":
        return {"status": "already_stopped", "service_id": service_id}

    try:
        container.stop(timeout=10)
        last_access.pop(service_id, None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "stopped", "service_id": service_id}


@app.post("/api/services/{service_id}/ping")
async def ping_service(service_id: str):
    """アイドルタイマーをリセットする（アクセスがあったことを通知）。"""
    last_access[service_id] = time.time()
    return {"status": "ok", "service_id": service_id, "timestamp": datetime.now(UTC).isoformat()}


@app.get("/api/services/{service_id}/idle-status")
async def get_idle_status(service_id: str):
    """on-demand サービスのアイドル残り時間を返す。"""
    manifests = load_manifests()
    manifest = manifests.get(service_id, {})

    if not manifest.get("on_demand"):
        return {"service_id": service_id, "on_demand": False, "idle_remaining_seconds": None}

    timeout = manifest.get("idle_timeout_seconds", 3600)
    accessed_at = last_access.get(service_id)
    if accessed_at is None:
        remaining = None
    else:
        remaining = max(0, int(timeout - (time.time() - accessed_at)))

    return {
        "service_id": service_id,
        "on_demand": True,
        "idle_timeout_seconds": timeout,
        "last_access": datetime.fromtimestamp(accessed_at, tz=UTC).isoformat()
        if accessed_at
        else None,
        "idle_remaining_seconds": remaining,
    }
