# Faster Whisper

OpenAI Whisper ベースの高速 STT（音声認識）サービス。

GPU を使用してリアルタイムに近い速度で文字起こしを行う。
モデルは初回起動時に HuggingFace から自動ダウンロードされる（named volume にキャッシュ）。

- **Port**: 9001
- **Image**: `ghcr.io/fedirz/faster-whisper-server:latest`（ARM64 対応。CUDA 専用イメージは amd64 のみのため CPU モード）
- **Docs**: <https://github.com/fedirz/faster-whisper-server>
- **運用**: オンデマンド（1時間無操作で自動停止）

## 必要条件

- NVIDIA GPU（CUDA 対応）
- NVIDIA Container Toolkit インストール済み

## セットアップ

```bash
# .env を作成（任意）
cp .env.example .env

# 起動（オンデマンド管理する場合は discovery-api の API 経由でも可）
docker compose up -d
```

## 使用例

```bash
# 文字起こし（wav ファイル）
curl http://localhost:9001/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=large-v3

# ヘルスチェック
curl http://localhost:9001/health
```

## モデルサイズ目安

| モデル | VRAM | 精度 |
|--------|------|------|
| `tiny` | ~1GB | 低 |
| `base` | ~1GB | 低 |
| `medium` | ~5GB | 中 |
| `large-v3` | ~10GB | 高 |

## ヘルスチェック

```bash
curl http://localhost:9001/health
```
