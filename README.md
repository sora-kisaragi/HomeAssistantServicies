# HomeAssistantServicies

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Validate](https://github.com/sora-kisaragi/HomeAssistantServicies/actions/workflows/validate.yml/badge.svg)](https://github.com/sora-kisaragi/HomeAssistantServicies/actions/workflows/validate.yml)
[![GitHub last commit](https://img.shields.io/github/last-commit/sora-kisaragi/HomeAssistantServicies)](https://github.com/sora-kisaragi/HomeAssistantServicies/commits/main)

PlaywrightMCP・SearXNG などの OSS コンテナをまとめて管理するリポジトリです。

各サービスの Docker Compose 設定、自動デプロイ、ヘルスチェックをここで一元管理します。

> **自分のサーバーで使いたい場合は Fork してください。**
> このリポジトリは個人設定のため、直接の push 権限はオーナーのみです。
> Fork すれば自由にカスタマイズでき、このリポジトリの更新を取り込むことも可能です。
> 詳しくは [docs/git-workflow.md#fork-して使う](docs/git-workflow.md#fork-して使う) を参照してください。

## このリポジトリでできること

| やりたいこと                     | 手段                                                          |
| -------------------------------- | ------------------------------------------------------------- |
| 新しいサービスを追加する         | `make add-service NAME=foo PORT=8090` でテンプレート生成 → PR |
| PR 時に設定ミスを検出する        | GitHub Actions が自動で compose 構文・manifest を検証         |
| main マージで手動デプロイ        | サーバーで `scripts/deploy.sh` を手動実行                     |
| 稼働サービス一覧を API で取得    | `GET http://<server>:8765/api/services`                       |
| フロントエンドからサービスを発見 | 上記 API のレスポンスに port・health・メタ情報が含まれる      |

## ディレクトリ構成

```text
services/
  searxng/              プライバシー重視のメタ検索エンジン（port 8080）
  playwright-mcp/       ブラウザ自動化 MCP サーバー（port 3000）
  <新サービス>/         make add-service で追加

discovery-api/          稼働サービス一覧を返す FastAPI（port 8765）
infra/watchtower/       Docker イメージの自動更新
scripts/                deploy.sh / health-check.sh 等
.github/workflows/      CI/CD（PR 検証 + 自動デプロイ）
PORTS.md               ポート割り当て一覧（衝突防止）
```

各サービスは以下の 4 ファイルで構成されます：

```text
services/<name>/
  docker-compose.yml   コンテナ定義
  manifest.json        API が読むメタデータ（port・health_check 等）
  .env.example         必要な環境変数の一覧（実値はコミットしない）
  README.md            サービス固有の説明
```

## API レスポンス例

`GET http://<server>:8765/api/services` を叩くとこのような JSON が返ります。

フロントエンドはこれを使ってサービス一覧を動的に表示できます。

```json
{
  "timestamp": "2026-04-07T11:00:00Z",
  "host": "homeserver",
  "services": [
    {
      "id": "searxng",
      "display_name": "SearXNG",
      "status": "running",
      "port": 8080,
      "health": { "status": "healthy", "response_time_ms": 23 },
      "container": { "image": "searxng/searxng:latest" }
    },
    {
      "id": "playwright-mcp",
      "display_name": "PlaywrightMCP",
      "status": "stopped",
      "port": 3000,
      "health": { "status": "unreachable" }
    }
  ]
}
```

その他のエンドポイント：

| エンドポイント           | 説明                         |
| ------------------------ | ---------------------------- |
| `GET /api/services`      | 全サービス一覧               |
| `GET /api/services/{id}` | 単体サービス詳細             |
| `GET /api/health`        | API 自身の死活確認           |
| `GET /docs`              | Swagger UI（ブラウザで確認） |

## 新サービスの追加手順

```bash
# 1. テンプレートを生成
make add-service NAME=myservice PORT=8090

# 2. 生成されたファイルを編集
#    services/myservice/docker-compose.yml  → image を設定
#    services/myservice/manifest.json       → display_name・tags を記入
#    services/myservice/.env.example        → 必要な環境変数を記載
#    PORTS.md                               → ポートを追記

# 3. PR を出す → validate.yml が自動チェック → main マージで自動デプロイ
```

## サーバー初回セットアップ

### 前提条件

- Ubuntu/Debian、Docker + Docker Compose v2、Git

### 手順

```bash
# リポジトリを clone
git clone https://github.com/sora-kisaragi/HomeAssistantServicies /opt/homeassistant
cd /opt/homeassistant

# Docker ネットワークを作成（全サービスが共有する）
make network

# 共通 .env を作成
cp .env.example .env && nano .env

# 各サービスの .env を作成（シークレットを設定）
cp services/searxng/.env.example services/searxng/.env && nano services/searxng/.env
cp services/playwright-mcp/.env.example services/playwright-mcp/.env

# サービスを起動
make up SERVICE=discovery-api
make up SERVICE=searxng
make up SERVICE=playwright-mcp
make up SERVICE=watchtower

# 動作確認
make health
```

### デプロイ（手動）

main マージ後、サーバーで以下を手動実行してデプロイします。

```bash
cd /opt/homeassistant
git pull origin main
bash scripts/deploy.sh
```

## CI/CD の流れ

```text
PR 作成
  └─ validate.yml が自動実行
       ├─ docker compose config で構文チェック
       ├─ manifest.json の JSON 検証
       └─ 必須ファイルの存在確認

main にマージ
  └─ サーバーで手動実行
       └─ scripts/deploy.sh
            ├─ git pull
            ├─ 変更されたサービスだけ pull + up -d
            ├─ discovery-api を再起動
            └─ health-check.sh で確認
```

## シークレット管理

- `.env` ファイルは `.gitignore` で除外済み — **絶対にコミットしない**
- `.env.example` が変数名のドキュメント（実値なし）
- 実値はサーバー上で手動管理（初回 SSH 時のみ設定が必要）

## よく使うコマンド

```bash
make validate              # compose 構文・manifest を一括チェック
make health                # 全サービスのヘルス確認
make up SERVICE=searxng    # 特定サービスを起動
make down SERVICE=searxng  # 特定サービスを停止
make logs SERVICE=searxng  # ログを tail
make pull                  # 全イメージを更新
make add-service NAME=foo PORT=8090  # 新サービスのスキャフォールド
make setup-dev             # pre-commit フックをインストール（初回のみ）
make lint                  # 全ファイルに lint + format を実行
```

## 詳細ドキュメント

仕組みをもっと詳しく知りたい場合は [docs/](docs/) を参照してください。

| ドキュメント                                   | 内容                                                  |
| ---------------------------------------------- | ----------------------------------------------------- |
| [docs/overview.md](docs/overview.md)           | リポジトリ全体の仕組みと登場人物                      |
| [docs/make-guide.md](docs/make-guide.md)       | `make` コマンドの使い方                               |
| [docs/cicd.md](docs/cicd.md)                   | CI/CD の仕組み（自動チェック・自動デプロイ）          |
| [docs/discovery-api.md](docs/discovery-api.md) | サービス一覧 API の仕組みとレスポンス形式             |
| [docs/local-dev.md](docs/local-dev.md)         | WSL2 でのローカル開発環境セットアップ手順             |
| [docs/git-workflow.md](docs/git-workflow.md)   | Git 運用方針（GitHub Flow・ブランチ命名・PR ルール）  |
