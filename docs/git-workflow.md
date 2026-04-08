# Git 運用方針（GitHub Flow）

このリポジトリは **GitHub Flow** を採用しています。
ルールはシンプルで、「`main` は常にデプロイ可能な状態を保つ」ことが唯一の原則です。

---

## GitHub Flow とは？

```text
main ───────────────────────────────────────────► （常にデプロイ可能）
        │                           ▲
        │ ブランチを切る             │ PR をマージ
        ▼                           │
     feat/add-searxng ──コミット──► PR 作成 → レビュー/CI → マージ
```

1. `main` からブランチを切る
2. ブランチ上でコミットを積む
3. PR を作成する
4. CI チェックとレビューが通ったらマージ
5. `main` へのマージ = 即デプロイ

Git Flow のような `develop` ブランチや `release` ブランチは使いません。
ブランチは `main` から生え、`main` に戻るだけです。

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

**命名のポイント：**
- 小文字 + ハイフン区切り（スペース・アンダースコアは使わない）
- 内容が一言でわかる名前にする
- 長くなる場合は `feat/add-foo-service` 程度に抑える

---

## 開発の流れ

### 1. ブランチを作成する

```bash
git switch main
git pull origin main          # 最新の main を取得
git switch -c feat/add-myservice
```

### 2. 変更をコミットする

[Conventional Commits](https://www.conventionalcommits.org/) に従います：

```
feat: myservice を追加
fix: discovery-api のヘルスチェック timeout を修正
docs: git-workflow ドキュメントを追加
chore: ruff を 0.8.4 にアップデート
```

コミットの粒度：
- **1コミット = 1つの論理的変更**
- 「とりあえずコミット」は OK。PR マージ時に squash する
- `WIP: ...` のような作業中コミットもブランチ上なら問題なし

### 3. pre-commit フックで自動チェック

`git commit` すると自動的に lint・format が走ります（[.pre-commit-config.yaml](../.pre-commit-config.yaml)）。
フックが失敗したら修正して再度 `git add && git commit` してください。

```bash
# 手動で全ファイルをチェックしたい場合
make lint
```

### 4. PR を作成する

```bash
git push origin feat/add-myservice
```

GitHub の画面で PR を作成します。PR 作成時：

- **タイトル**：コミットメッセージと同じ形式（`feat: myservice を追加`）
- **本文**：変更内容・確認してほしいポイントを簡潔に書く
- **チェックリスト**：[CONTRIBUTING.md](../CONTRIBUTING.md) の PR チェックリストを参照

PR を作成すると `validate.yml` が自動実行されます（docker compose 構文・manifest 検証など）。

### 5. マージする

CI が通ったら **Squash and merge** でマージします。

```text
[推奨] Squash and merge
  → ブランチ上の細かいコミットをまとめて 1 コミットにする
  → main の履歴がすっきり保たれる

[非推奨] Merge commit
  → 不要な "Merge branch ..." コミットが main に残る

[非推奨] Rebase and merge
  → 複数コミットがそのまま main に入る（スカッシュの意味がない）
```

マージしたら、サーバーで `git pull && bash scripts/deploy.sh` を手動実行してデプロイします。
ブランチは GitHub の UI からそのまま削除してください。

---

## よくあるシナリオ

### シナリオ A：新しいサービスを追加する

```bash
git switch main && git pull origin main
git switch -c feat/add-myservice

make add-service NAME=myservice PORT=8090
# → services/myservice/ のファイルを編集

git add services/myservice/ PORTS.md
git commit -m "feat: myservice を追加"

git push origin feat/add-myservice
# → GitHub で PR 作成 → CI 通過 → Squash merge
```

### シナリオ B：discovery-api のバグを修正する

```bash
git switch main && git pull origin main
git switch -c fix/health-probe-timeout

# discovery-api/app/main.py を修正
git add discovery-api/app/main.py
git commit -m "fix: ヘルスプローブの timeout を 5s → 10s に変更"

git push origin fix/health-probe-timeout
# → GitHub で PR 作成 → CI 通過 → Squash merge
```

### シナリオ C：main が先に進んでいてブランチが古くなった

```bash
# rebase で main に追従する（merge commit を作らない）
git switch feat/add-myservice
git fetch origin
git rebase origin/main

# コンフリクトがあれば解消してから
git rebase --continue
```

---

## やってはいけないこと

| NG 操作 | 理由 |
| --- | --- |
| `main` に直接 push | CI が走らない・レビューを経ない変更がデプロイされる |
| `--force-push` を `main` に実行 | 他者のコミットが消える |
| ブランチを長期間放置する | main との差分が大きくなりコンフリクトが増える |
| PR なしで作業ブランチをマージ | 変更が追跡しにくくなる |

---

## ブランチの寿命

ブランチは**短命**に保ちます。

- 作業開始から PR マージまでを **数日以内** を目安にする
- 長引く場合は定期的に `git rebase origin/main` で main に追従する
- マージ後はブランチを即削除する

---

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

Fork 後は **自分のリポジトリ** として GitHub Flow をそのまま使えます。

```text
upstream/main（元リポジトリ）
       │
       │ 更新を取り込みたいとき
       ▼
origin/main（自分の Fork）
       │
       │ ブランチを切る
       ▼
  feat/add-myservice ──► PR ──► 自分の main にマージ ──► デプロイ
```

```bash
# 元リポジトリの更新を自分の Fork に取り込む
git fetch upstream
git switch main
git merge upstream/main    # または git rebase upstream/main
git push origin main
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

### Branch Protection Rules（`main` ブランチ）

GitHub の `Settings > Branches > Add branch protection rule` で以下を設定します。

| 設定項目 | 値 | 理由 |
| --- | --- | --- |
| Require a pull request before merging | ON | 直接 push を禁止し、必ず PR を経由させる |
| Require status checks to pass | ON（`validate` を選択） | CI が通らない PR はマージ不可 |
| Require branches to be up to date before merging | ON | main と乖離した状態でマージさせない |
| Do not allow bypassing the above settings | ON | 管理者でも例外なしにルールを適用 |
| Allow force pushes | OFF | main の履歴を書き換えさせない |

### Repository 一般設定

`Settings > General` で確認する項目：

| 設定項目 | 推奨値 | 場所 |
| --- | --- | --- |
| Visibility | Public | General > Danger Zone |
| Allow forking | ON（Public リポジトリはデフォルト ON） | General > Features |
| Default branch | `main` | General > Default branch |
| Automatically delete head branches | ON | General > Pull Requests |
| Allow squash merging | ON | General > Pull Requests |
| Allow merge commits | OFF | General > Pull Requests |
| Allow rebase merging | OFF | General > Pull Requests |

> **Pull Requests の squash 以外を OFF にする理由**
> `main` の履歴を「1PR = 1コミット」に保つためです。
> merge commit や複数 rebase コミットが混じると `git log` が読みにくくなります。

---

## 関連ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | コミット規約・コードスタイル・PR チェックリスト |
| [cicd.md](cicd.md) | PR 時の validate・マージ時の自動デプロイの仕組み |
