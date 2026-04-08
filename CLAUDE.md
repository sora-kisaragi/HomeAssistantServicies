# CLAUDE.md — Claude Code 動作指針

このリポジトリで Claude Code が自律的に従うべき規約・作業スタイルを記述します。

---

## コミットの方針（自動）

まとまった変更が完了したら、**依頼されなくても** 適切な粒度でコミットする。

- **粒度の基準**：1 コミット = 1 つの論理的な変更（バグ修正、機能追加、ドキュメント更新など）
- **メッセージ形式**：Conventional Commits（英語）

  | プレフィックス | 用途 |
  | --- | --- |
  | `feat:` | 新機能 |
  | `fix:` | バグ修正 |
  | `docs:` | ドキュメント変更 |
  | `chore:` | 設定・ツール・ビルド |
  | `refactor:` | リファクタリング |

- **必須**：`git commit` は常に `PYTHONUTF8=1` を前置する（後述）
- **Co-Author 行を付ける**：

  ```text
  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  ```

---

## PR の方針（自動）

一連の作業が完了したタイミングで、**依頼されなくても** push して PR を作成する。

- **ベースブランチ**：`main`
- **PR タイトル**：Conventional Commits 形式（英語）
- **PR 本文テンプレート**：

```markdown
## Summary
- 変更内容の箇条書き

## Test plan
- [ ] 確認事項

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## 環境固有の注意事項

### Windows 日本語ロケール（cp932）対応

pre-commit の yamllint が日本語コメント入り YAML を cp932 で読もうとして失敗する。
**`git commit` は必ず `PYTHONUTF8=1` を前置すること。**

```bash
# 正しい例
PYTHONUTF8=1 git commit -m "..."

# git add / git push は通常通りでよい
git add <files>
git push
```

---

## プロジェクト規約

### ブランチ命名

```text
feat/<topic>   — 新機能
fix/<topic>    — バグ修正
docs/<topic>   — ドキュメント
chore/<topic>  — 設定・ツール
```

### デプロイ

- self-hosted runner は **使用しない**
- `main` マージ後はサーバーで手動実行：

```bash
cd /opt/homeassistant
git pull origin main
bash scripts/deploy.sh
```

### Markdown 記述ルール

- 段落（文章の塊）の間は必ず**空行を1行**入れる
- コードブロックには必ず言語を指定する（`bash`, `text`, `json` など）
- 見出し（`###`）の直後に `**太字**` だけの行を置かない（MD036違反）
- 見出しの前後は必ず空行を入れる
- `pre-commit` の `markdownlint` が自動チェックする（`.markdownlint.yml` 参照）

### 言語使い分け

| 対象 | 言語 |
| --- | --- |
| ユーザーとの会話 | 日本語 |
| コード・変数名 | 英語 |
| コミットメッセージ・PR タイトル | 英語 |
| ドキュメント（`.md`） | 日本語 |
