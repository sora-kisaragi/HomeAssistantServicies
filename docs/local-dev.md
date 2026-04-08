# ローカル開発環境のセットアップ（WSL2）

## 前提条件

- Windows 11 + WSL2（Ubuntu 22.04 推奨）
- Docker Desktop for Windows（WSL2 バックエンド有効）
- Git

Docker Desktop の設定で **「Use the WSL 2 based engine」** が有効になっていることを確認してください。
これにより WSL2 の Ubuntu 内から `docker` コマンドが使えるようになります。

---

## セットアップ手順

以下はすべて **WSL2（Ubuntu）のターミナル上**で実行します。

### 1. リポジトリを clone

```bash
# WSL2 のホームディレクトリ以下に置くことを推奨
# （Windows 側の /mnt/c/... に置くとファイルシステムが遅くなる）
git clone https://github.com/sora-kisaragi/HomeAssistantServicies ~/homeassistant
cd ~/homeassistant
```

### 2. make をインストール（未インストールの場合）

```bash
sudo apt update && sudo apt install -y make
```

### 3. Docker ネットワークを作成

```bash
make network
```

### 4. 環境変数ファイルを作成

```bash
# 共通設定
cp .env.example .env

# SearXNG 用
cp services/searxng/.env.example services/searxng/.env
```

`services/searxng/.env` を開いて `SEARXNG_SECRET_KEY` を設定します：

```bash
# ランダムな秘密鍵を生成してそのままファイルに書き込む
echo "SEARXNG_SECRET_KEY=$(openssl rand -hex 32)" >> services/searxng/.env
```

PlaywrightMCP も同様に：

```bash
cp services/playwright-mcp/.env.example services/playwright-mcp/.env
```

> **discovery-api の `.env` は不要です。** 秘密情報がないため `.env` なしで起動できます。

### 5. サービスを起動

```bash
# discovery-api（サービス一覧 API）
make up SERVICE=discovery-api

# SearXNG
make up SERVICE=searxng

# PlaywrightMCP（重いので必要なときだけ起動してもよい）
make up SERVICE=playwright-mcp
```

### 6. 動作確認

```bash
# API が返ってくるか確認
curl http://localhost:8765/api/services

# ヘルスチェック
make health
```

ブラウザでも確認できます：

| サービス | URL |
| --- | --- |
| discovery-api Swagger UI | [http://localhost:8765/docs](http://localhost:8765/docs) |
| SearXNG | [http://localhost:8080](http://localhost:8080) |
| PlaywrightMCP | [http://localhost:3000](http://localhost:3000) |

---

## 日常的な操作

```bash
# ログを見る
make logs SERVICE=searxng

# サービスを止める
make down SERVICE=searxng

# 設定を変えたあと再起動
make down SERVICE=searxng && make up SERVICE=searxng

# 設定ファイルの構文チェック（PR 前に実行）
make validate
```

---

## 注意事項

### `deploy.sh` はローカルで実行しない

`scripts/deploy.sh` はサーバー用のスクリプトです。
ログ出力先 `/var/log/homeassistant/` が WSL に存在しないためエラーになります。
ローカルでは `make up` / `make down` で個別に操作してください。

### デプロイはサーバーで手動実行

本番デプロイは `main` マージ後にサーバーで `git pull && bash scripts/deploy.sh` を手動実行します。
ローカルでは `make up` するだけで十分です。

### Windows 側のブラウザからアクセスするには

Docker Desktop for Windows を使っていれば、WSL2 内で起動したコンテナには
**Windows 側のブラウザからも `localhost` でアクセスできます**。
`http://localhost:8080` をそのままブラウザで開けばOKです。

### リポジトリの置き場所について

Windows 側（`/mnt/c/Users/...`）にリポジトリを置いた場合でも動作しますが、
ファイルシステムのオーバーヘッドで `docker compose` の起動が遅くなることがあります。
WSL2 のホームディレクトリ（`~/`）に置くことを推奨します。

---

## トラブルシューティング

### `docker: command not found`

Docker Desktop が起動していないか、WSL2 インテグレーションが無効です。

Docker Desktop → Settings → Resources → WSL Integration で
使用している Ubuntu ディストリビューションが有効になっているか確認してください。

### `make: command not found`

```bash
sudo apt install -y make
```

### `network homeassistant already exists`

```bash
make network
# → "Network 'homeassistant' already exists" と表示されれば問題なし
```

### SearXNG が起動しない

`services/searxng/.env` に `SEARXNG_SECRET_KEY` が設定されているか確認します：

```bash
cat services/searxng/.env
```

空または `change_me_...` のままの場合は生成し直します：

```bash
echo "SEARXNG_SECRET_KEY=$(openssl rand -hex 32)" > services/searxng/.env
echo "SEARXNG_BASE_URL=http://localhost:8080" >> services/searxng/.env
make up SERVICE=searxng
```
