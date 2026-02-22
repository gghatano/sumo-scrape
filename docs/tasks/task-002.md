# Task-002: CLI骨格の実装

**Phase**: 0（土台）
**依存**: task-001
**ブロック**: task-003, task-009

## 概要

argparse によるCLI引数処理、ログ設定、終了コードの基盤を実装する。

## やること

- `src/sumodata/__main__.py` に `python -m sumodata` のエントリポイント作成
- `src/sumodata/cli.py` に引数パーサー実装
  - `--basho YYYYMM`（必須）
  - `--force`（フラグ）
  - `--raw-cache on/off`（デフォルト: on）
  - `--playoff on/off`（デフォルト: on）
  - `--log-level INFO/DEBUG`（デフォルト: INFO）
- logging設定（フォーマット: `%(asctime)s %(levelname)s %(name)s %(message)s`）
- 正常終了=0、エラー=1 の終了コード制御

## 受入条件

- `python -m sumodata --basho 202601` で正常起動しログ出力される
- `--help` でオプション一覧が表示される
- 不正入力時にエラーメッセージと終了コード1

## 参照

- docs/spec.md Section 7, 11
- docs/technical-spec.md
