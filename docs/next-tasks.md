# 次への課題

## 優先度：高

### 1. 本番サーバーへの展開

ローカル（WSL2）での動作確認は完了。次は実際のサーバーにセットアップする。

- [ ] サーバーに Docker + Docker Compose v2 をインストール
- [ ] リポジトリを `/opt/homeassistant` に clone
- [ ] 各サービスの `.env` を作成（シークレットを設定）
- [ ] `make network` でネットワーク作成
- [ ] 全サービスを起動して `make health` で確認
- [ ] main マージ後に `git pull && bash scripts/deploy.sh` で手動デプロイして動作確認

### 2. GitHub リポジトリの保護設定

→ 詳細は下の「GitHub 側でやること」セクションを参照

### 3. deploy.sh の手動実行フロー

デプロイは `main` マージ後にサーバーで手動実行する運用。

```bash
cd /opt/homeassistant
git pull origin main
bash scripts/deploy.sh
```

---

## 優先度：中

### 4. discovery-api の manifest 読み込み改善

`GET /api/services` のレスポンスで discovery-api 自身が `display_name: "discovery-api"`
（manifest.json の値ではなくコンテナ名のデフォルト）になっている。

原因：`discovery-api/manifest.json` が `/manifests`（= `services/` のみをマウント）の外にある。

対処案：`discovery-api/docker-compose.yml` に追加マウントを加える。

```yaml
volumes:
  - ../services:/manifests:ro
  - ./manifest.json:/manifests/discovery-api/manifest.json:ro  # 追加
```

### 5. フロントエンドの開発

別リポジトリで `GET /api/services` を叩いてサービス一覧を表示するフロントエンドを作る。

API レスポンスで使えるフィールド：

- `status` — running / stopped でバッジ表示
- `health.status` — healthy / unhealthy でインジケーター表示
- `port` — 「開く」ボタンのリンク生成
- `category` — タブやフィルターで絞り込み
- `tags` — 検索・フィルター
- `docs_url` — ドキュメントへのリンク

### 6. Watchtower の有効化

`infra/watchtower/docker-compose.yml` は作成済みだが未起動。
本番サーバーに展開後、Docker イメージの自動更新を有効にする。

```bash
docker compose -f infra/watchtower/docker-compose.yml up -d
```

---

## 優先度：低

### 7. サービス追加

必要に応じて以下のようなサービスを追加できる（`make add-service` で雛形生成）。

候補例：

- Portainer（Docker 管理 UI）
- Grafana（メトリクス可視化）
- n8n（ワークフロー自動化）
- Open WebUI（LLM フロントエンド）

### 8. デプロイ通知

`deploy-trigger.yml` に Slack / Discord 通知のステップが TODO として残っている。
本番運用を始めたら設定する。

---

## GitHub 側でやること

### Branch Protection Rules（必須）

現状は誰でも main に直接 push できる。以下を設定する。

設定場所：`Settings > Branches > Add branch protection rule`、対象ブランチ: `main`

| 設定項目 | 推奨値 | 理由 |
| --- | --- | --- |
| Require a pull request before merging | ON | 直接 push を禁止 |
| Require approvals | 1 | レビューなしのマージを防ぐ（1人運用なら任意） |
| Require status checks to pass | ON | validate.yml が失敗したらマージ不可にする |
| Required status checks | `validate` | validate.yml の job 名を指定 |
| Do not allow bypassing the above settings | ON | 管理者も例外なし |

### Environment Protection（推奨）

deploy-trigger.yml が `environment: production` を指定しているが、
GitHub 側で Environment を作成しないと保護が効かない。

設定場所：`Settings > Environments > New environment`、名前: `production`

| 設定項目 | 推奨値 | 理由 |
| --- | --- | --- |
| Required reviewers | 自分のアカウント | デプロイ前に手動承認が入る |
| Deployment branches | Selected branches: `main` | main 以外からのデプロイを禁止 |
