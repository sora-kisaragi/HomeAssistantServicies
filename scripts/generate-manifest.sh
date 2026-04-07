#!/usr/bin/env bash
# generate-manifest.sh — services/*/manifest.json を1つの JSON に結合する
# 出力: dist/services-manifest.json

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${REPO_DIR}/dist"
OUTPUT_FILE="${OUTPUT_DIR}/services-manifest.json"
DRY_RUN="${1:-}"

MANIFESTS=()
for manifest in "${REPO_DIR}/services"/*/manifest.json; do
    [[ -f "${manifest}" ]] && MANIFESTS+=("${manifest}")
done
# discovery-api manifest も含める
[[ -f "${REPO_DIR}/discovery-api/manifest.json" ]] && MANIFESTS+=("${REPO_DIR}/discovery-api/manifest.json")

# python3 で結合
COMBINED=$(python3 - "${MANIFESTS[@]}" <<'EOF'
import json, sys
from datetime import datetime, timezone

files = sys.argv[1:]
services = []
for f in files:
    try:
        services.append(json.load(open(f)))
    except Exception as e:
        print(f"WARNING: failed to parse {f}: {e}", file=sys.stderr)

result = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "services": services
}
print(json.dumps(result, ensure_ascii=False, indent=2))
EOF
)

if [[ "${DRY_RUN}" == "--dry-run" ]]; then
    echo "Dry run — would write to ${OUTPUT_FILE}"
    echo "${COMBINED}" | python3 -m json.tool > /dev/null
    echo "JSON is valid."
    exit 0
fi

mkdir -p "${OUTPUT_DIR}"
echo "${COMBINED}" > "${OUTPUT_FILE}"
echo "Generated: ${OUTPUT_FILE}"
