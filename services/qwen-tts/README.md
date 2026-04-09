# Qwen TTS

Qwen2.5-TTS による高品質テキスト読み上げサービス。

OpenAI 互換の `/v1/audio/speech` API でテキストから音声を生成する。
モデルは初回起動時に HuggingFace から自動ダウンロードされる（named volume にキャッシュ）。

- **Port**: 9002
- **Image**: カスタムビルド（`pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime` ベース）
- **Model**: `Qwen/Qwen3-TTS-12Hz-1.7B-Base`（デフォルト）
- **Docs**: <https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base>
- **運用**: オンデマンド（1時間無操作で自動停止）

## 必要条件

- NVIDIA GPU（CUDA 12.1 対応）
- NVIDIA Container Toolkit インストール済み
- VRAM: 3B モデルで約 8GB、7B モデルで約 16GB

## セットアップ

```bash
# .env を作成（任意）
cp .env.example .env

# イメージをビルドして起動
docker compose up -d --build
```

初回はモデルダウンロードのため起動に数分かかる場合がある。

## 使用例

```bash
# 音声合成（WAV 出力）
curl http://localhost:9002/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "こんにちは、世界！", "voice": "default"}' \
  --output speech.wav

# ヘルスチェック
curl http://localhost:9002/health
```

## モデル選択

| モデル | パラメータ | 用途 |
|--------|-----------|------|
| `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | 1.7B | 汎用 TTS（デフォルト） |
| `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | 0.6B | 軽量・高速 |
| `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | 1.7B | 音声クローン（Issue #10 参照） |

`.env` の `QWEN_TTS_MODEL` で切り替え可能。

## ヘルスチェック

```bash
curl http://localhost:9002/health
```
