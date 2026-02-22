# レビュー結果

## Findings

1. **High** [RESOLVED] `monthly.yml`案の差分判定順が誤っており、初回更新を取りこぼす可能性
`docs/spec.md` で `git diff --quiet` を先に実行し、`git add` が後になっていた。
**対応**: `git add` → `git diff --cached --quiet` の順に修正済み。`task-013.md` にも注記追加済み。

2. **Medium** [RESOLVED] 四股名抽出ルールがタスクと技術仕様で不整合
`task-007.md` が「表示テキストから抽出」、技術仕様が `title` 属性先頭（日本語四股名）を推奨で不一致だった。
**対応**: 「title属性の日本語四股名を使用、取得不可時のみローマ字フォールバック」に統一。task-007.md、technical-spec.md Section 7.4, 7.7 を更新済み。

3. **Medium** [RESOLVED] `Task-005` の関数契約が `BoutRecord` 必須項目と噛み合っていない
`parse_results_page(html, event_id, day)` だけでは `event_type/is_regular/source_url/fetched_at` 等の責務が曖昧だった。
**対応**: 関数シグネチャを `(html, event_id, event_type, is_regular, basho, day, source_url, fetched_at)` に拡張。technical-spec.md に Section 5.10「メタ列の責務分担」を新設し、全フィールドの責務を明文化済み。

## Open Questions / Assumptions

1. [RESOLVED] `shikona_at_basho` → 「日本語優先・欠損時ローマ字フォールバック」で確定。
2. [RESOLVED] `BoutRecord` メタ列 → パーサーが全フィールドを埋める。`fetched_at` は呼び出し側がHTTP取得時刻を記録し引数として渡す。

## 補足

レビュー対象は実装コードではなく `docs/` の仕様・タスク定義。
このディレクトリはGitリポジトリではないため、差分ベースではなくドキュメント整合性レビューを実施。
