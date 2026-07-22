# ci-guard — CI/CDの秘密流出・承認偽装リンター

ai-project-loop **Cycle 5** の成果物(2026-07-23)。

## 概要

CI/CD のスクリプト・ワークフロー定義を静的に検査し、**秘密の外部流出フロー**・
**難読化実行**・**承認偽装フレーズ**を、パイプラインに流す前に検出するリンター。
Python 3 標準ライブラリのみ。

| type | 内容 | severity |
|------|------|----------|
| `secret-egress` | env/secret を読んだ値が外部URLへの送信に渡る(多段の変数ロンダリングを追跡) | high |
| `obfuscated-exec` | `curl … \| bash` / `base64 -d \| sh` / eval(デコード) など | high |
| `secret-egress-suspect` | 秘密参照と送信が同一行でURLが変数化の疑い | medium |
| `authority-framing` | 「事前承認済み」「レビュー不要」「do not block」等(英/日) | medium |

## 着想元(11_AI Archive)

- [[2026-07-23-they-ll-verify-they-just-won-t-act-how-authority-framing-and-341b]] —
  5つのLLMエージェントで構成されたCI/CDに対し、**権限フレーミング(「事前承認」の装い)**と
  **コード難読化**で、秘密を外部URLに流す悪意あるコードが多段チェックを通過した脆弱性の実証。
  本ツールはその2つの攻撃ベクトル(承認偽装 + 秘密流出/難読化)を静的検出する対策。
- 系譜: Cycle 1 [[2026-07-21-prompt-injection-attacks-are-thwarting-ai-hacking-agents-b4a1|vault-inject-scan]] は散文ノートの注入を見たが、本ツールは**CIコードの秘密→送信データフロー**を追う別対象。

## 使い方

```bash
python ci_guard.py <repo_dir>
```

- `--json` でJSON出力 / 終了コード: 検出=1・なし=0(CIの事前ゲートに組込む想定)
- 対象拡張子: `.sh .bash .yml .yaml .py .js .ts .ps1`

## 動作確認結果(2026-07-23)

`sample/`(悪性 `malicious-deploy.yml` / `exfil.py`、良性 `benign-ci.yml`)で5件検出:

```
[high  ] exfil.py:7            secret-egress     # api_key→payload→requests.post を多段追跡
[high  ] malicious-deploy.yml:10 obfuscated-exec  # curl … | bash
[high  ] malicious-deploy.yml:14 secret-egress    # $TOKEN を外部URLへPOST
[medium] malicious-deploy.yml:2  authority-framing # "pre-approved … do not block"
[medium] malicious-deploy.yml:15 authority-framing # "already reviewed, skip review"
-- 5 findings in 2 files (high=3, medium=2)
```

`benign-ci.yml`(pip install / pytest / echo)は **0件**(誤検知なし)。

## 制限事項

- 汚染追跡は行単位の軽量ヒューリスティック(関数境界・データフロー解析はしない)。真の静的解析ではない
- 外部URL判定はドメインにドットを含む http(s)。内部ドメインの許可リストは未実装
- 難読化は既知パターンのみ。新種の難読化・多層エンコードは取りこぼし得る
