# make コマンド ガイド

## make とは？

`make` は「長いコマンドに短い名前をつけて呼び出せるツール」です。

たとえば、SearXNG を起動するには本来こう打ちます：

```bash
docker compose -f services/searxng/docker-compose.yml up -d
```

`Makefile` にこれを登録しておけば、こう書くだけで済みます：

```bash
make up SERVICE=searxng
```

このリポジトリの `Makefile` はその登録ファイルです。
`make` を使わなくても動きますが、使うと楽になります。

---

## 使い方の基本

```bash
make <コマンド名>
make <コマンド名> 変数名=値
```

コマンド一覧を確認するには：

```bash
make help
```

---

## コマンド一覧

### `make network`
**Docker の共有ネットワークを作る（初回のみ）**

このリポジトリの全コンテナは `homeassistant` という名前のネットワークで通信します。
サーバーに初めてセットアップするときに一度だけ実行します。

```bash
make network
```

---

### `make validate`
**設定ファイルに間違いがないか確認する**

以下を一括チェックします：
- 各 `docker-compose.yml` の書き方が正しいか
- 各 `manifest.json` が正しい JSON か

PR を出す前にローカルで実行しておくと安心です。

```bash
make validate
```

```text
=== Validating docker compose files ===
  [OK]  services/searxng/docker-compose.yml
  [OK]  services/playwright-mcp/docker-compose.yml
  [OK]  discovery-api/docker-compose.yml

=== Validating manifest.json files ===
  [OK]  services/searxng/manifest.json
  [OK]  services/playwright-mcp/manifest.json
```

---

### `make health`
**全サービスが正常に動いているか確認する**

各サービスのヘルスチェック URL を実際に叩いて、応答があるか確認します。

```bash
make health
```

```text
=== Health Check ===
  [OK]   searxng: http://localhost:8080/healthz => 200
  [FAIL] playwright-mcp: http://localhost:3000/ => 000
  [SKIP] discovery-api: no health_check configured

Results: 1 passed, 1 failed, 1 skipped
```

---

### `make up SERVICE=<名前>`
**特定のサービスを起動する**

```bash
make up SERVICE=searxng
make up SERVICE=playwright-mcp
make up SERVICE=discovery-api
```

内部では `docker compose -f services/searxng/docker-compose.yml up -d` が実行されます。
`-d` はバックグラウンドで動かすオプションです。

---

### `make down SERVICE=<名前>`
**特定のサービスを停止する**

```bash
make down SERVICE=searxng
```

コンテナが停止します（データは消えません）。

---

### `make logs SERVICE=<名前>`
**特定のサービスのログをリアルタイムで見る**

```bash
make logs SERVICE=searxng
```

`Ctrl+C` で終了します。

---

### `make pull`
**全サービスの Docker イメージを最新版に更新する**

```bash
make pull
```

イメージを落とすだけで、コンテナの再起動はしません。
再起動するには別途 `make up SERVICE=<名前>` が必要です。

（Watchtower を使っている場合は自動で更新されるため、手動実行は不要です）

---

### `make deploy`
**サーバー上で手動デプロイを実行する**

```bash
make deploy
```

**サーバー上で実行するコマンドです。ローカル PC からは実行しません。**

内部では `scripts/deploy.sh` が走ります：
1. `git pull` で最新コードを取得
2. 変更されたサービスだけコンテナを再起動
3. discovery-api を再起動
4. ヘルスチェックを実行

通常は GitHub にマージすると自動でこれが走るので、手動実行が必要な場面は少ないです。

---

### `make manifest`
**サービス一覧 JSON を生成する**

```bash
make manifest
```

`services/*/manifest.json` を読み込んで、`dist/services-manifest.json` にまとめます。
discovery-api が動いていれば自動で読み込まれるため、通常は実行不要です。

---

### `make add-service NAME=<名前> PORT=<ポート>`
**新サービスのテンプレートを生成する**

```bash
make add-service NAME=grafana PORT=3001
```

`services/grafana/` フォルダが作られ、以下のテンプレートファイルが入ります：

```text
services/grafana/
  docker-compose.yml   # image の行だけ TODO になっている
  manifest.json        # display_name 等を埋める
  .env.example         # 環境変数の説明を書く
  README.md            # サービスの説明を書く
```

あとはファイルを編集して PR を出すだけです。

---

## よくある使い方の流れ

### 新しいサービスを試したい

```bash
# 1. テンプレートを作る
make add-service NAME=grafana PORT=3001

# 2. ファイルを編集（image を設定等）
# services/grafana/docker-compose.yml を編集

# 3. ローカルで起動して確認
make up SERVICE=grafana

# 4. ログを確認
make logs SERVICE=grafana

# 5. 問題なければ PR を出す
```

### 設定を変えてから動作確認したい

```bash
# 1. 構文チェック
make validate

# 2. サービスを再起動（変更を反映）
make down SERVICE=searxng
make up SERVICE=searxng

# 3. ヘルスチェック
make health
```
