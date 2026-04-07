#!/usr/bin/env bash
# deploy.sh — サーバー上で実行されるマスターデプロイスクリプト
# self-hosted GitHub Actions runner または手動で実行する
# 冪等性あり（何度実行しても安全）

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/var/log/homeassistant"
LOG_FILE="${LOG_DIR}/deploy.log"
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S%z')

# ログディレクトリを確保
mkdir -p "${LOG_DIR}"

log() {
    echo "[${TIMESTAMP}] $*" | tee -a "${LOG_FILE}"
}

log "=== Deploy started ==="
log "Repo: ${REPO_DIR}"
log "User: $(whoami)"

# 1. git pull
log "Pulling latest from origin/main..."
git -C "${REPO_DIR}" pull origin main

# 2. 前回デプロイから変更されたサービスを検出
CHANGED_SERVICES=()
while IFS= read -r changed_file; do
    # services/<name>/... の形式からサービス名を抽出
    if [[ "${changed_file}" =~ ^services/([^/]+)/ ]]; then
        svc="${BASH_REMATCH[1]}"
        # 重複を除外
        if [[ " ${CHANGED_SERVICES[*]} " != *" ${svc} "* ]]; then
            CHANGED_SERVICES+=("${svc}")
        fi
    fi
done < <(git -C "${REPO_DIR}" diff HEAD~1 HEAD --name-only 2>/dev/null || git -C "${REPO_DIR}" diff --name-only HEAD 2>/dev/null || true)

log "Changed services: ${CHANGED_SERVICES[*]:-none}"

# 3. 変更されたサービスを pull + 再起動
for svc in "${CHANGED_SERVICES[@]}"; do
    compose_file="${REPO_DIR}/services/${svc}/docker-compose.yml"
    if [[ ! -f "${compose_file}" ]]; then
        log "WARNING: ${compose_file} not found, skipping ${svc}"
        continue
    fi

    log "Deploying service: ${svc}"
    docker compose -f "${compose_file}" pull --quiet
    docker compose -f "${compose_file}" up -d --remove-orphans
    log "Service ${svc}: deployed"
done

# 4. discovery-api は常に再起動（manifest 変更を反映させるため）
DISCOVERY_COMPOSE="${REPO_DIR}/discovery-api/docker-compose.yml"
if [[ -f "${DISCOVERY_COMPOSE}" ]]; then
    log "Restarting discovery-api..."
    docker compose -f "${DISCOVERY_COMPOSE}" build --quiet
    docker compose -f "${DISCOVERY_COMPOSE}" up -d --remove-orphans
    log "discovery-api: restarted"
fi

# 5. ヘルスチェック
log "Running health checks..."
if bash "${REPO_DIR}/scripts/health-check.sh"; then
    log "Health checks: PASSED"
else
    log "Health checks: FAILED (some services may be unhealthy)"
    exit 1
fi

log "=== Deploy finished ==="
