# SumoDB Scraping & CSV Generation

SumoDB（sumodb.sumogames.de）から大相撲の取組データをスクレイピングし、力士ID（rid）で名寄せされた分析用CSVを生成・更新するツール。

## リポジトリ構成

```
sumo_scrape/
├── src/sumodata/
│   ├── __init__.py          # バージョン定義
│   ├── __main__.py          # python -m sumodata エントリポイント
│   ├── cli.py               # 引数パース、メイン処理フロー
│   ├── fetch.py             # HTTP取得、リトライ、キャッシュ
│   ├── parse_results.py     # Results.aspx パーサー
│   ├── parse_banzuke.py     # Banzuke.aspx パーサー
│   ├── parse_rikishi.py     # Rikishi.aspx パーサー
│   ├── io_csv.py            # CSV読み書き、upsert/replace
│   ├── models.py            # dataclass定義
│   └── util.py              # 共通ユーティリティ
├── data/
│   ├── fact/
│   │   └── fact_bout_daily.csv       # 取組ファクトテーブル
│   ├── dim/
│   │   └── dim_shikona_by_basho.csv  # 四股名ディメンションテーブル
│   └── raw/                          # HTMLキャッシュ（.gitignore）
├── tests/                   # pytest テスト
├── scripts/
│   └── run_local.sh         # ローカル実行ヘルパー
├── .github/workflows/
│   └── monthly.yml          # GitHub Actions 月次バッチ
├── docs/
│   ├── spec.md              # 仕様書
│   └── technical-spec.md    # 技術仕様書
└── pyproject.toml
```

## クイックスタート

### 前提条件

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)

### インストール

```bash
uv sync
```

### 実行

```bash
uv run python -m sumodata --basho 202501
```

### 出力確認

実行後、以下のCSVファイルが生成・更新されます。

```bash
# 取組データ
head data/fact/fact_bout_daily.csv

# 四股名データ
head data/dim/dim_shikona_by_basho.csv
```

## CLIオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--basho YYYYMM` | 対象場所（YYYYMM形式、必須） | -- |
| `--force` | 対象イベントの行を完全置換（upsertではなくreplace） | off |
| `--raw-cache on\|off` | HTMLキャッシュモード | `on` |
| `--playoff on\|off` | 優勝決定戦の検出・取得 | `on` |
| `--log-level INFO\|DEBUG` | ログレベル | `INFO` |

## 出力CSV

### `data/fact/fact_bout_daily.csv` — 取組ファクトテーブル

日別の全取組記録。力士はrid（力士ID）で名寄せ済み。

| カラム | 型 | 説明 |
|---|---|---|
| `event_id` | string | イベントID（例: `honbasho-202501`） |
| `event_type` | string | イベント種別（`honbasho_regular` / `honbasho_playoff`） |
| `is_regular` | string | 本場所通常日程なら `T`、それ以外は `F` |
| `basho` | string | 場所（YYYYMM） |
| `day` | int | 日目（1〜15、playoff=16） |
| `division` | string | 階級（Makuuchi, Juryo, ...） |
| `bout_no` | int | division内の取組番号 |
| `east_rid` | int | 東方の力士ID |
| `west_rid` | int | 西方の力士ID |
| `winner_side` | string | 勝者（`E` / `W` / 空） |
| `kimarite` | string | 決まり手 |
| `east_rank` | string | 東方の番付（例: `Y1e`） |
| `west_rank` | string | 西方の番付 |
| `result_type` | string | 結果種別（`normal` / `fusen` / `kyujo` / `playoff` / `unknown`） |
| `note` | string | 備考 |
| `source_url` | string | 取得元URL |
| `source_row_index` | int | ページ内行番号 |
| `fetched_at` | string | 取得日時（ISO形式） |

一意キー: `(event_id, day, division, bout_no)`

### `data/dim/dim_shikona_by_basho.csv` — 四股名ディメンションテーブル

場所ごとの力士四股名。番付ページから取得した日本語四股名を使用。

| カラム | 型 | 説明 |
|---|---|---|
| `basho` | string | 場所（YYYYMM） |
| `rid` | int | 力士ID |
| `shikona_at_basho` | string | 当該場所時点の四股名 |
| `source_url` | string | 取得元URL |
| `division` | string | 階級 |
| `rank` | string | 番付 |

一意キー: `(basho, rid)`

## 過去データの一括取得

2000年〜2024年の本場所データを一括取得するヘルパースクリプト:

```bash
./scripts/run_local.sh historical
```

詳細は `scripts/run_local.sh` を参照。

## GitHub Actions による自動実行

`.github/workflows/monthly.yml` により、毎月27日（UTC）に自動実行されます。本場所月（1/3/5/7/9/11月）のみデータ取得を行い、差分がある場合にコミット・プッシュします。

手動実行（`workflow_dispatch`）にも対応しており、任意の場所を指定して実行できます。

詳細は [docs/technical-spec.md](docs/technical-spec.md) の「GitHub Actions ワークフロー」を参照。

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [docs/spec.md](docs/spec.md) | 仕様書（目的、データソース、スキーマ、イベントモデル、更新ルール） |
| [docs/technical-spec.md](docs/technical-spec.md) | 技術仕様書（モジュール構成、HTML解析、処理フロー、GitHub Actions） |
