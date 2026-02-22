# Task-001: プロジェクト雛形作成

**Phase**: 0（土台）
**依存**: なし
**ブロック**: task-002, task-003 以降すべて

## 概要

pyproject.toml、srcレイアウト、README等のプロジェクト基盤を作成する。

## やること

- `pyproject.toml` 作成（Python 3.12、依存: requests, beautifulsoup4）
- `src/sumodata/` パッケージ作成（`__init__.py`, 各モジュールの空ファイル）
- `data/fact/`, `data/dim/`, `data/raw/` ディレクトリ作成
- `.gitignore` に `data/raw/` を追加
- `README.md` の雛形作成

## 受入条件

- `uv sync` でインストールが通る
- `python -m sumodata` が（エラーメッセージでもよいが）実行できる
- ディレクトリ構成が spec.md Section 12 に準拠している

## 参照

- docs/spec.md Section 12（リポジトリ構成）
- docs/technical-spec.md（技術仕様）
