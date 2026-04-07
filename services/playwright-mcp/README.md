# PlaywrightMCP

Playwright を使ったブラウザ自動化の MCP (Model Context Protocol) サーバー。
LLM（Claude等）からブラウザ操作・スクリーンショット取得・Web スクレイピング等が可能になる。

- **Port**: 3000
- **Image**: `mcr.microsoft.com/playwright:v1.49.0-noble`
- **Docs**: https://github.com/microsoft/playwright-mcp

## セットアップ

```bash
# .env を作成（必要に応じて）
cp .env.example .env

# 起動
docker compose up -d
```

## MCP クライアント設定例（Claude Desktop）

```json
{
  "mcpServers": {
    "playwright": {
      "url": "http://localhost:3000"
    }
  }
}
```

## ヘルスチェック

```bash
curl http://localhost:3000/
```

## 注意事項

- ブラウザ操作を伴うため、サーバーリソース（メモリ・CPU）を消費する
- 本番環境では適切なアクセス制御を設けること
