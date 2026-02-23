# 仕様書：SumoDB 取組データ収集・名寄せCSV生成

## 1. 目的

SumoDB（sumodb.sumogames.de）を情報源として、大相撲の取組結果を取得し、**力士ID（rid）で名寄せされたCSV**を生成・更新する。

本場所の通常日程に加え、優勝決定戦（Playoff）にも対応する。イベント概念（`event_id` / `event_type` / `is_regular`）をスキーマに組み込み、通常日程と非通常イベントを区別できる構造としている。

---

## 2. データソース

SumoDB の以下のページからデータを取得する。

| 種別 | URL パターン | 説明 |
|---|---|---|
| Results | `https://sumodb.sumogames.de/Results.aspx?b={YYYYMM}&d={day}` | 日別取組結果（d=1〜15） |
| Banzuke | `https://sumodb.sumogames.de/Banzuke.aspx?b={YYYYMM}` | 場所の番付（力士一覧・四股名） |
| Rikishi | `https://sumodb.sumogames.de/Rikishi.aspx?r={rid}` | 力士個別ページ（最新四股名、差分のみ） |
| Playoff | `https://sumodb.sumogames.de/Results.aspx?b={YYYYMM}&d=16` | 優勝決定戦（存在する場合のみ） |

---

## 3. 出力ファイル仕様

### 3.1 `data/fact/fact_bout_daily.csv` — 取組ファクトテーブル

日別の全取組記録。力士は rid で名寄せされている。

**一意キー**: `(event_id, day, division, bout_no)`

**ソート順**: `event_id, day, division, bout_no`

| カラム | 型 | 説明 |
|---|---|---|
| `event_id` | string | イベントID（例: `honbasho-202501`, `honbasho-202501-playoff`） |
| `event_type` | string | `honbasho_regular` / `honbasho_playoff` / `tournament` / `unknown` |
| `is_regular` | string | 本場所通常日程: `T`、それ以外: `F` |
| `basho` | string | 場所（YYYYMM）。本場所由来のイベントのみ |
| `day` | int | 日目（本場所: 1〜15、playoff: 16） |
| `division` | string | 階級（Makuuchi / Juryo / Makushita / Sandanme / Jonidan / Jonokuchi） |
| `bout_no` | int | division内の出現順連番（1〜N） |
| `east_rid` | int | 東方の力士ID |
| `west_rid` | int | 西方の力士ID |
| `winner_side` | string | 勝者側（`E` / `W` / 空文字） |
| `kimarite` | string | 決まり手（未記載は空文字） |
| `east_rank` | string | 東方の番付（例: `Y1e`。取得不可は空文字） |
| `west_rank` | string | 西方の番付 |
| `result_type` | string | `normal` / `fusen` / `kyujo` / `playoff` / `unknown` |
| `note` | string | 備考 |
| `source_url` | string | 取得元URL |
| `source_row_index` | int | ページ内行番号 |
| `fetched_at` | string | 取得日時（ISO形式） |

### 3.2 `data/dim/dim_shikona_by_basho.csv` — 四股名ディメンションテーブル

場所ごとの力士四股名。本場所用途に限定。

**一意キー**: `(basho, rid)`

**ソート順**: `basho, rid`

| カラム | 型 | 説明 |
|---|---|---|
| `basho` | string | 場所（YYYYMM） |
| `rid` | int | 力士ID |
| `shikona_at_basho` | string | 当該場所時点の四股名（日本語） |
| `source_url` | string | 取得元URL（Banzuke URL） |
| `division` | string | 階級 |
| `rank` | string | 番付 |

### 3.3 `data/dim/dim_rikishi_current.csv` — 最新四股名ディメンション（任意）

| カラム | 型 | 説明 |
|---|---|---|
| `rid` | int | 力士ID |
| `current_shikona` | string | 最新の四股名 |
| `updated_at` | string | 更新日時（ISO形式） |
| `source_url` | string | 取得元URL |

---

## 4. イベントモデル

取組は「イベント（event）」に紐づけて管理される。

| フィールド | 説明 | 値の例 |
|---|---|---|
| `event_id` | イベントの一意識別子 | `honbasho-202501`, `honbasho-202501-playoff` |
| `event_type` | イベントの種別 | `honbasho_regular`, `honbasho_playoff`, `tournament` |
| `is_regular` | 本場所通常日程かどうか | `T`（通常日程）/ `F`（playoff等） |

### イベント決定ルール

- **本場所通常日程**: `event_id = honbasho-{YYYYMM}`, `event_type = honbasho_regular`, `is_regular = T`
- **Playoff**: `event_id = honbasho-{YYYYMM}-playoff`, `event_type = honbasho_playoff`, `is_regular = F`, `day = 16`

---

## 5. 名寄せ方針

### rid ベースの名寄せ

- 名寄せキーは**力士ページID（rid）**（`Rikishi.aspx?r=...` の `r` パラメータ）
- 四股名（表示名）は主キーにしない

### 四股名の管理（dim）

四股名は以下の2系統で管理する:

| テーブル | 用途 | 結合方法 |
|---|---|---|
| `dim_shikona_by_basho` | 場所時点の四股名を復元 | `basho` + `rid` で join |
| `dim_rikishi_current` | 最新の表示名（任意） | `rid` で join |

### 改名への対応

- 改名履歴を日付で JOIN する設計は避ける
- `dim_shikona_by_basho` により**「場所時点の四股名」**を正確に復元できる

---

## 6. 更新ルール

### 6.1 upsert（デフォルト）

既存CSVに同一キーの行がある場合は上書き、ない場合は追加。

| ファイル | upsert キー |
|---|---|
| `fact_bout_daily.csv` | `(event_id, day, division, bout_no)` |
| `dim_shikona_by_basho.csv` | `(basho, rid)` |

### 6.2 force replace（`--force` オプション）

対象イベント/場所の行を全削除してから新規生成分で置換。

| ファイル | 削除条件 |
|---|---|
| `fact_bout_daily.csv` | `event_id` が対象イベントに一致する行 |
| `dim_shikona_by_basho.csv` | `basho` が対象場所に一致する行 |

---

## 7. 非機能要件

### 再現性

- 同一入力で同一結果となること（外部サイト更新を除く）
- HTMLキャッシュ（`--raw-cache on`）を有効にすることで、再実行時にfetchを省略し同一結果を保証

### 負荷制御

- 取得は最小限（1本場所あたり results 最大15ページ + banzuke 1ページ + playoff + 新規rid分）
- レート制御: ページ間 sleep（0.5〜1.5秒ランダム）、リトライ（指数バックオフ、最大3回）
- User-Agent を明示

### エラーハンドリング

- HTTP最終失敗 → ジョブ停止（Fail fast）
- HTML構造変更によるパース失敗 → ジョブ停止
- Playoff検出不能 → 警告ログのみ、スキップ
- 本場所でない月の指定 → 正常終了（no-op）
- ログに URL・HTTPステータス・例外要点を記録
