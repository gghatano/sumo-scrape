# Task-009: CSV writer（UTF-8, LF）

**Phase**: 3（出力層）
**依存**: task-002, task-005, task-007
**ブロック**: task-010

## 概要

パース結果をCSVファイルに書き出す基盤を実装する。

## やること

- `src/sumodata/io_csv.py` を実装
  - `write_fact_csv(records: list[BoutRecord], path: Path)`
  - `write_dim_shikona_csv(records: list[ShikonaRecord], path: Path)`
  - ヘッダ付き、UTF-8、改行LF
  - fact_bout_daily.csv: spec Section 6.1 のカラム順
  - dim_shikona_by_basho.csv: spec Section 6.2 のカラム順

## 受入条件

- 生成されたCSVがUTF-8, LFで出力される
- ヘッダ行がスキーマ定義と一致する
- 空のリストを渡してもヘッダのみのCSVが生成される

## 参照

- docs/spec.md Section 3, 6, 8.4
- docs/technical-spec.md（CSV出力仕様）
