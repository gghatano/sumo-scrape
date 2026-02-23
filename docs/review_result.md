# 全体レビュー結果（2026-02-23）

## Findings

1. **Low** `is_regular` の型表現がドキュメント間で不一致  
`docs/spec.md:116` では `is_regular : bool（T/F）`、`docs/technical-spec.md:48` では `is_regular: str  # "T" / "F"` となっている。  
実装時の型設計（`bool` で保持してCSV出力時に `T/F` へ変換するのか、最初から `str` で持つのか）を明確に統一した方がよい。

2. **Low** `winner_side` 判定根拠の表現が task と技術仕様でずれる  
`docs/tasks/task-005.md:18` は「勝敗記号（○●等）から判定」、`docs/technical-spec.md:158` は「`img src` で判定」と記載。  
実装指針としては `img src` 判定を正とし、task 側も同じ表現にそろえると誤解が減る。

## 参考（確認済み）

- `monthly.yml` の差分判定順は `git add` → `git diff --cached --quiet` に修正済み（`docs/spec.md:454`, `docs/spec.md:456`）。  
- 四股名抽出ルールは「title属性先頭の日本語、欠損時のみローマ字フォールバック」に統一済み（`docs/tasks/task-007.md:16`, `docs/technical-spec.md:358`）。  
- `parse_results_page` の契約（`fetched_at` 含む）とメタ列責務は整備済み（`docs/tasks/task-005.md:14`, `docs/technical-spec.md:216`）。

## 補足

レビュー対象は `docs/` の仕様・タスク定義。  
実装コードは未レビューのため、実行時挙動は別途テストで確認が必要。
