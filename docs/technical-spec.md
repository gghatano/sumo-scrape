# 技術仕様書：SumoDB スクレイピング・パース実装

本ドキュメントは `docs/spec.md` の実装に必要な技術的詳細を記載する。
SumoDB（sumodb.sumogames.de）のHTML構造解析結果に基づく。

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

## 2. モジュール構成

```
src/sumodata/
  __init__.py          # バージョン定義
  __main__.py          # python -m sumodata エントリポイント
  cli.py               # 引数パース、メイン処理フロー
  fetch.py             # HTTP取得、リトライ、キャッシュ
  parse_results.py     # Results.aspx パーサー
  parse_banzuke.py     # Banzuke.aspx パーサー
  parse_rikishi.py     # Rikishi.aspx パーサー（任意）
  io_csv.py            # CSV読み書き、upsert/replace
  models.py            # dataclass定義
  util.py              # 共通ユーティリティ
```

---

## 3. データモデル（models.py）

```python
from dataclasses import dataclass

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

### 4.1 URL構成

| 種別 | URLパターン |
|---|---|
| Results | `https://sumodb.sumogames.de/Results.aspx?b={basho}&d={day}` |
| Banzuke | `https://sumodb.sumogames.de/Banzuke.aspx?b={basho}` |
| Rikishi | `https://sumodb.sumogames.de/Rikishi.aspx?r={rid}` |

### 4.2 リクエスト設定

```python
HEADERS = {
    "User-Agent": "sumodata/0.1 (+https://github.com/<owner>/sumo_scrape)"
}
MAX_RETRIES = 3
BACKOFF_BASE = 1  # 秒: 1, 2, 4
SLEEP_MIN = 0.5
SLEEP_MAX = 1.5
```

### 4.3 リトライロジック

```
attempt 1 → 失敗 → sleep 1s → attempt 2 → 失敗 → sleep 2s → attempt 3 → 失敗 → 例外
```

HTTP != 200 またはConnectionError時にリトライ。最終失敗で `FetchError` を送出。

### 4.4 キャッシュ設計

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

### 5.1 ページ全体構造

```
<table class="layout">
  <td class="layoutleft">   ← サイドバー（日別ナビ、優勝争い）
  <td class="layoutright">  ← メインコンテンツ（取組結果）
```

### 5.2 Division認識

- `<table class="tk_table">` が division 単位で存在（1ページに6テーブル）
- 各テーブルの最初の `<tr>` に `<td class="tk_kaku" colspan="5">` があり、division名を含む

Division名（テキスト値）:
- `Makuuchi`, `Juryo`, `Makushita`, `Sandanme`, `Jonidan`, `Jonokuchi`

### 5.3 取組行の構造（5セル）

```
| td.tk_kekka | td.tk_east | td.tk_kim | td.tk_west | td.tk_kekka |
| East結果    | East力士   | 決まり手  | West力士   | West結果    |
```

### 5.4 勝敗判定（tk_kekka セル）

`<img>` の `src` 属性で判定:

| src | 意味 | winner_side |
|---|---|---|
| `img/hoshi_shiro.gif` | 勝ち（白星） | 該当側 |
| `img/hoshi_kuro.gif` | 負け（黒星） | - |
| `img/hoshi_fusensho.gif` | 不戦勝 | 該当側 |
| `img/hoshi_fusenpai.gif` | 不戦敗 | - |

**判定ルール**: East側（1番目のtk_kekka）が `shiro` or `fusensho` → `winner_side = "E"`、West側（5番目のtk_kekka）が同様 → `winner_side = "W"`。

### 5.5 力士rid抽出（tk_east / tk_west セル）

```html
<a href='Rikishi.aspx?r=11927'>Terunofuji</a>
```

正規表現: `Rikishi\.aspx\?r=(\d+)`

### 5.6 番付抽出（tk_east / tk_west セル）

```html
<font size="1">Y1e</font>
```

`<font size="1">` の最初のテキストノードから取得。

### 5.7 決まり手抽出（tk_kim セル）

```html
<td class="tk_kim">
  <font size="1"><br /></font>
  yorikiri              ← これが kimarite
  <br />
  <font ...>...</font>
</td>
```

`<font size="1"><br/></font>` の直後のテキストノードを `.strip()` で取得。

### 5.8 result_type 判定

| 条件 | result_type |
|---|---|
| img src に `fusensho` or `fusenpai` | `fusen` |
| kimarite テキストが `"fusen"` | `fusen` |
| 力士リンクがない、またはkyujoマーカー | `kyujo` |
| day = 16（playoff） | `playoff` |
| 上記以外で正常パース | `normal` |
| パース失敗 | `unknown` |

### 5.9 bout_no 採番

- division内で出現順に1から連番
- divisionが変わるとリセット

### 5.10 BoutRecord メタ列の責務分担

`parse_results_page` は以下の引数を受け取り、BoutRecord の全フィールドを埋める責務を持つ:

| フィールド | 値の由来 |
|---|---|
| `event_id` | 引数（呼び出し側が生成） |
| `event_type` | 引数（呼び出し側が決定） |
| `is_regular` | 引数（呼び出し側が決定） |
| `basho` | 引数（呼び出し側が設定） |
| `day` | 引数（呼び出し側が設定） |
| `division` | パーサーがHTMLから抽出 |
| `bout_no` | パーサーが採番 |
| `east_rid`, `west_rid` | パーサーがHTMLから抽出 |
| `winner_side` | パーサーがHTMLから判定 |
| `kimarite` | パーサーがHTMLから抽出 |
| `east_rank`, `west_rank` | パーサーがHTMLから抽出 |
| `result_type` | パーサーが判定（Section 5.8） |
| `note` | パーサーが判定 |
| `source_url` | 引数（呼び出し側が設定） |
| `source_row_index` | パーサーが採番（ページ内の取組行通し番号。division をまたいで1から連番） |
| `fetched_at` | 引数（呼び出し側が取得時刻を渡す） |

呼び出し側（cli.py）のコード例:
```python
records = parse_results_page(
    html=html,
    event_id="honbasho-202601",
    event_type="honbasho_regular",
    is_regular="T",
    basho="202601",
    day=1,
    source_url="https://sumodb.sumogames.de/Results.aspx?b=202601&d=1",
    fetched_at="2026-01-20T12:00:00+09:00",
)
```

---

## 6. Playoff検出ロジック

### 6.1 検出方法

左サイドバーの `<table class="daytable">` 内を走査:

```html
<td colspan="5"><a href="Results.aspx?b=202501&d=16">Playoffs</a></td>
```

- `d=16` へのリンクが存在し、テキストが `"Playoffs"` であれば playoff あり
- 15日目のページで検出するのが最も確実

### 6.2 playoffページの構造

通常のResultsページと**同一構造**（`tk_table`, `tk_kaku`, etc.）。

パース時の設定:
- `event_id = honbasho-{basho}-playoff`
- `event_type = honbasho_playoff`
- `is_regular = "F"`
- `day = 16`

### 6.3 ページタイトル

```html
<h1>Hatsu 2025, Yusho Playoffs</h1>
```

---

## 7. Banzukeページ解析仕様（parse_banzuke.py）

### 7.1 ページ構造

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

### 7.2 Caption → Division マッピング

| caption テキスト | division |
|---|---|
| `Makuuchi Banzuke` | Makuuchi |
| `Juryo Banzuke` | Juryo |
| `Makushita Banzuke` | Makushita |
| `Sandanme Banzuke` | Sandanme |
| `Jonidan Banzuke` | Jonidan |
| `Jonokuchi Banzuke` | Jonokuchi |
| `Mae-zumo` | Mae-zumo（スキップ推奨）|
| `Banzuke-gai` | Banzuke-gai（スキップ推奨）|

### 7.3 力士行の構造（5セル）

```
| td (Result) | td.shikona (East) | td.short_rank (Rank) | td.shikona (West) | td (Result) |
```

### 7.4 rid・四股名抽出

```html
<td class="shikona">
  <a title='琴櫻, Sadogatake, Chiba, ...' href='Rikishi.aspx?r=12270'>Kotozakura</a>
</td>
```

- rid: `href` から正規表現 `Rikishi\.aspx\?r=(\d+)` で抽出
- **shikona_at_basho（確定ルール）**: `title` 属性のカンマ区切り1番目（**日本語四股名**）を使用する
  - 抽出方法: `title.split(',')[0].strip()`
  - 例: `title='琴櫻, Sadogatake, ...'` → `shikona_at_basho = "琴櫻"`
  - **フォールバック**: title属性が存在しない、または空の場合のみリンクテキスト（ローマ字）を使用
  - 注: リンクテキスト（例: `Kotozakura`）は主キーとしては使用しない

### 7.5 番付抽出

```html
<td class="short_rank">Y</td>
<td class="short_rank">M1</td>
```

- East側の力士: `{rank}e` (例: `Ye`, `M1e`)
- West側の力士: `{rank}w` (例: `Yw`, `M1w`)
- `short_rank` のテキスト + side文字で完全な番付文字列を構成

### 7.6 特殊セル

| クラス | 意味 | 処理 |
|---|---|---|
| `td.emptycell` (colspan=2) | 該当側に力士なし | スキップ |
| `td.retired` | 引退力士 | 取得する（番付に載っている） |
| `td.debut` | 新入幕等 | 取得する |
| `tr.sanyaku` | 三役以上 | 通常通り取得 |

### 7.7 四股名の抽出ルール（確定）

- **確定**: `shikona_at_basho` には title 属性の先頭フィールド（**日本語四股名**）を使用する
- title 属性が存在しない、または空の場合**のみ**リンクテキスト（ローマ字）にフォールバック
- この規則は Banzuke パース（task-007）だけでなく、将来的に他の箇所で四股名を取得する場合にも適用する

---

## 8. CSV出力仕様（io_csv.py）

### 8.1 共通設定

- エンコーディング: UTF-8（BOMなし）
- 改行: LF (`\n`)
- 区切り: カンマ
- 引用: 必要時のみ（csv.QUOTE_MINIMAL）
- ヘッダ: 常に出力

### 8.2 fact_bout_daily.csv カラム順

```
event_id,event_type,is_regular,basho,day,division,bout_no,east_rid,west_rid,winner_side,kimarite,east_rank,west_rank,result_type,note,source_url,source_row_index,fetched_at
```

### 8.3 dim_shikona_by_basho.csv カラム順

```
basho,rid,shikona_at_basho,source_url,division,rank
```

### 8.4 dim_rikishi_current.csv カラム順

```
rid,current_shikona,updated_at,source_url
```

### 8.5 upsert ロジック

標準ライブラリ `csv` + `dict` ベースで実装する（pandas は使用しない。依存最小化のため）。

```python
def upsert(
    csv_path: Path,
    new_records: list[dict],
    key_columns: list[str],
    sort_columns: list[str],
) -> None:
    # 1. 既存CSVを csv.DictReader で list[dict] として読み込み（ファイル未存在時は空リスト）
    # 2. 既存行を key_columns のタプルをキーにした dict[tuple, dict] に変換
    # 3. new_records で上書き（同一キーは置換、新規キーは追加）
    # 4. sort_columns でソートして csv.DictWriter で書き出し
```

### 8.6 force 置換ロジック

```python
def force_replace(
    csv_path: Path,
    new_records: list[dict],
    filter_column: str,
    filter_value: str,
    sort_columns: list[str],
) -> None:
    # 1. 既存CSVを csv.DictReader で list[dict] として読み込み
    # 2. filter_column == filter_value の行を除去
    # 3. new_records を追加
    # 4. sort_columns でソートして csv.DictWriter で書き出し
```

---

## 9. CLI設計（cli.py）

### 9.1 引数一覧

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

### 9.2 メイン処理フロー

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

### 9.3 終了コード

| コード | 意味 |
|---|---|
| 0 | 正常終了 |
| 1 | エラー（HTTP失敗、パースエラー等） |

---

## 10. エラーハンドリング

### 10.1 例外クラス

```python
class SumodataError(Exception): pass
class FetchError(SumodataError): pass
class ParseError(SumodataError): pass
```

### 10.2 Fail fast 方針

- HTTP最終失敗 → `FetchError` → ジョブ停止
- HTML構造変更によるパース失敗 → `ParseError` → ジョブ停止
- Playoff検出不能 → 警告ログのみ、スキップ
- 個別取組行のパース失敗 → `result_type=unknown` で記録、続行

---

## 11. rikishi title属性のフィールド構成

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

※フィールド5（引退場所）が空の場合、カンマは残るが値がない。
