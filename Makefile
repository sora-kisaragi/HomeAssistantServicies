.PHONY: help validate deploy health manifest add-service up down logs pull network setup-dev lint

REPO_DIR := $(shell pwd)
SERVICE ?=
NAME ?=
PORT ?=

help: ## このヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Variables:"
	@echo "    SERVICE=<name>   対象サービス名 (up/down/logs/pull で使用)"
	@echo "    NAME=<name>      新サービス名 (add-service で使用)"
	@echo "    PORT=<number>    新サービスのポート (add-service で使用)"

setup-dev: ## 開発環境セットアップ（pre-commit フックをインストール）
	@if ! command -v pipx >/dev/null 2>&1; then \
		echo "pipx が見つかりません。インストールします..."; \
		sudo apt install -y pipx; \
	fi
	pipx install pre-commit
	export PATH="$${HOME}/.local/bin:$$PATH" && pre-commit install
	@echo "pre-commit hooks installed."
	@echo "※ 次のターミナルから pre-commit コマンドが直接使えます（pipx ensurepath で PATH に追加済み）。"

lint: ## 全ファイルに lint + format を実行（pre-commit + markdownlint）
	export PATH="$${HOME}/.local/bin:$$PATH" && pre-commit run --all-files
	npx markdownlint-cli2 "**/*.md"

network: ## homeassistant Docker ネットワークを作成（初回のみ）
	docker network create homeassistant 2>/dev/null || echo "Network 'homeassistant' already exists"

validate: ## 全サービスの docker compose 構文をチェック
	@echo "=== Validating docker compose files ==="
	@failed=0; \
	for compose in services/*/docker-compose.yml discovery-api/docker-compose.yml; do \
		svc=$$(dirname $$compose); \
		if [ -f "$$svc/.env.example" ]; then \
			cp "$$svc/.env.example" "$$svc/.env.validate_tmp"; \
		fi; \
		if docker compose -f "$$compose" config --quiet 2>&1; then \
			echo "  [OK]  $$compose"; \
		else \
			echo "  [FAIL] $$compose"; \
			failed=1; \
		fi; \
		rm -f "$$svc/.env.validate_tmp"; \
	done; \
	echo ""; \
	echo "=== Validating manifest.json files ==="; \
	for manifest in services/*/manifest.json discovery-api/manifest.json; do \
		if python3 -m json.tool "$$manifest" > /dev/null 2>&1; then \
			echo "  [OK]  $$manifest"; \
		else \
			echo "  [FAIL] $$manifest"; \
			failed=1; \
		fi; \
	done; \
	exit $$failed

deploy: ## deploy.sh を手動実行（サーバー上で実行すること）
	@bash scripts/deploy.sh

health: ## 全サービスのヘルスチェック
	@bash scripts/health-check.sh

manifest: ## dist/services-manifest.json を再生成
	@bash scripts/generate-manifest.sh

add-service: ## 新サービスのスキャフォールドを生成 (NAME=foo PORT=8090 必須)
	@if [ -z "$(NAME)" ] || [ -z "$(PORT)" ]; then \
		echo "Usage: make add-service NAME=<service-name> PORT=<port>"; \
		exit 1; \
	fi
	@bash scripts/add-service.sh NAME=$(NAME) PORT=$(PORT)

up: ## 特定サービスを起動 (SERVICE=<name> 必須)
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make up SERVICE=<name>"; exit 1; fi
	@if [ -f "services/$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f services/$(SERVICE)/docker-compose.yml up -d; \
	elif [ -f "infra/$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f infra/$(SERVICE)/docker-compose.yml up -d; \
	elif [ -f "$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f $(SERVICE)/docker-compose.yml up -d; \
	else \
		echo "Not found: $(SERVICE)"; exit 1; \
	fi

down: ## 特定サービスを停止 (SERVICE=<name> 必須)
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make down SERVICE=<name>"; exit 1; fi
	@if [ -f "services/$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f services/$(SERVICE)/docker-compose.yml down; \
	elif [ -f "infra/$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f infra/$(SERVICE)/docker-compose.yml down; \
	elif [ -f "$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f $(SERVICE)/docker-compose.yml down; \
	else \
		echo "Not found: $(SERVICE)"; exit 1; \
	fi

logs: ## 特定サービスのログを tail (SERVICE=<name> 必須)
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make logs SERVICE=<name>"; exit 1; fi
	@if [ -f "services/$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f services/$(SERVICE)/docker-compose.yml logs -f; \
	elif [ -f "infra/$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f infra/$(SERVICE)/docker-compose.yml logs -f; \
	elif [ -f "$(SERVICE)/docker-compose.yml" ]; then \
		docker compose -f $(SERVICE)/docker-compose.yml logs -f; \
	else \
		echo "Not found: $(SERVICE)"; exit 1; \
	fi

pull: ## 全イメージの最新版を pull
	@echo "=== Pulling all images ==="
	@for compose in services/*/docker-compose.yml discovery-api/docker-compose.yml infra/watchtower/docker-compose.yml; do \
		[ -f "$$compose" ] && docker compose -f "$$compose" pull --quiet && echo "  pulled: $$compose" || true; \
	done
