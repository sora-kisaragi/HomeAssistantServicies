# discovery-api の仕組み

## 何のための API？

フロントエンドが「今どんなサービスが動いているか」を知るための API です。

フロントエンドが毎回 `docker ps` を実行するわけにはいかないので、代わりに discovery-api が Docker を調べて JSON で返します。

```text
フロントエンド
  │
  └─ GET http://サーバー:8765/api/services
            │
            ▼
       discovery-api（コンテナ）
            │
            ├─ Docker ソケットを読む（どのコンテナが動いているか）
            └─ manifest.json を読む（各サービスのメタ情報）
```

---

## エンドポイント一覧

| URL | 説明 |
| --- | --- |
| `GET /api/services` | 全サービスの一覧 |
| `GET /api/services/{id}` | 特定サービスの詳細 |
| `GET /api/services/{id}/health` | 特定サービスのヘルスを今すぐ確認 |
| `GET /api/health` | discovery-api 自身が生きているか |
| `GET /docs` | ブラウザで API を試せる Swagger UI |

---

## レスポンス例

`GET /api/services` のレスポンス：

```json
{
  "timestamp": "2026-04-07T11:00:00Z",
  "host": "homeserver",
  "services": [
    {
      "id": "searxng",
      "display_name": "SearXNG",
      "description": "プライバシーを重視したメタ検索エンジン",
      "category": "search",
      "status": "running",
      "port": 8080,
      "uptime_seconds": 86400,
      "health": {
        "status": "healthy",
        "last_checked": "2026-04-07T10:59:45Z",
        "response_time_ms": 23
      },
      "container": {
        "id": "a3f9c2d1",
        "image": "searxng/searxng:latest",
        "started_at": "2026-04-06T11:00:00Z"
      },
      "tags": ["search", "privacy"],
      "docs_url": "https://docs.searxng.org"
    },
    {
      "id": "playwright-mcp",
      "display_name": "PlaywrightMCP",
      "status": "stopped",
      "port": 3000,
      "health": {
        "status": "unreachable",
        "last_checked": null
      },
      "container": null
    }
  ]
}
```

### `status` の値の意味

| 値 | 意味 |
| --- | --- |
| `running` | コンテナが動いている |
| `stopped` | コンテナが停止している（manifest には登録されているが起動していない） |
| `exited` | コンテナが異常終了した |

### `health.status` の値の意味

| 値 | 意味 |
| --- | --- |
| `healthy` | ヘルスチェック URL が期待するステータスコードを返した |
| `unhealthy` | URL には繋がったが、期待とは異なるレスポンスが来た |
| `unreachable` | 接続自体ができなかった（停止中 or ネットワーク問題） |
| `unknown` | ヘルスチェック URL が manifest に設定されていない |

---

## どうやってサービスを検出しているか？

### 方法①：Docker ラベルを読む（稼働中コンテナ）

各サービスの `docker-compose.yml` には以下のラベルが書かれています：

```yaml
labels:
  homeassistant.service: "true"
  homeassistant.name: "searxng"
  homeassistant.port: "8080"
```

discovery-api は Docker ソケット経由で「`homeassistant.service=true` ラベルを持つコンテナ」を検索し、それをサービス一覧のベースにします。

### 方法②：manifest.json を読む（停止中も含む）

`/manifests` ディレクトリ（= リポジトリの `services/` をマウント）にある各サービスの `manifest.json` を読み込みます。

これにより、コンテナが停止していても「登録されているが停止中」として一覧に表示されます。

### 統合の仕組み

```text
manifest.json に登録されているサービス
  +
Docker で実際に動いているコンテナ（ラベル付き）
  ↓
マージして1つのレスポンスに
```

---

## ヘルスチェックの仕組み

各サービスの `manifest.json` には `health_check` フィールドがあります：

```json
{
  "health_check": {
    "path": "/healthz",
    "expected_status": 200
  }
}
```

`GET /api/services` が呼ばれるたびに、discovery-api が各サービスの `http://<サービス名>:<ポート>/healthz` を実際に叩いて応答を確認します。

コンテナ同士は `homeassistant` Docker ネットワークで繋がっているため、`http://searxng:8080/healthz` のようにコンテナ名で直接アクセスできます。

---

## manifest.json の書き方

```json
{
  "id": "myservice",           // サービスの識別子（フォルダ名と同じにする）
  "display_name": "My Service", // UI に表示する名前
  "description": "説明文",
  "category": "search",        // 分類（search / automation / infrastructure / other）
  "port": 8090,                // 外部からアクセスするポート番号
  "internal_url": "http://myservice:8090", // コンテナ間通信用 URL
  "icon": "box",               // アイコン名（フロントエンドで使用）
  "tags": ["tag1", "tag2"],
  "docs_url": "https://example.com/docs",
  "health_check": {
    "path": "/healthz",        // GET リクエストを送るパス
    "expected_status": 200     // 正常時の HTTP ステータスコード
  },
  "env_vars": ["MY_API_KEY"]   // 必要な環境変数の一覧（参考情報）
}
```

---

## Swagger UI で試す

`discovery-api` が起動していれば、ブラウザで以下を開くとインタラクティブに API を試せます。

```text
http://<サーバーのIPアドレス>:8765/docs
```

ローカルで動かしている場合はこちら：

```text
http://localhost:8765/docs
```
