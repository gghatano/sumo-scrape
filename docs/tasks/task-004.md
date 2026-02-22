# Task-004: rawキャッシュ保存（ON/OFF）

**Phase**: 1（取得層）
**依存**: task-003
**ブロック**: task-005, task-007

## 概要

取得したHTMLをファイルに保存し、キャッシュヒット時にfetchを省略する機構を実装する。

## やること

- `src/sumodata/fetch.py` にキャッシュ層を追加
  - 保存先: `data/raw/<event_id>/results_d<DD>.html`, `data/raw/<event_id>/banzuke.html` 等
  - `--raw-cache on` の場合: キャッシュファイルが存在すればfetchスキップ
  - `--raw-cache off` の場合: 常にfetch（キャッシュ読み書きしない）
- キャッシュファイルのエンコーディング: UTF-8

## 受入条件

- `--raw-cache on` で実行すると `data/raw/` にHTMLファイルが保存される
- 2回目の実行でHTTP通信が発生しない（キャッシュヒット）
- `--raw-cache off` ではキャッシュを読み書きしない

## 参照

- docs/spec.md Section 5.1, 8.2
- docs/technical-spec.md（キャッシュ設計）
