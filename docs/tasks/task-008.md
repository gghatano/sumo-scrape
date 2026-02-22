# Task-008: 例外行の取り扱い（fusen/kyujo/unknown）

**Phase**: 2（パース層）
**依存**: task-005
**ブロック**: task-009

## 概要

不戦勝・休場・その他の例外的な取組行を適切に分類・格納する。

## やること

- parse_results 内の例外行判定ロジック:
  - 不戦勝（fusen）: 「fusensho」「fusenpai」等のキーワード
  - 休場（kyujo）: 「kyujo」等のキーワード
  - 判定不能: unknown
- result_type フィールドへの分類:
  - `normal` / `fusen` / `kyujo` / `playoff` / `unknown`
- winner_side: 不戦勝は勝者あり、休場は "" 等
- kimarite: 不戦は "fusen"、休場は ""
- note フィールドに補足情報

## 受入条件

- 不戦勝の取組が result_type=fusen として正しく記録される
- 休場が result_type=kyujo として記録される
- 判定不能な行が unknown として記録され、ジョブが停止しない

## 参照

- docs/spec.md Section 8.3-A, 10
- docs/technical-spec.md（例外行パターン）
