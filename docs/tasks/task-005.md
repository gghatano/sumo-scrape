# Task-005: Results パース

**Phase**: 2（パース層）
**依存**: task-003
**ブロック**: task-006, task-008, task-009

## 概要

Results.aspx のHTMLをパースし、取組データを構造化する。Phase 2の中核タスク。

## やること

- `src/sumodata/parse_results.py` を実装
  - `parse_results_page(html: str, event_id: str, event_type: str, is_regular: str, basho: str, day: int, source_url: str, fetched_at: str) -> list[BoutRecord]`
  - division認識（Makuuchi, Juryo, ...）: HTMLのセクション見出しから判定
  - 各取組行から以下を抽出:
    - east_rid / west_rid: `Rikishi.aspx?r=XXX` のリンクから
    - winner_side: 勝敗記号（○●等）から "E" / "W" / ""
    - kimarite: 決まり手テキスト
    - east_rank / west_rank: 番付テキスト
  - bout_no: division内の出現順で1から採番
  - **メタ列の責務**: パーサーが以下を埋める
    - `event_id`, `event_type`, `is_regular`, `basho`, `day`: 引数からそのまま設定
    - `source_url`: 引数から設定
    - `source_row_index`: ページ内の取組行通し番号（division をまたいで1から連番。bout_no とは異なる）
    - `fetched_at`: 呼び出し側（cli.py/fetch層）がHTTP取得時刻を記録し、引数として渡す
    - `result_type`, `note`: パース結果に基づき判定（task-008で詳細化）
- `src/sumodata/models.py` に `BoutRecord` dataclass を定義

## 受入条件

- 固定HTMLフィクスチャに対して、期待通りのBoutRecordリストが生成される
- rid が正しく抽出される
- division境界でbout_noがリセットされる

## 参照

- docs/spec.md Section 6.1, 8.3-A
- docs/technical-spec.md（Resultsページ解析仕様）
