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
| 3 | 2026-07-23 | [false-friend-finder](projects/2026-07-22_false-friend-finder/) | 多言語語彙のクロスリンガル・ホモグラフ(偽の友)検出器。トークナイザ論文の診断器 |
| 4 | 2026-07-23 | [conformal-coverage](projects/2026-07-23_conformal-coverage/) | 分割共形予測のクラス別カバレッジ崩壊デモ(依存ゼロ)。ラベル複雑性論文の教材 |
| 5 | 2026-07-23 | [ci-guard](projects/2026-07-23_ci-guard/) | CI/CDの秘密流出・難読化・承認偽装リンター。エージェント型CI/CD攻撃論文の対策 |
| 6 | 2026-07-23 | [copyrate](projects/2026-07-23_copyrate/) | 推論トレースの逐語コピー率(copy-rate)計測器。反復コピー論文の診断器 |
| 7 | 2026-07-23 | [stepcheck](projects/2026-07-23_stepcheck/) | 推論チェーンのステップ整合性リンター(KB照合でハルシネーション検出)。ステップ自己整合性論文 |
| 8 | 2026-07-23 | [shapley-paths](projects/2026-07-23_shapley-paths/) | 並列推論パスのShapley値報酬帰属(貢献者/フリーライダー識別)。Parallel Shapley論文 |
| 9 | 2026-07-23 | [route-sim](projects/2026-07-23_route-sim/) | エージェント回復ルーティング3方策の固定予算比較シミュレータ。CodeRescue論文 |
| 10 | 2026-07-23 | [rubric-score](projects/2026-07-23_rubric-score/) | 宣言的ルーブリックのエッセイ採点+フィードバック生成。RLAES(エッセイ採点)論文 |
| 11 | 2026-07-23 | [biaslens](projects/2026-07-23_biaslens/) | ニュース文のバイアス検出+中立化(loaded language→中立表現)。AutoJourn論文 |
| 12 | 2026-07-23 | [promptlint](projects/2026-07-23_promptlint/) | プロンプトの指示遵守/ハルシネーション リスクリンター(3因子)。Prompt Design at Scale論文 |
