# CI/CD の仕組み

## CI/CD とは？

- **CI（継続的インテグレーション）** — コードを変更するたびに自動でテスト・チェックを走らせる
- **CD（継続的デリバリー）** — チェックが通ったら自動でサーバーに反映する

このリポジトリでは GitHub Actions を使って CI/CD を実現しています。

---

## 全体の流れ

```text
あなた                  GitHub                   サーバー
  │                       │                         │
  ├─ PR を作成 ──────────►│                         │
  │                       ├─ validate.yml 実行      │
  │                       │   構文チェック等         │
  │◄── チェック結果 ───────┤                         │
  │                       │                         │
  ├─ main にマージ ───────►│                         │
  │                       ├─ deploy-trigger.yml 実行│
  │                       │   └─ self-hosted runner ─►│
  │                       │                         ├─ git pull
  │                       │                         ├─ コンテナ再起動
  │                       │                         └─ ヘルスチェック
  │                       │◄── 結果（成功/失敗） ────┤
```

---

## ワークフロー①：validate.yml（PR 時）

**いつ動く？** → `main` ブランチへの PR を作成・更新したとき

**何をするか？** GitHub のクラウドサーバー（ubuntu-latest）上で以下を実行します：

### ステップ1：必須ファイルの確認
`services/` 配下の全フォルダに、以下の4ファイルが揃っているか確認します。

```text
docker-compose.yml
manifest.json
.env.example
README.md
```

1つでも欠けていると PR がブロックされます。

### ステップ2：docker compose の構文チェック
各サービスの `docker-compose.yml` を `docker compose config` コマンドで検証します。
YAML の書き方ミスや、存在しない設定キーを検出できます。

> **ポイント**：検証時は `.env.example` の内容を仮の `.env` として使います。
> これにより「環境変数が定義されていない」というエラーを防ぎます。

### ステップ3：manifest.json の検証
各 `manifest.json` が正しい JSON 形式か、必須フィールド（`id`・`display_name`・`port`）があるか確認します。

### ステップ4：Dockerfile の lint（hadolint）
`Dockerfile` があれば、セキュリティや最善策の観点でチェックします。

---

## ワークフロー②：deploy-trigger.yml（マージ時）

**いつ動く？** → `main` ブランチに push（= PR マージ）されたとき

**何をするか？** サーバー上の self-hosted runner が `scripts/deploy.sh` を実行します。

### self-hosted runner とは？

通常の GitHub Actions は GitHub のクラウドサーバーで動きます。
しかし自宅サーバーへのデプロイには使えません（GitHub からサーバーに入れない）。

`self-hosted runner` はサーバー側に常駐するプログラムで、
**サーバーから GitHub へ** outbound 接続してジョブを受け取ります。
サーバーに inbound ポートを開ける必要がないため、NAT の内側でも動作します。

```text
GitHub
  │
  │◄────────────────── サーバーが接続を維持（outbound）
  │
  └─ 「deploy job が来たよ」と通知
            │
            ▼
       サーバー上で deploy.sh が実行される
```

### deploy.sh の動作

```text
1. git pull origin main
   └─ 最新の設定ファイルをサーバーにダウンロード

2. 変更されたサービスを検出
   └─ git diff で直前のコミットと比較
      例: services/searxng/ が変わっていたら searxng を対象に

3. 変更サービスを再起動
   └─ docker compose pull（最新イメージをダウンロード）
   └─ docker compose up -d（コンテナを更新起動）

4. discovery-api を再起動
   └─ manifest.json の変更を反映させるため毎回実行

5. ヘルスチェック
   └─ 全サービスの URL を叩いて応答を確認
   └─ 失敗があれば GitHub Actions の結果が「失敗」になる
```

### 変更されたサービスだけ再起動する理由

全サービスを毎回再起動すると、変更に無関係なサービスも一時的に停止します。
`deploy.sh` は `git diff` で変更ファイルを調べて、関係するサービスだけ再起動します。

例：SearXNG の設定だけ変えた PR をマージ → SearXNG だけ再起動、PlaywrightMCP は停止しない。

---

## GitHub Actions の結果を見る場所

リポジトリの **Actions タブ** でワークフローの実行履歴と詳細ログを確認できます。

```text
https://github.com/sora-kisaragi/HomeAssistantServicies/actions
```

デプロイが失敗した場合、ここでエラーの詳細を確認できます。

---

## セキュリティの考え方

| 懸念 | 対策 |
| --- | --- |
| `.env`（パスワード等）が GitHub に漏れる | `.gitignore` で除外。絶対にコミットしない |
| runner が乗っ取られてサーバーが危険になる | GitHub の `environment` 保護ルールで承認フローを追加できる |
| 誰でも main にマージできる | Branch Protection Rules で PR レビュー必須にする |
