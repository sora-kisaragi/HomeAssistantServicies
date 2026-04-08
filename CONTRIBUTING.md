# Contributing to HomeAssistantServicies

## 開発の始め方

> **このリポジトリへの直接 push 権限はオーナーのみです。**  
> 自分のサーバーで使いたい場合・バグ修正や改善を提案したい場合は、まず **Fork** してください。  
> Fork の手順は [docs/git-workflow.md](docs/git-workflow.md#fork-して使う) を参照してください。

```bash
# Fork 済みの場合
git clone https://github.com/<your-username>/HomeAssistantServicies
cd HomeAssistantServicies
cp .env.example .env

# pre-commit フックをインストール（初回のみ）
make setup-dev
```

以後、`git commit` 時に lint・format が自動で走ります。手動で全ファイルに実行したい場合は：

```bash
make lint
```

PR を出す前に `make validate` でローカル検証してください。

## コントリビューションの種類

### 新しいサービスの追加（最も一般的）

```bash
make add-service NAME=myservice PORT=8090
```

生成された以下のファイルを編集してから PR を作成します：

| ファイル                             | 編集内容                                       |
| ------------------------------------ | ---------------------------------------------- |
| `services/<name>/docker-compose.yml` | `image` を設定、`homeassistant.*` ラベルを付与 |
| `services/<name>/manifest.json`      | `display_name`・`tags`・`health_check` を記入  |
| `services/<name>/.env.example`       | 必要な環境変数を記載（実値は不要）             |
| `services/<name>/README.md`          | サービスの説明・用途を記述                     |
| `PORTS.md`                           | 使用するポートを追記                           |

### バグ修正・改善

- Issue を作成してから PR を出すことを推奨しますが、軽微な修正は直接 PR でも構いません。

- `discovery-api` の変更は `make validate` に加えて手動での動作確認もお願いします。

## コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/) に従います：

```text
feat: 新しいサービス (searxng) を追加
fix: discovery-api のヘルスチェック timeout を修正
docs: README にセットアップ手順を追記
chore: 依存パッケージをアップデート
ci: validate ワークフローに hadolint を追加
```

## コードスタイル

### Python (`discovery-api/`)

- [PEP 8](https://pep8.org/) 準拠、インデントはスペース 4 つ、1 行 100 文字以内
- **ruff** で lint + format（設定は [pyproject.toml](./pyproject.toml)）
- pre-commit が `git commit` 時に自動で `ruff --fix` と `ruff-format` を実行する

### Dockerfile

- [hadolint](https://github.com/hadolint/hadolint) のチェックに通ること
  - `DL3008`・`DL3009`（apt-get バージョン固定警告）は ignore 済み
- ベースイメージは `slim` 系を使用してイメージサイズを抑える

### Shell スクリプト

- `#!/usr/bin/env bash` で始める
- `set -euo pipefail` を先頭に入れる
- インデントはスペース 2 つ

### YAML / JSON

- インデントはスペース 2 つ
- JSON はトレイリングカンマなし

## PR チェックリスト

- [ ] `make lint` が通る（pre-commit で確認済み）
- [ ] `make validate` がローカルで通る
- [ ] `PORTS.md` にポートを追記した（サービス追加の場合）
- [ ] `.env.example` に実値が含まれていない
- [ ] 秘密情報（パスワード・トークン）がコードに含まれていない

## ライセンス

このリポジトリへのコントリビューションは [MIT License](./LICENSE) の下で提供されます。
