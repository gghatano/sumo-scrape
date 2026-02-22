# Task-010: upsert / replace（更新ルール）

**Phase**: 3（出力層）
**依存**: task-009
**ブロック**: task-012, task-013

## 概要

既存CSVに対するupsertおよびforce時の完全置換ロジックを実装する。

## やること

- `src/sumodata/io_csv.py` に更新ロジックを追加
  - `update_fact_csv(new_records, path, force: bool, event_id: str)`
  - `update_dim_shikona_csv(new_records, path, force: bool, basho: str)`
- `--force` 指定時:
  - fact: 対象event_idの行を全削除 → 新規分で置換
  - dim: 対象bashoの行を全削除 → 新規分で置換
- `--force` なし（upsert）:
  - fact: キー `(event_id, day, division, bout_no)` で既存行を上書き/追加
  - dim: キー `(basho, rid)` で既存行を上書き/追加
- ソート順の維持:
  - fact: `event_id, day, division, bout_no`
  - dim: `basho, rid`

## 受入条件

- force時に対象event_idの行のみが置換され、他event_idの行は影響を受けない
- upsert時に既存キーの行が正しく更新される
- 出力CSVが指定のソート順で出力される

## 参照

- docs/spec.md Section 9
- docs/technical-spec.md（更新ルール詳細）
