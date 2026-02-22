# Task-003: HTTP fetch + リトライ + sleep + User-Agent

**Phase**: 1（取得層）
**依存**: task-001
**ブロック**: task-004, task-005, task-007

## 概要

SumoDBへのHTTPリクエスト基盤を実装する。リトライ、レート制御、User-Agent明示を含む。

## やること

- `src/sumodata/fetch.py` に HTTP取得関数を実装
  - `fetch_page(url: str) -> str` （HTML文字列を返す）
  - リトライ: 最大3回、指数バックオフ（1s, 2s, 4s）
  - ページ間sleep: 0.5〜1.5秒ランダム
  - User-Agent: `sumodata/0.1 (+https://github.com/<owner>/sumo_scrape)`
  - HTTP ステータス != 200 でリトライ、最終失敗で例外
- URL組み立てヘルパー
  - `results_url(basho: str, day: int) -> str`
  - `banzuke_url(basho: str) -> str`
  - `rikishi_url(rid: int) -> str`

## 受入条件

- 正常なURLに対してHTML文字列が返る
- HTTP 500等でリトライが行われ、最終失敗で例外が発生する
- ログにURL、ステータスコード、リトライ回数が記録される

## 参照

- docs/spec.md Section 5.3, 8.2
- docs/technical-spec.md（HTTPクライアント設計）
