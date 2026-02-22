# Task-013: GitHub Actions workflow（monthly.yml）

**Phase**: 4（運用）
**依存**: task-010
**ブロック**: なし

## 概要

GitHub Actionsによる月次バッチ自動実行のワークフローを作成する。

## やること

- `.github/workflows/monthly.yml` を作成
  - spec.md Section 13.4 のYAMLをベースに実装（※git add → git diff --cached の順序に修正済み）
  - workflow_dispatch（手動実行）対応
  - schedule（毎月27日 16:30 UTC = 28日 01:30 JST）
  - basho自動算出（本場所月のみ実行）
  - uv sync によるインストール
  - 差分がある場合のみ commit/push
  - concurrency 設定
- permissions: contents: write

## 受入条件

- workflow_dispatch で手動実行でき、basho を指定できる
- 本場所月でない場合はno-op（正常終了）
- 差分がある場合のみコミットが作成される

## 参照

- docs/spec.md Section 13
