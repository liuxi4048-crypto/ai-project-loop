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
| 13 | 2026-07-23 | [optmem](projects/2026-07-23_optmem/) | 学習メモリ/オプティマイザ状態プランナ(Tiered割当の削減効果)。SkewAdam論文 |
| 14 | 2026-07-23 | [cot2qa](projects/2026-07-23_cot2qa/) | 推論チェーン→依存関係付き中間QAレコード変換(依存グラフ構築)。DAIS論文 |
| 15 | 2026-07-23 | [splitaudit](projects/2026-07-23_splitaudit/) | 学習データ分割の漏洩監査(random/grouped/temporal)。不正検知汎化ベンチ論文 |
| 16 | 2026-07-23 | [ireval](projects/2026-07-23_ireval/) | BM25検索+情報検索評価(recall@k/MRR/nDCG@k)。AILQA(法律QA評価)論文 |
| 17 | 2026-07-23 | [divmeter](projects/2026-07-23_divmeter/) | 回答多様性メーター(構造化出力の多様性崩壊を定量化)。構造化出力×多様性論文 |
| 18 | 2026-07-23 | [codebench](projects/2026-07-23_codebench/) | 実行型コード生成ベンチマークランナー(I/Oテストでpass@1)。SciCodePile論文 |
| 19 | 2026-07-23 | [feedbackblind](projects/2026-07-23_feedbackblind/) | 「観測のみ検索」のフィードバック盲目性の実証(効用条件付けで解消)。Utility-Augmented Transformer論文 |
| 20 | 2026-07-23 | [watermark](projects/2026-07-23_watermark/) | グリーンリスト統計透かしの埋め込み+z検定検出(鍵依存)。SynthID/AI検出記事 |
| 21 | 2026-07-23 | [detiler](projects/2026-07-23_detiler/) | タイル継ぎ目アーティファクトのスライディング窓平均による低減。SWITi論文 |
| 22 | 2026-07-23 | [specsim](projects/2026-07-23_specsim/) | 投機的デコーディングの高速化見積り(固定γ vs 文脈適応γ)。AdaFlash論文 |
| 23 | 2026-07-23 | [svgsurgeon](projects/2026-07-23_svgsurgeon/) | SVGの外科的編集検証(修復適用+保護対象非破壊)。Vector-Bench論文 |
| 24 | 2026-07-23 | [subjfcast](projects/2026-07-23_subjfcast/) | 被験者条件付け時系列予測 vs 集団モデル(RMSE比較)。SCGP(血糖予測)論文 |
| 25 | 2026-07-23 | [deteval](projects/2026-07-23_deteval/) | 物体検出のmAP評価(IoUマッチ→AP→mAP)。AEC図面レイアウト検出ベンチ論文 |
| 26 | 2026-07-23 | [prf](projects/2026-07-23_prf/) | 擬似関連性フィードバックによるクエリ拡張(語彙不一致を橋渡し)。PLAID-PRF論文 |
| 27 | 2026-07-23 | [argue](projects/2026-07-23_argue/) | 議論の受理計算(grounded extension)+証拠被覆。MIRA-Ev(議論マイニング)論文 |
| 28 | 2026-07-23 | [aiinnov](projects/2026-07-23_aiinnov/) | 商標データによるAIイノベーション指標(比率・成長・セクター拡散)。商標データ論文 |
| 29 | 2026-07-23 | [exposurebias](projects/2026-07-23_exposurebias/) | 教師強制評価が隠す露呈バイアスの実証(TF vs 自己回帰)。EEG-to-Text論文 |
| 30 | 2026-07-23 | [capaudit](projects/2026-07-23_capaudit/) | エージェント能力の最小権限・封じ込め監査(過剰権限+脱出組合せ検出)。サンドボックス脱出事件 |
| 31 | 2026-07-23 | [distrl](projects/2026-07-23_distrl/) | カテゴリカル分布Bellmanバックアップ(分布強化学習、Cramér距離で収束測定)。分布ソフトBellman論文 |
| 32 | 2026-07-23 | [tpmatrix](projects/2026-07-22_tpmatrix/) | 全正/全非負行列の判定+特性多項式係数(厳密有理数)。全正行列と特性多項式論文 |
| 33 | 2026-07-23 | [eventdedup](projects/2026-07-23_eventdedup/) | 同一事件のほぼ重複報道の集約(Jaccard+Union-Find)。アーカイブの冗長性 |
| 34 | 2026-07-23 | [groundcheck](projects/2026-07-23_groundcheck/) | 生成回答の根拠づけ(幻覚)検証(ソース被覆でゲート)。ゼロ幻覚・階層的監視論文 |
| 35 | 2026-07-23 | [staypoint](projects/2026-07-23_staypoint/) | GPS軌跡からの滞在点検出(座標列→意味ある場所)。滞在点検出ベンチ論文 |
| 36 | 2026-07-23 | [sfgate](projects/2026-07-23_sfgate/) | 統計優先ゲーティング(信頼区間で確定/エスカレート)。SFGA論文 |
| 37 | 2026-07-23 | [lqr](projects/2026-07-23_lqr/) | 離散時間LQR最適制御(リッカチ解でフィードバックゲイン合成)。リアルタイム最適制御論文 |
| 38 | 2026-07-23 | [rocket](projects/2026-07-23_rocket/) | ランダム畳み込み特徴による時系列分類(ROCKET系)。ランダム畳み込み時系列分類論文 |
| 39 | 2026-07-23 | [fundflow](projects/2026-07-23_fundflow/) | AI投資・資金調達のディールフロー分析(集中度HHI)。投資ニュースクラスタ |
| 40 | 2026-07-23 | [sdfplan](projects/2026-07-23_sdfplan/) | 符号付き距離関数(SDF)による動作計画(距離を保つ経路)。UAV向けSDF計画論文 |
| 41 | 2026-07-23 | [anthrolint](projects/2026-07-23_anthrolint/) | AI応答の擬人化検出(感情/欲求/関係性/記憶/身体性)+中立化提案。子どもの擬人化論文 |
| 42 | 2026-07-23 | [benchspot](projects/2026-07-23_benchspot/) | ベンチマーク汚染(特定プロンプト過学習)の検出(二元加法残差)。pelicanmaxxing記事 |
| 43 | 2026-07-23 | [sancscreen](projects/2026-07-23_sancscreen/) | 制裁・禁輸ウォッチリスト名寄せスクリーニング(表記ゆれ頑健)。対中制裁・ソブリンAIクラスタ |
| 44 | 2026-07-23 | [capexroi](projects/2026-07-23_capexroi/) | AIインフラ投資のDCF評価(回収期間・NPV・IRR・ROI)。AI投資正当化クラスタ |
| 45 | 2026-07-23 | [mudeval](projects/2026-07-23_mudeval/) | 決定論的テキストMUDによるエージェント行動評価(4次元)。次元の取捨で順位が反転しチートを検出。MUD-LLM評価概念実証 |
| 46 | 2026-07-23 | [cmsketch](projects/2026-07-23_cmsketch/) | Count-Minスケッチによる少メモリ頻度推定(過小評価なし・上位ヒッタ復元)。エッジ/オンザフライ計算 |
| 47 | 2026-07-23 | [conshash](projects/2026-07-23_conshash/) | コンシステントハッシュ(ノード増減時の再マッピング最小化 vs mod)。データセンター/分散サービング |
