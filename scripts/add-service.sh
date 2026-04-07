#!/usr/bin/env bash
# add-service.sh — 新サービスのディレクトリをテンプレートから生成する
#
# 使用例:
#   ./scripts/add-service.sh NAME=myservice PORT=8090
#   make add-service NAME=myservice PORT=8090

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 引数解析 (NAME=xxx PORT=xxx 形式 または 位置引数)
NAME=""
PORT=""
for arg in "$@"; do
    case "${arg}" in
        NAME=*) NAME="${arg#NAME=}" ;;
        PORT=*) PORT="${arg#PORT=}" ;;
        *) echo "Unknown argument: ${arg}"; exit 1 ;;
    esac
done

if [[ -z "${NAME}" || -z "${PORT}" ]]; then
    echo "Usage: $0 NAME=<service-name> PORT=<port>"
    echo "Example: $0 NAME=myservice PORT=8090"
    exit 1
fi

TARGET_DIR="${REPO_DIR}/services/${NAME}"

if [[ -d "${TARGET_DIR}" ]]; then
    echo "ERROR: ${TARGET_DIR} already exists"
    exit 1
fi

echo "Creating service scaffold: ${NAME} (port ${PORT})"
mkdir -p "${TARGET_DIR}"

# docker-compose.yml
cat > "${TARGET_DIR}/docker-compose.yml" << EOF
services:
  ${NAME}:
    image: # TODO: set image (e.g. organization/image:tag)
    container_name: ${NAME}
    restart: unless-stopped
    ports:
      - "${PORT}:${PORT}"
    env_file:
      - ../../.env
      - .env
    labels:
      homeassistant.service: "true"
      homeassistant.name: "${NAME}"
      homeassistant.display_name: "$(echo "${NAME}" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')"
      homeassistant.description: "TODO: add description"
      homeassistant.category: "other"
      homeassistant.port: "${PORT}"
      homeassistant.icon: "box"
    networks:
      - homeassistant

networks:
  homeassistant:
    external: true
    name: homeassistant
EOF

# .env.example
cat > "${TARGET_DIR}/.env.example" << EOF
# ${NAME} environment variables
# Copy to .env and fill in real values (NEVER commit .env)

# TODO: add required environment variables
EOF

# manifest.json
cat > "${TARGET_DIR}/manifest.json" << EOF
{
  "id": "${NAME}",
  "display_name": "$(echo "${NAME}" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')",
  "description": "TODO: add description",
  "category": "other",
  "port": ${PORT},
  "internal_url": "http://${NAME}:${PORT}",
  "icon": "box",
  "tags": [],
  "docs_url": null,
  "health_check": {
    "path": "/",
    "expected_status": 200
  },
  "env_vars": []
}
EOF

# README.md
cat > "${TARGET_DIR}/README.md" << EOF
# $(echo "${NAME}" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')

TODO: add description

- **Port**: ${PORT}
- **Image**: TODO
- **Docs**: TODO

## セットアップ

\`\`\`bash
cp .env.example .env
# .env を編集
docker compose up -d
\`\`\`
EOF

echo ""
echo "Created:"
echo "  ${TARGET_DIR}/docker-compose.yml"
echo "  ${TARGET_DIR}/.env.example"
echo "  ${TARGET_DIR}/manifest.json"
echo "  ${TARGET_DIR}/README.md"
echo ""
echo "Next steps:"
echo "  1. Edit ${TARGET_DIR}/docker-compose.yml — set the image"
echo "  2. Edit ${TARGET_DIR}/manifest.json — fill in display_name, description, tags"
echo "  3. Edit ${TARGET_DIR}/.env.example — document required env vars"
echo "  4. Add port ${PORT} to PORTS.md"
echo "  5. Open a PR"
