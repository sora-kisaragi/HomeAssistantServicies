# Watcher UI

サービス管理ダッシュボード。

discovery-api のデータをリアルタイムで表示し、GUI から各サービスの起動・停止・リソース監視が行える。

- **Port**: 8767
- **Image**: カスタムビルド（`python:3.12-slim` ベース）
- **Backend**: FastAPI（静的ファイル配信 + SSE）
- **Frontend**: Alpine.js（CDN）、ビルドステップなし

## 機能

- サービス一覧（稼働状態・タグ・ヘルス）
- start / stop ボタン（オンデマンドサービス対応）
- CPU・メモリ使用率バー
- GPU 使用率・VRAM 表示
- アイドルタイムアウト残り時間
- 未登録コンテナ検出と登録ガイド
- SSE によるリアルタイム更新（5秒間隔）

## 必要条件

- discovery-api が稼働していること（同一 `homeassistant` ネットワーク内）

## セットアップ

```bash
# .env を作成（任意）
cp .env.example .env

# ビルド・起動
docker compose up -d --build
```

ブラウザで `http://localhost:8767` を開く。

## ヘルスチェック

```bash
curl http://localhost:8767/
```
