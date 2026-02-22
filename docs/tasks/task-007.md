# Task-007: Banzuke パース

**Phase**: 2（パース層）
**依存**: task-003
**ブロック**: task-009

## 概要

Banzuke.aspx のHTMLをパースし、場所×力士の四股名ディメンションを生成する。

## やること

- `src/sumodata/parse_banzuke.py` を実装
  - `parse_banzuke_page(html: str, basho: str, source_url: str) -> list[ShikonaRecord]`
  - 力士リンクから rid を抽出
  - `title` 属性の先頭フィールド（日本語四股名）を `shikona_at_basho` として抽出
    - title属性が取得できない場合はリンクテキスト（ローマ字）にフォールバック
  - 可能なら division, rank も抽出
  - source_url を記録（呼び出し側から `source_url` を引数で受け取る）
- `src/sumodata/models.py` に `ShikonaRecord` dataclass を定義

## 受入条件

- 固定HTMLフィクスチャに対して、期待通りのShikonaRecordリストが生成される
- rid と日本語四股名が正しくペアリングされる（title属性から取得）
- 全力士（幕内〜序ノ口）が取得される

## 参照

- docs/spec.md Section 6.2, 8.3-B
- docs/technical-spec.md（Banzukeページ解析仕様）
