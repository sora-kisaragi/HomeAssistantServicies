#!/usr/bin/env bash
# health-check.sh — 全サービスのヘルスエンドポイントを確認する
# 終了コード: 0=全て正常, 1=1件以上NG

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILED=0
PASSED=0
SKIPPED=0

check_service() {
    local svc_dir="$1"
    local svc_name
    svc_name="$(basename "${svc_dir}")"
    local manifest="${svc_dir}/manifest.json"

    if [[ ! -f "${manifest}" ]]; then
        return
    fi

    local port health_path expected_status
    port=$(python3 -c "import json,sys; d=json.load(open('${manifest}')); print(d.get('port',''))" 2>/dev/null || true)
    health_path=$(python3 -c "import json,sys; d=json.load(open('${manifest}')); print(d.get('health_check',{}).get('path',''))" 2>/dev/null || true)
    expected_status=$(python3 -c "import json,sys; d=json.load(open('${manifest}')); print(d.get('health_check',{}).get('expected_status',200))" 2>/dev/null || echo "200")

    if [[ -z "${port}" || -z "${health_path}" ]]; then
        echo "  [SKIP] ${svc_name}: no health_check configured"
        ((SKIPPED++)) || true
        return
    fi

    local url="http://localhost:${port}${health_path}"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${url}" 2>/dev/null || echo "000")

    if [[ "${http_code}" == "${expected_status}" ]]; then
        echo "  [OK]   ${svc_name}: ${url} => ${http_code}"
        ((PASSED++)) || true
    else
        echo "  [FAIL] ${svc_name}: ${url} => ${http_code} (expected ${expected_status})"
        ((FAILED++)) || true
    fi
}

echo "=== Health Check ==="

# services/* を確認
for svc_dir in "${REPO_DIR}/services"/*/; do
    check_service "${svc_dir}"
done

# discovery-api を確認
check_service "${REPO_DIR}/discovery-api"

echo ""
echo "Results: ${PASSED} passed, ${FAILED} failed, ${SKIPPED} skipped"

if [[ ${FAILED} -gt 0 ]]; then
    exit 1
fi
exit 0
