# Task-006: Playoff検出・取得・パース

**Phase**: 2（パース層）
**依存**: task-005
**ブロック**: task-009

## 概要

Resultsページからplayoff（優勝決定戦）の導線を検出し、取得・パースする。

## やること

- Resultsページ内のplayoff導線リンクを検出するロジック
- playoff用のevent_id生成: `honbasho-YYYYMM-playoff`
- パース結果のマッピング:
  - event_type = `honbasho_playoff`
  - is_regular = F
  - day = 16（固定）
- `--playoff off` の場合はスキップ
- 導線が見つからない場合もスキップ（警告ログのみ）

## 受入条件

- playoffが存在する場所のHTMLでplayoff取組が取得される
- event_id, event_type, is_regular, day が正しく設定される
- playoffがない場所ではスキップされ、エラーにならない

## 参照

- docs/spec.md Section 8.1, 8.3-A
- docs/technical-spec.md（Playoff検出ロジック）
