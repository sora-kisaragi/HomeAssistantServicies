# SearXNG

プライバシーを重視したメタ検索エンジン。

Google・Bing等を横断検索しつつトラッキングを回避する。

- **Port**: 8080
- **Image**: `searxng/searxng:latest`
- **Docs**: <https://docs.searxng.org>

## セットアップ

```bash
# .env を作成
cp .env.example .env
# .env を編集: SEARXNG_SECRET_KEY を openssl rand -hex 32 で生成

# 起動
docker compose up -d
```

## 設定ファイル

| ファイル | 説明 |
|---|---|
| `config/settings.yml` | メイン設定（検索エンジン、UI、言語等） |
| `config/limiter.toml` | レートリミッター設定 |

## ヘルスチェック

```bash
curl http://localhost:8080/healthz
```
