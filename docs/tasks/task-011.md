# Task-011: dim_rikishi_current（最新四股名、任意）

**Phase**: 3（出力層）
**依存**: task-003, task-009
**ブロック**: なし

## 概要

力士の最新四股名ディメンションを差分更新する（任意タスク）。

## やること

- `src/sumodata/parse_rikishi.py` を実装
  - `parse_rikishi_page(html: str, rid: int) -> RikishiRecord`
  - Rikishi.aspx から最新四股名を取得
- 差分更新ロジック:
  - 今回の実行で出現したrid一覧を収集
  - dim_rikishi_current.csv に存在しない、または更新対象のridのみfetch
  - `updated_at` をISO形式で記録
- `src/sumodata/models.py` に `RikishiRecord` dataclass を定義

## 受入条件

- 新規ridが正しく追加される
- 既存ridの四股名が変更されていれば更新される
- 未変更のridはfetchされない（最小リクエスト）

## 参照

- docs/spec.md Section 6.3, 8.3-C
- docs/technical-spec.md
