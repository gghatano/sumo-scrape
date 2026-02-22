# Task-014: 単体テスト

**Phase**: 5（品質）
**依存**: task-005, task-007, task-010
**ブロック**: なし

## 概要

各パーサーとCSV操作の単体テストを作成する。固定HTMLフィクスチャによる回帰テスト。

## やること

- `tests/` ディレクトリ作成
- テストフィクスチャ:
  - `tests/fixtures/` にResults, Banzukeの固定HTML
  - 実際のSumoDBからダウンロードして固定化
- テストケース:
  - `test_parse_results.py`: division認識、rid抽出、winner_side、kimarite、bout_no
  - `test_parse_banzuke.py`: rid、四股名、division/rank
  - `test_io_csv.py`: write、upsert、force置換
  - `test_fetch.py`: URL組み立て（HTTP通信はmock）
  - `test_exceptions.py`: fusen、kyujo、unknown行
- pytest 設定を pyproject.toml に追加

## 受入条件

- `pytest` で全テストがpassする
- パーサーのロジック変更時に回帰が検出できる
- テストカバレッジがパース層で80%以上

## 参照

- docs/spec.md Section 14-Phase 5
