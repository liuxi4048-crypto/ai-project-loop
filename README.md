# ai-project-loop

Obsidian vault の `11_AI Archive/`(AIニュースアーカイブ)を情報源に、
プロジェクトを構想して**動くプロトタイプまで実装する**自律ループシステム。

## 仕組み

1サイクル = 情報取得 → 構想(候補3件→批評→1件選定) → 実装+動作確認 → 記録+push

- ワークフロー定義: `~/.claude/skills/ai-project-loop/SKILL.md`
- 情報源: `C:\Users\PC_User\ObsidianVault\11_AI Archive\`(読み取り専用)
- 成果物: `projects/YYYY-MM-DD_<slug>/` に1サイクル1フォルダで蓄積
- 使用済み情報の管理: `state/used_sources.json`(同じトピックノートを二度使わない)

## 起動方法

- **セッション内ループ**: Claude Code で「プロジェクトループ開始」→ ScheduleWakeup で連続実行。「止めて」で停止
- **1サイクルだけ**: `/ai-project-loop 1サイクル実行`
- **定期実行**: Windowsタスク `AiProjectLoop`(毎日09:00、`~/.claude/scripts/Invoke-AiProjectLoop.ps1`)。
  時刻変更は `schtasks /Change /TN AiProjectLoop /ST HH:MM`。ログは `~/.claude/logs/ai-project-loop.log`

## プロジェクト索引

| # | 日付 | プロジェクト | 概要 |
|---|------|--------------|------|
| 1 | 2026-07-22 | [vault-inject-scan](projects/2026-07-22_vault-inject-scan/) | Markdownノートのプロンプトインジェクション検査CLI。実vaultで予約名ノート1件を検出 |
| 2 | 2026-07-22 | [pareto-sweep](projects/2026-07-22_pareto-sweep/) | 宣言的パラメータ掃引+Pareto分析ランナー(依存ゼロ)。srt-slurm記事のローカル版 |
