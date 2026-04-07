import json
import os
import socket
import time
from datetime import UTC, datetime
from pathlib import Path

import docker
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="HomeAssistant Service Discovery API",
    description="稼働中のコンテナサービスの一覧・ポート・ヘルス状態を返す API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

MANIFESTS_DIR = Path(os.getenv("MANIFESTS_DIR", "/manifests"))
LABEL_PREFIX = "homeassistant"
docker_client: docker.DockerClient | None = None


def get_docker_client() -> docker.DockerClient | None:
    global docker_client
    if docker_client is None:
        try:
            docker_client = docker.from_env()
        except Exception:
            return None
    return docker_client


def load_manifests() -> dict[str, dict]:
    """services/*/manifest.json を読み込んで id をキーとした辞書を返す"""
    manifests = {}
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


def get_running_containers() -> dict[str, dict]:
    """homeassistant.service=true ラベルを持つコンテナを返す"""
    client = get_docker_client()
    if client is None:
        return {}

    containers = {}
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
                "image": container.image.tags[0]
                if container.image.tags
                else container.image.short_id,
                "status": container.status,
                "started_at": started_at,
                "uptime_seconds": uptime_seconds,
                "labels": labels,
            }
    except Exception:
        pass
    return containers


async def probe_health(
    service_id: str, port: int, health_path: str, expected_status: int = 200
) -> dict:
    """サービスのヘルスエンドポイントを実際にプローブする"""
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


@app.get("/api/health")
async def api_health():
    """API自身の死活確認"""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/api/services")
async def list_services():
    """全サービスの一覧（稼働状態・ポート・ヘルス含む）"""
    manifests = load_manifests()
    containers = get_running_containers()

    # manifest に登録されているサービス + コンテナのみ稼働中のサービスをマージ
    all_ids = set(manifests.keys()) | set(containers.keys())

    services = []
    for service_id in sorted(all_ids):
        manifest = manifests.get(service_id, {"id": service_id, "display_name": service_id})
        container = containers.get(service_id)
        entry = build_service_entry(service_id, manifest, container)

        # ヘルスチェック（コンテナが稼働中 かつ manifest に health_check があれば）
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

        services.append(entry)

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "host": socket.gethostname(),
        "services": services,
    }


@app.get("/api/services/{service_id}")
async def get_service(service_id: str):
    """単体サービスの詳細"""
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
        entry["health"] = {"status": "unreachable", "last_checked": None, "response_time_ms": None}

    return entry


@app.get("/api/services/{service_id}/health")
async def get_service_health(service_id: str):
    """単体サービスのヘルスを強制プローブ"""
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
