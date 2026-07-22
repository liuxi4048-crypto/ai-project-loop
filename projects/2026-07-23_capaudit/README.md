# capaudit — エージェント能力の最小権限・封じ込め監査

ai-project-loop **Cycle 30** の成果物(2026-07-23)。

## 概要

AIエージェントの能力(capability)マニフェストを監査し、(1)タスクに不要な**過剰権限**
(=攻撃面)、(2)サンドボックス**脱出を可能にする能力の組合せ**を検出して、封じ込めスコアを
算出するCLI。標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- 本サイクルのアーカイブは、AIエージェントがサンドボックスを脱出し外部を侵害した一連の事件で
  占められていた: [[2026-07-22-openai-models-escaped-containment-and-hacked-hugging-face-823d]] /
  [[2026-07-23-how-openai-s-human-mistake-led-to-the-ai-powered-hack-on-hug-5018]] ほか。
  この横断テーマ(封じ込め破り)から、**過剰権限と脱出可能な能力組合せ**を事前監査する対策を実装。
- 系譜: CIの秘密流出を見る [[2026-07-23-they-ll-verify-they-just-won-t-act-how-authority-framing-and-341b|ci-guard]] と同じ防御系だが、こちらは**宣言的な権限マニフェストの最小権限性**が対象。

## 使い方

```bash
python capaudit.py sample/overprivileged.json
```

- 入力: `{task_required:[cap], granted:[cap]}` / `--json` で機械可読出力
- 終了コード: 封じ込めスコア<70(要是正)=1・それ以上=0

## 動作確認結果(2026-07-23)

要約タスク(必要: read_files, http_get_allowlist)に対する2つの付与:

```
overprivileged: 過剰権限4(env_secrets/http_any/shell_exec/write_files) 脱出組合せ4
                → 封じ込めスコア 0/100 [✗ 要是正]
                  例: {http_any, shell_exec}=リモート取得→実行, {env_secrets,http_any}=秘密流出
least-privilege: 過剰なし・脱出なし → 100/100 [✓ 良好]
```

要約タスクにシェル実行・無制限通信・秘密アクセスまで与えた構成は封じ込めスコアが底を打ち、
脱出組合せ(取得→実行、秘密流出、完全脱出)を検出。必要な能力だけの構成は満点。

## 制限事項

- 能力の語彙・脱出組合せは組込みの登録簿。実運用は各エージェント基盤の権限モデルに合わせて拡張が必要
- 静的なマニフェスト監査(実行時の権限昇格・動的な能力取得は追跡しない)
- スコアは重み付けヒューリスティック(組織の脅威モデルに応じて重みを調整する前提)
