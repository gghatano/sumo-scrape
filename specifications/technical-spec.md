# 技術仕様書：SumoDB スクレイピング・パース実装

本ドキュメントはモジュール構成、HTML解析仕様、処理フロー、運用に関する技術的詳細を記載する。
データスキーマやイベントモデルについては [spec.md](spec.md) を参照。

---

## 1. 技術スタック

| 項目 | 選定 |
|---|---|
| Python | 3.12+ |
| パッケージ管理 | uv |
| HTTPクライアント | requests |
| HTMLパーサー | beautifulsoup4 (html.parser) |
| テスト | pytest |
| ビルド | pyproject.toml (src layout) |

---

## 2. モジュール構成と責務

```
src/sumodata/
  __init__.py          # バージョン定義
  __main__.py          # python -m sumodata エントリポイント
  cli.py               # 引数パース、メイン処理フロー
  fetch.py             # HTTP取得、リトライ、キャッシュ
  parse_results.py     # Results.aspx パーサー
  parse_banzuke.py     # Banzuke.aspx パーサー
  parse_rikishi.py     # Rikishi.aspx パーサー
  io_csv.py            # CSV読み書き、upsert/replace
  models.py            # dataclass定義
  util.py              # 共通ユーティリティ
```

| モジュール | 責務 |
|---|---|
| `cli.py` | 引数パース、イベント決定、各モジュールの呼び出し、サマリーログ出力 |
| `fetch.py` | HTTP取得（リトライ・sleep）、HTMLキャッシュの読み書き |
| `parse_results.py` | Results.aspx のHTML解析 → `BoutRecord` リスト生成 |
| `parse_banzuke.py` | Banzuke.aspx のHTML解析 → `ShikonaRecord` リスト生成 |
| `parse_rikishi.py` | Rikishi.aspx のHTML解析 → `RikishiRecord` 生成 |
| `io_csv.py` | CSV読み書き、upsert / force_replace ロジック |
| `models.py` | `BoutRecord`, `ShikonaRecord`, `RikishiRecord` の dataclass 定義 |

---

## 3. データモデル（models.py）

```python
@dataclass
class BoutRecord:
    event_id: str
    event_type: str        # honbasho_regular / honbasho_playoff
    is_regular: str        # "T" / "F"
    basho: str             # YYYYMM
    day: int
    division: str
    bout_no: int
    east_rid: int
    west_rid: int
    winner_side: str       # "E" / "W" / ""
    kimarite: str
    east_rank: str
    west_rank: str
    result_type: str       # normal / fusen / kyujo / playoff / unknown
    note: str
    source_url: str
    source_row_index: int
    fetched_at: str        # ISO形式

@dataclass
class ShikonaRecord:
    basho: str
    rid: int
    shikona_at_basho: str
    source_url: str
    division: str
    rank: str

@dataclass
class RikishiRecord:
    rid: int
    current_shikona: str
    updated_at: str
    source_url: str
```

---

## 4. HTTPクライアント設計（fetch.py）

### URL構成

| 種別 | URLパターン |
|---|---|
| Results | `https://sumodb.sumogames.de/Results.aspx?b={basho}&d={day}` |
| Banzuke | `https://sumodb.sumogames.de/Banzuke.aspx?b={basho}` |
| Rikishi | `https://sumodb.sumogames.de/Rikishi.aspx?r={rid}` |

### リクエスト設定

```python
HEADERS = {
    "User-Agent": "sumodata/0.1 (+https://github.com/<owner>/sumo_scrape)"
}
MAX_RETRIES = 3
BACKOFF_BASE = 1  # 秒: 1, 2, 4
SLEEP_MIN = 0.5
SLEEP_MAX = 1.5
```

### リトライロジック

```
attempt 1 → 失敗 → sleep 1s → attempt 2 → 失敗 → sleep 2s → attempt 3 → 失敗 → FetchError
```

HTTP != 200 または ConnectionError 時にリトライ。最終失敗で `FetchError` を送出。

### キャッシュ設計

| 設定 | 動作 |
|---|---|
| `--raw-cache on` | fetch前にキャッシュ確認。ヒットでfetchスキップ。取得後にファイル保存 |
| `--raw-cache off` | キャッシュの読み書きを一切しない |

キャッシュパス:
```
data/raw/{event_id}/results_d{DD:02d}.html
data/raw/{event_id}/banzuke.html
data/raw/{event_id}/playoff.html
data/raw/rikishi/r{rid}.html
```

---

## 5. Resultsページ解析仕様（parse_results.py）

### ページ全体構造

```html
<table class="layout">
  <td class="layoutleft">   <!-- サイドバー（日別ナビ、優勝争い） -->
  <td class="layoutright">  <!-- メインコンテンツ（取組結果） -->
```

### Division認識

- `<table class="tk_table">` が division 単位で存在（1ページに最大6テーブル）
- 各テーブルの最初の `<tr>` に `<td class="tk_kaku" colspan="5">` があり、division名を含む
- Division名: `Makuuchi`, `Juryo`, `Makushita`, `Sandanme`, `Jonidan`, `Jonokuchi`

### 取組行の構造（5セル）

```
| td.tk_kekka | td.tk_east | td.tk_kim | td.tk_west | td.tk_kekka |
| East結果    | East力士   | 決まり手  | West力士   | West結果    |
```

### 勝敗判定（tk_kekka セル）

`<img>` の `src` 属性で判定:

| src | 意味 | winner_side |
|---|---|---|
| `img/hoshi_shiro.gif` | 勝ち（白星） | 該当側 |
| `img/hoshi_kuro.gif` | 負け（黒星） | - |
| `img/hoshi_fusensho.gif` | 不戦勝 | 該当側 |
| `img/hoshi_fusenpai.gif` | 不戦敗 | - |

**判定ルール**: East側（1番目のtk_kekka）が `shiro` or `fusensho` → `winner_side = "E"`、West側（5番目のtk_kekka）が同様 → `winner_side = "W"`

### 力士rid抽出（tk_east / tk_west セル）

```html
<a href='Rikishi.aspx?r=11927'>Terunofuji</a>
```

正規表現: `Rikishi\.aspx\?r=(\d+)`

### 番付抽出（tk_east / tk_west セル）

```html
<font size="1">Y1e</font>
```

`<font size="1">` の最初のテキストノードから取得。

### 決まり手抽出（tk_kim セル）

```html
<td class="tk_kim">
  <font size="1"><br /></font>
  yorikiri              <!-- これが kimarite -->
  <br />
  <font ...>...</font>
</td>
```

`<font size="1"><br/></font>` の直後のテキストノードを `.strip()` で取得。

### result_type 判定

| 条件 | result_type |
|---|---|
| img src に `fusensho` or `fusenpai` | `fusen` |
| kimarite テキストが `"fusen"` | `fusen` |
| 力士リンクがない、またはkyujoマーカー | `kyujo` |
| day = 16（playoff） | `playoff` |
| 上記以外で正常パース | `normal` |
| パース失敗 | `unknown` |

### bout_no 採番

- division内で出現順に1から連番
- divisionが変わるとリセット

### BoutRecord メタ列の責務分担

`parse_results_page` は以下の引数を受け取り、BoutRecord の全フィールドを埋める:

| フィールド | 値の由来 |
|---|---|
| `event_id`, `event_type`, `is_regular`, `basho`, `day` | 引数（呼び出し側が設定） |
| `division`, `bout_no`, `east_rid`, `west_rid`, `winner_side`, `kimarite`, `east_rank`, `west_rank`, `result_type`, `note` | パーサーがHTMLから抽出・判定 |
| `source_url`, `fetched_at` | 引数（呼び出し側が設定） |
| `source_row_index` | パーサーが採番（ページ内通し番号） |

---

## 6. Banzukeページ解析仕様（parse_banzuke.py）

### ページ構造

division ごとに `<table class="banzuke">` が存在。

```html
<table class="banzuke" border="0" width="370">
  <caption>Makuuchi Banzuke</caption>
  <thead>
    <tr><th>Result</th><th>East</th><th>Rank</th><th>West</th><th>Result</th></tr>
  </thead>
  <tbody>
    <!-- 力士行 -->
  </tbody>
</table>
```

### Caption → Division マッピング

| caption テキスト | division |
|---|---|
| `Makuuchi Banzuke` | Makuuchi |
| `Juryo Banzuke` | Juryo |
| `Makushita Banzuke` | Makushita |
| `Sandanme Banzuke` | Sandanme |
| `Jonidan Banzuke` | Jonidan |
| `Jonokuchi Banzuke` | Jonokuchi |
| `Mae-zumo` | Mae-zumo（スキップ） |
| `Banzuke-gai` | Banzuke-gai（スキップ） |

### 力士行の構造（5セル）

```
| td (Result) | td.shikona (East) | td.short_rank (Rank) | td.shikona (West) | td (Result) |
```

### rid・四股名抽出

```html
<td class="shikona">
  <a title='琴櫻, Sadogatake, Chiba, ...' href='Rikishi.aspx?r=12270'>Kotozakura</a>
</td>
```

- **rid**: `href` から正規表現 `Rikishi\.aspx\?r=(\d+)` で抽出
- **shikona_at_basho**: `title` 属性のカンマ区切り1番目（**日本語四股名**）を使用
  - 抽出方法: `title.split(',')[0].strip()`
  - フォールバック: title属性が存在しないまたは空の場合のみリンクテキスト（ローマ字）を使用

### 番付抽出

```html
<td class="short_rank">Y</td>
<td class="short_rank">M1</td>
```

- East側: `{rank}e`（例: `Ye`, `M1e`）
- West側: `{rank}w`（例: `Yw`, `M1w`）

### 特殊セル

| クラス | 意味 | 処理 |
|---|---|---|
| `td.emptycell` (colspan=2) | 該当側に力士なし | スキップ |
| `td.retired` | 引退力士 | 取得する |
| `td.debut` | 新入幕等 | 取得する |
| `tr.sanyaku` | 三役以上 | 通常通り取得 |

### title属性のフィールド構成

Results/Banzuke共通。力士リンクの `title` 属性:

```
'照ノ富士, Isegahama, Mongolia, 29.11.1991, 2011.01, 2025.01, 192 cm 176 kg, Y'
```

| 位置 | 内容 | 例 |
|---|---|---|
| 0 | 日本語四股名 | 照ノ富士 |
| 1 | 部屋 | Isegahama |
| 2 | 出身地 | Mongolia |
| 3 | 生年月日 | 29.11.1991 |
| 4 | 初土俵 | 2011.01 |
| 5 | 引退場所（現役は空） | 2025.01 |
| 6 | 身長体重 | 192 cm 176 kg |
| 7 | 現在最高位 | Y |

---

## 7. Playoff検出ロジック

### 検出方法

左サイドバーの `<table class="daytable">` 内を走査:

```html
<td colspan="5"><a href="Results.aspx?b=202501&d=16">Playoffs</a></td>
```

- `d=16` へのリンクが存在し、テキストが `"Playoffs"` であれば playoff あり
- 15日目のページで検出するのが最も確実

### playoffページの構造

通常のResultsページと**同一構造**（`tk_table`, `tk_kaku`, etc.）。

パース時の設定:
- `event_id = honbasho-{basho}-playoff`
- `event_type = honbasho_playoff`
- `is_regular = "F"`
- `day = 16`

---

## 8. CSV出力仕様（io_csv.py）

### 共通設定

- エンコーディング: UTF-8（BOMなし）
- 改行: LF (`\n`)
- 区切り: カンマ
- 引用: 必要時のみ（`csv.QUOTE_MINIMAL`）
- ヘッダ: 常に出力

### カラム順

**fact_bout_daily.csv**:
```
event_id,event_type,is_regular,basho,day,division,bout_no,east_rid,west_rid,winner_side,kimarite,east_rank,west_rank,result_type,note,source_url,source_row_index,fetched_at
```

**dim_shikona_by_basho.csv**:
```
basho,rid,shikona_at_basho,source_url,division,rank
```

**dim_rikishi_current.csv**:
```
rid,current_shikona,updated_at,source_url
```

### upsert ロジック

標準ライブラリ `csv` + `dict` ベースで実装（pandas は使用しない）。

```python
def upsert(csv_path, new_records, key_columns, sort_columns):
    # 1. 既存CSVを csv.DictReader で読み込み（ファイル未存在時は空リスト）
    # 2. 既存行を key_columns のタプルをキーにした dict に変換
    # 3. new_records で上書き（同一キーは置換、新規キーは追加）
    # 4. sort_columns でソートして csv.DictWriter で書き出し
```

### force 置換ロジック

```python
def force_replace(csv_path, new_records, filter_column, filter_value, sort_columns):
    # 1. 既存CSVを読み込み
    # 2. filter_column == filter_value の行を除去
    # 3. new_records を追加
    # 4. sort_columns でソートして書き出し
```

---

## 9. CLI設計（cli.py）

### 引数一覧

```
python -m sumodata --basho YYYYMM [options]

必須:
  --basho YYYYMM        対象場所（例: 202601）

オプション:
  --force               イベント単位で完全置換（デフォルト: upsert）
  --raw-cache {on,off}  HTMLキャッシュ（デフォルト: on）
  --playoff {on,off}    playoff取得（デフォルト: on）
  --log-level {INFO,DEBUG}  ログレベル（デフォルト: INFO）
```

### メイン処理フロー

```
1. 引数パース
2. event_id 生成: honbasho-{basho}
3. Results取得・パース (d=1..15)
4. Banzuke取得・パース
5. Playoff検出・取得・パース（--playoff on の場合）
6. CSV出力 (fact_bout_daily, dim_shikona_by_basho)
7. (任意) dim_rikishi_current 更新
8. サマリーログ出力
```

### 終了コード

| コード | 意味 |
|---|---|
| 0 | 正常終了 |
| 1 | エラー（HTTP失敗、パースエラー等） |

---

## 10. エラーハンドリング

### 例外クラス

```python
class SumodataError(Exception): pass
class FetchError(SumodataError): pass
class ParseError(SumodataError): pass
```

### Fail fast 方針

| 状況 | 動作 |
|---|---|
| HTTP最終失敗 | `FetchError` → ジョブ停止 |
| HTML構造変更によるパース失敗 | `ParseError` → ジョブ停止 |
| Playoff検出不能 | 警告ログのみ、スキップ |
| 個別取組行のパース失敗 | `result_type=unknown` で記録、続行 |

---

## 11. GitHub Actions ワークフロー（monthly.yml）

### 実行方式

- `workflow_dispatch`（手動）+ `schedule`（月次）
- schedule: 毎月27日 16:30 UTC（= 28日 01:30 JST）

### basho決定

- **手動**: 入力 `basho`（YYYYMM）があればそれを優先
- **自動**: 当月（UTC）の `YYYYMM` を算出し、本場所月（1/3/5/7/9/11）のみ実行
- 本場所月でない場合は no-op（正常終了）

### 更新・コミット

1. `data/fact/*.csv` と `data/dim/*.csv` を `git add`
2. 差分があるときだけ commit & push
3. 競合回避: `git pull --rebase`
4. 多重実行防止: `concurrency` グループ設定

### ワークフロー定義

```yaml
name: Monthly Sumo Data Update

on:
  workflow_dispatch:
    inputs:
      basho:
        description: "Target basho in YYYYMM (e.g., 202601). If empty, computed from current date."
        required: false
        default: ""
      force:
        description: "Force rebuild for the target basho (replace rows)."
        required: false
        default: "false"
  schedule:
    - cron: "30 16 27 * *"

permissions:
  contents: write

concurrency:
  group: sumo-data-monthly
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - Checkout → Setup Python → Install uv → Install dependencies
      - Compute target basho (本場所月判定)
      - Run pipeline (uv run python -m sumodata --basho ... --raw-cache off)
      - Commit & push if changed
```

ワークフロー定義の全文は `.github/workflows/monthly.yml` を参照。
