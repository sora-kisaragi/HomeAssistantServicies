# Git 運用方針（GitHub Flow ベース）

このリポジトリは **GitHub Flow** をベースに、`develop` ブランチを統合ブランチとして運用します。

---

## ブランチ構成

| ブランチ | 役割 | マージ先 |
| --- | --- | --- |
| `main` | 本番デプロイ用。常にデプロイ可能な状態を保つ | — |
| `develop` | 統合ブランチ。フィーチャーブランチの PR はここへ | `main`（定期的） |
| `feat/*` `fix/*` etc. | 作業ブランチ。短命。 | `develop` |

```text
main ──────────────────────────────────────────► （デプロイ済み）
       ▲                             ▲
       │ develop → main（定期的）     │
       │                             │
develop ──────────────────────────────────────► （統合・CI 確認済み）
        ▲           ▲           ▲
        │           │           │
  feat/foo    fix/bar    docs/baz
```

**`main` へのマージを少なくする理由**：`main` push 時にデプロイトリガーが走るため、
不要な実行を減らして GitHub Actions の時間を節約します。

---

## 基本の流れ

1. `develop` からブランチを切る
2. ブランチ上でコミットを積む
3. `develop` へ PR を作成 → CI + レビュー → Squash merge
4. 機能が揃ったタイミングで `develop` → `main` へ PR を作成してデプロイ

---

## ブランチ命名規則

`<type>/<kebab-case-description>` の形式を使います。

| type | 用途 | 例 |
| --- | --- | --- |
| `feat` | 新しいサービス追加・新機能 | `feat/add-searxng` |
| `fix` | バグ修正 | `fix/discovery-api-timeout` |
| `docs` | ドキュメントのみの変更 | `docs/update-readme` |
| `chore` | 依存更新・設定変更など | `chore/bump-ruff-version` |
| `ci` | CI/CD ワークフローの変更 | `ci/add-shellcheck` |

命名のポイント：

- 小文字 + ハイフン区切り（スペース・アンダースコアは使わない）
- 内容が一言でわかる名前にする

---

## 開発の流れ

### 1. ブランチを作成する

```bash
git switch develop
git pull origin develop      # 最新の develop を取得
git switch -c feat/add-myservice
```

### 2. 変更をコミットする

[Conventional Commits](https://www.conventionalcommits.org/) に従います：

```text
feat: myservice を追加
fix: discovery-api のヘルスチェック timeout を修正
docs: git-workflow ドキュメントを追加
chore: ruff を 0.8.4 にアップデート
```

コミットの粒度：

- **1コミット = 1つの論理的変更**
- 「とりあえずコミット」は OK（PR マージ時に squash する）
- `WIP: ...` のような作業中コミットもブランチ上なら問題なし

### 3. pre-commit フックで自動チェック

`git commit` すると自動的に lint・format が走ります（[.pre-commit-config.yaml](../.pre-commit-config.yaml)）。

フックが失敗したら修正して再度 `git add && git commit` してください。

```bash
# 手動で全ファイルをチェックしたい場合
make lint
```

### 4. `develop` へ PR を作成する

```bash
git push origin feat/add-myservice
```

GitHub の画面で PR を作成します。**ベースブランチは `develop`** を選択してください。

PR 作成時：

- **タイトル**：コミットメッセージと同じ形式（`feat: myservice を追加`）
- **本文**：変更内容・確認してほしいポイントを簡潔に書く
- **チェックリスト**：[CONTRIBUTING.md](../CONTRIBUTING.md) の PR チェックリストを参照

PR を作成すると `validate.yml` が自動実行されます（docker compose 構文・manifest 検証など）。

### 5. Squash merge して develop に統合する

CI が通ったら **Squash and merge** でマージします。

```text
[推奨] Squash and merge
  → ブランチ上の細かいコミットをまとめて 1 コミットにする
  → develop の履歴がすっきり保たれる

[非推奨] Merge commit / Rebase and merge
  → 不要なコミットが履歴に残る
```

マージ後はブランチを即削除してください。

### 6. develop → main へ PR を作成してデプロイ

機能がまとまったタイミングで `develop` → `main` への PR を作成します。

```bash
# ローカルで develop を最新にしてから
git switch develop && git pull origin develop
```

`main` へのマージ後、サーバーで手動デプロイします：

```bash
cd /opt/homeassistant
git pull origin main
bash scripts/deploy.sh
```

---

## よくあるシナリオ

### シナリオ A：新しいサービスを追加する

```bash
git switch develop && git pull origin develop
git switch -c feat/add-myservice

make add-service NAME=myservice PORT=8090
# → services/myservice/ のファイルを編集

git add services/myservice/ PORTS.md
git commit -m "feat: myservice を追加"

git push origin feat/add-myservice
# → GitHub で develop へ PR 作成 → CI 通過 → Squash merge
```

### シナリオ B：discovery-api のバグを修正する

```bash
git switch develop && git pull origin develop
git switch -c fix/health-probe-timeout

# discovery-api/app/main.py を修正
git add discovery-api/app/main.py
git commit -m "fix: ヘルスプローブの timeout を 5s → 10s に変更"

git push origin fix/health-probe-timeout
# → GitHub で develop へ PR 作成 → CI 通過 → Squash merge
```

### シナリオ C：develop が先に進んでいてブランチが古くなった

```bash
git switch feat/add-myservice
git fetch origin
git rebase origin/develop

# コンフリクトがあれば解消してから
git rebase --continue
```

---

## やってはいけないこと

| NG 操作 | 理由 |
| --- | --- |
| `main` に直接 push | デプロイが意図せず走る・CI を経ない |
| `develop` に直接 push | レビューを経ない変更が統合される |
| `--force-push` を `main`/`develop` に実行 | 他者のコミットが消える |
| ブランチを長期間放置する | develop との差分が大きくなりコンフリクトが増える |

---

## ブランチの寿命

ブランチは**短命**に保ちます。

- 作業開始から PR マージまでを **数日以内** を目安にする
- 長引く場合は定期的に `git rebase origin/develop` で develop に追従する
- マージ後はブランチを即削除する

---

## Fork して使う

このリポジトリは個人の自宅サーバー設定です。

**他の人が自分のサーバーで使いたい場合は Fork してください。**

直接の push 権限はオーナーのみです。

### Fork の手順

```bash
# 1. GitHub 上で右上の「Fork」ボタンを押す
#    → github.com/<your-username>/HomeAssistantServicies が作成される

# 2. Fork 先を clone する
git clone https://github.com/<your-username>/HomeAssistantServicies /opt/homeassistant
cd /opt/homeassistant

# 3. upstream（元リポジトリ）を登録しておく
git remote add upstream https://github.com/sora-kisaragi/HomeAssistantServicies
```

### Fork 後のワークフロー

Fork 後は **自分のリポジトリ** として同じフローをそのまま使えます。

```text
upstream/main（元リポジトリ）
       │
       │ 更新を取り込みたいとき
       ▼
origin/develop（自分の Fork）
       │
       │ ブランチを切る
       ▼
  feat/add-myservice ──► PR（develop へ）──► develop にマージ ──► main にマージ ──► デプロイ
```

```bash
# 元リポジトリの更新を自分の Fork に取り込む
git fetch upstream
git switch develop
git merge upstream/develop
git push origin develop
```

### Fork とテンプレートの違い

| | Fork | Template（Use this template） |
| --- | --- | --- |
| 元リポジトリとの繋がり | あり（PR で貢献できる） | なし（完全に独立） |
| upstream の更新を取り込める | はい（`git fetch upstream`） | 手動コピーが必要 |
| 適した用途 | 元の変更を取り込みながら使いたい | 完全に独自の設定にしたい |

自宅サーバー用途なら **Fork を推奨**します（upstream の修正を取り込みやすいため）。

---

## GitHub リポジトリ設定（推奨）

### Branch Protection Rules

**`main` ブランチ**（`Settings > Branches > Add branch protection rule`）：

| 設定項目 | 値 | 理由 |
| --- | --- | --- |
| Require a pull request before merging | ON | 直接 push を禁止 |
| Require status checks to pass | ON（`validate` を選択） | CI が通らない PR はマージ不可 |
| Require branches to be up to date before merging | ON | 乖離した状態でのマージを防ぐ |
| Do not allow bypassing the above settings | ON | 管理者も例外なし |
| Allow force pushes | OFF | 履歴を書き換えさせない |

**`develop` ブランチ**にも同様のルールを設定することを推奨します。

### Repository 一般設定

`Settings > General > Pull Requests` の推奨値：

| 設定項目 | 推奨値 |
| --- | --- |
| Default branch | `develop` |
| Automatically delete head branches | ON |
| Allow squash merging | ON |
| Allow merge commits | OFF |
| Allow rebase merging | OFF |

> `main` の履歴を「1PR = 1コミット」に保つため、squash 以外を OFF にします。

---

## 関連ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | コミット規約・コードスタイル・PR チェックリスト |
| [cicd.md](cicd.md) | PR 時の validate・マージ時のデプロイの仕組み |
