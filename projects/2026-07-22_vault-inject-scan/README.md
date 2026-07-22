# vault-inject-scan — Markdownノートのプロンプトインジェクション検査器

ai-project-loop **Cycle 1** の成果物(2026-07-22)。

## 概要

Obsidian vault のように「外部由来テキスト(RSS/Web)が毎日流れ込み、AIエージェントが
それを読む」環境で、ノートに仕込まれた指示文・隠しテキストを静的に検出するCLI。
Python 3 標準ライブラリのみ。

検出対象:

| type | 内容 | severity |
|------|------|----------|
| `instruction-like` | エージェントへの命令を装う文言(英/日) | medium〜high |
| `hidden-comment-instruction` | HTMLコメント内の命令文(人間に見えない層) | high |
| `hidden-char` | ゼロ幅文字・RTL/LTR制御文字 | medium |
| `base64-text` | 自然言語に復号できる長いbase64塊 | medium |
| `reserved-filename` | `claude.md` `gemini.md` 等、エージェントが指示ファイルとして読む予約名 | high |

## 着想元(11_AI Archive)

- [[2026-07-21-prompt-injection-attacks-are-thwarting-ai-hacking-agents-b4a1]] — 「コンテキスト爆弾」でエージェントを停止させる攻撃の報告。注入は攻撃にも防御にも使われる現実
- 実体験: [[entity-note-shadowed-claude-md]] — RSS由来の `claude.md` が指示ファイルとして読み込まれた事件。本ツールの `reserved-filename` 検査はその一般化

## 使い方

```bash
python scanner.py <scan_root>
```

```bash
python scanner.py "C:\Users\PC_User\ObsidianVault\11_AI Archive" --min-severity medium
```

- `--json` でJSON出力、`--min-severity {low,medium,high}` で絞り込み
- 終了コード: 検出あり=1 / なし=0(フック・CI組込み用)

## 動作確認結果(2026-07-22)

- `sample/` の植え込みデータ: 6種すべて検出(instruction英/日・ゼロ幅文字・隠しコメント・base64・予約名)
- 実データ `11_AI Archive`(386ノート): **1件検出** — `Entities\Models\gemini.md` が予約名。
  ai-collect の予約名ガードの穴として別タスク化済み

## 制限事項

- パターンベースのため言い換え・多言語(英日以外)の注入は検出しない
- base64判定はASCII自然言語のみ(圧縮・暗号化ペイロードは対象外)
- `sample/claude.md` は検出テスト用の意図的な予約名ファイル(中身は無害)
