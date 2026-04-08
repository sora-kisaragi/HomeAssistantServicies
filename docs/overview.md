# リポジトリ全体の仕組み

## このリポジトリは何をするもの？

一言で言うと「**複数の Docker コンテナをまとめて管理する設定置き場**」です。

PlaywrightMCP や SearXNG のような OSS ツールはそれぞれ Docker イメージが公開されています。
このリポジトリでは「どのイメージをどのポートで動かすか」という設定ファイルを管理し、
さらに「設定を変えたら自動でサーバーに反映する」仕組みも整えています。

---

## 全体像

```text
あなたのPC（このリポジトリ）
  │
  │  設定を変更して PR → main にマージ
  │
  ▼
GitHub
  ├─ PR 時    → 設定ミスがないか自動チェック（validate.yml）
  └─ マージ時 → サーバーに「デプロイして」と指示（deploy-trigger.yml）
                        │
                        ▼ （サーバーから GitHub に接続して受け取る）
               自宅サーバー / VPS
                 ├─ SearXNG コンテナ（port 8080）
                 ├─ PlaywrightMCP コンテナ（port 3000）
                 ├─ discovery-api コンテナ（port 8765）  ← サービス一覧 API
                 └─ Watchtower コンテナ（Docker イメージ自動更新）

別リポジトリのフロントエンド
  └─ GET http://サーバー:8765/api/services
       → 稼働中のサービス一覧・ポート番号・ヘルス状態を取得
```

---

## 主要な登場人物

### `services/<名前>/` フォルダ
1サービス = 1フォルダです。フォルダの中に4つのファイルを置くのがルールです。

| ファイル | 役割 |
| --- | --- |
| `docker-compose.yml` | コンテナの起動設定（イメージ・ポート・環境変数など） |
| `manifest.json` | discovery-api が読むメタデータ（表示名・ポート・ヘルスチェック先） |
| `.env.example` | 必要な環境変数の説明書（実際の値は書かない） |
| `README.md` | そのサービスの説明書 |

### `discovery-api/`
サーバー上で動く小さな API サーバーです。
Docker のソケット（通信口）を覗いて「今どのコンテナが動いているか」を調べ、
`/api/services` にアクセスすると JSON で一覧を返します。

### `scripts/`
シェルスクリプト（`.sh` ファイル）の集まりです。
- `deploy.sh` — git pull → 変更サービスだけ再起動、という一連の作業を自動化
- `health-check.sh` — 全サービスの URL を叩いて生きているか確認
- `add-service.sh` — 新サービスのフォルダをテンプレートから自動生成

### `Makefile`
「よく使うコマンドのショートカット集」です。
`make validate` と打つだけで、長い docker compose コマンドを毎回書かずに済みます。
→ 詳しくは [make-guide.md](make-guide.md) を参照。

### `.github/workflows/`
GitHub Actions の設定ファイルです。PR を出したりマージしたりすると、
GitHub のサーバー上で自動的にスクリプトが走ります。
→ 詳しくは [cicd.md](cicd.md) を参照。

---

## データの流れ（新サービスを追加するとき）

```text
1. make add-service NAME=myapp PORT=8090
   └─ services/myapp/ フォルダとテンプレートファイルが生成される

2. ファイルを編集（docker-compose.yml にイメージを設定など）

3. git push → Pull Request を作成
   └─ GitHub Actions が自動で構文チェックを実行

4. PR をレビューして main にマージ
   └─ サーバーで手動実行（git pull && bash scripts/deploy.sh）
      └─ myapp コンテナが起動

5. discovery-api が自動的に myapp を検出
   └─ /api/services に myapp が追加される
```

---

## ファイルを変えたらどうなる？

| 変更内容 | 何が起きるか |
| --- | --- |
| `services/searxng/docker-compose.yml` を編集 | PR時に構文チェック → マージでサーバーが searxng だけ再起動 |
| `services/searxng/manifest.json` を編集 | マージで discovery-api が再起動し、API レスポンスが更新される |
| 新しい `services/mynew/` を追加 | マージで mynew コンテナが起動し、API に現れる |
| `.env` を変更 | `.env` はコミットしないルール。サーバーに SSH して手動変更 |
