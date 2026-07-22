# argue — 議論の受理計算(grounded extension)+証拠被覆

ai-project-loop **Cycle 27** の成果物(2026-07-23)。

## 概要

主張(claim)と前提(premise)が支持/攻撃で結ばれた議論グラフから、**どの主張が正当化されるか**を
Dung の抽象議論フレームワークの **grounded 意味論**で計算するCLI。特性関数
`F(S)={a: a の全攻撃者が S に攻撃される}` を空集合から反復し最小不動点(=grounded extension)を
求め、各引数を受理(IN)/却下(OUT)/未決(UNDEC)に分類。さらに受理された主張が受理された
前提に支持されているか(証拠被覆)を検査する。標準ライブラリのみ・決定論的。

## 着想元(11_AI Archive)

- [[2026-07-23-mira-ev-a-benchmark-for-granular-evidence-detection-and-rela-7f07]] —
  臨床試験問題で、スパン単位の**前提・主張・支持/攻撃関係**を再アノテートした議論マイニング
  (argument mining)ベンチ MIRA-Ev。本ツールはその関係構造から「何が正当化されるか」を
  形式的議論論で計算する推論器。

## 使い方

```bash
python argue.py sample/clinical.json
```

- 入力: `{arguments:[{id,type}], attacks:[[x,y]], supports:[[p,c]]}`(x が y を攻撃, p が c を支持)
- `--json` で機械可読出力

## 動作確認結果(2026-07-23)

臨床風の議論(診断A/B が排他的に攻撃、前提 ev3 が診断B に反証):

```
  [✓ 受理] dxA (claim)     [✗ 却下] dxB (claim)
  [✓ 受理] ev1/ev2/ev3 (premise)
受理された主張の証拠被覆:  ✓ 根拠あり: dxA ← ev1
-- 受理 4 / 却下 1 / 未決 0
```

反証 ev3 が診断B を却下し、B に倒されなくなった診断A が受理され、A は受理された前提 ev1 に
支持される。grounded 意味論による正当化と証拠被覆を正しく計算できている
(ある主張を支える前提を消すと、証拠被覆は「⚠ 根拠なし」に変わる)。

## 制限事項

- grounded(最も慎重な単一)意味論のみ。preferred/stable など複数拡張の列挙は未実装
- 支持関係は「証拠被覆の overlay」として扱い、双極議論(bipolar)の支持伝播は簡略
- スパン抽出・関係のアノテーションは所与(自然文からの argument mining 本体は含まない)
