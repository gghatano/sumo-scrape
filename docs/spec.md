# 仕様書：SumoDB 取組データ収集・名寄せCSV生成（大会拡張／GitHub Actions月次バッチ対応）

## 1. 目的

SumoDB を情報源として、取組結果を取得し、分析に耐える形で **r-id（力士ID）で名寄せされたCSV**を生成・更新する。

運用は段階導入で進める：

* **～2024年**：ローカル実行で過去データを作成（検証・整備）
* **2025年**：GitHub Actions で実行可否・安定性検証（テスト運用）
* **2026年以降**：GitHub Actions の月次バッチで自動更新（放置運用）

加えて、Playoffや「日本大相撲トーナメント」等の本場所以外の大会にも耐えるよう、イベント概念（event_id / event_type / is_regular）をスキーマに組み込む。

---

## 2. スコープ

### 2.1 取得対象（初期実装）

* 本場所（honbasho）：年・月（YYYYMM）で指定
* 日別結果ページ：`Results.aspx?b=YYYYMM&d=DD`（d=1..15）

  * 例：`https://sumodb.sumogames.de/Results.aspx?b=202601&d=1`
* Playoff（優勝決定戦等）：Resultsページに導線がある場合に取得
* 番付ページ：`Banzuke.aspx?b=YYYYMM`（場所×力士の四股名取得）

  * 例：`https://sumodb.sumogames.de/Banzuke.aspx?b=202601`
* 力士ページ：`Rikishi.aspx?r=RID`（最新四股名取得、差分のみ）

  * 例：`https://sumodb.sumogames.de/Rikishi.aspx?r=12451`

### 2.2 将来拡張（初期実装では取得対象外でよい）

* 本場所以外の大会（例：日本大相撲トーナメント）
  ※スキーマは対応済み。取得ロジック／入力インターフェースは後付け可能にする。

---

## 3. 生成物（アウトプット）

必須：

1. **取組ファクト（r-id名寄せ済み）**
   `data/fact/fact_bout_daily.csv`
2. **場所×力士の四股名ディメンション（本場所用）**
   `data/dim/dim_shikona_by_basho.csv`

任意（推奨）：
3) **力士の最新四股名ディメンション**
`data/dim/dim_rikishi_current.csv`
4) **取得元HTMLのキャッシュ（再現性・デバッグ用）**
`data/raw/<event_id>/...`

---

## 4. 前提・設計方針

### 4.1 名寄せ方針

* 名寄せキーは **力士ページID（rid）**（`Rikishi.aspx?r=...` の `r`）とする。
* 四股名（表示名）は主キーにしない。以下の2系統で扱う：

  * **場所×四股名**：`dim_shikona_by_basho`（本場所の場所単位で join）
  * **最新四股名**：`dim_rikishi_current`（任意、表示用）

### 4.2 改名履歴の扱い

* 改名履歴を日付でJOINする設計は避ける。
* 本場所は `dim_shikona_by_basho` により **「場所時点の四股名」**を復元する。

### 4.3 イベント（大会）モデル

取組は「イベント（event）」に紐づけて扱う：

* `event_id`：イベントを一意に識別（例：`honbasho-202601`、`honbasho-202601-playoff`）
* `event_type`：イベント種別（例：`honbasho_regular` / `honbasho_playoff` / `tournament`）
* `is_regular`：本場所の通常日程（1〜15日目）の取組であれば **T**、それ以外は **F**

---

## 5. 非機能要件

### 5.1 再現性

* 同一入力で同一結果となること（外部サイト更新を除く）。
* HTML構造変更に備え、rawキャッシュ保存をON/OFFできる。

### 5.2 運用性

* ローカル：任意期間の作成・再作成が容易（CLI）。
* GitHub Actions：月次バッチで「該当月が本場所月なら実行」し差分更新。
* エラー時はジョブ失敗（Fail fast）。ログに URL・HTTPステータス・例外要点を残す。

### 5.3 負荷・礼儀

* 取得は最小限：1本場所あたり results最大15ページ＋banzuke1ページ＋（任意）playoff＋新規rid分。
* レート制御（sleep、リトライ、User-Agent明示）。

---

## 6. データ仕様（CSVスキーマ）

### 6.1 `fact_bout_daily.csv`（取組ファクト）

**一意キー（確定）**：`(event_id, day, division, bout_no)`

列（必須）：

* `event_id` : string

  * 例：`honbasho-202601` / `honbasho-202601-playoff`
* `event_type` : string

  * 値候補：`honbasho_regular` / `honbasho_playoff` / `tournament` / `unknown`
* `is_regular` : bool（T/F）

  * 定義：`event_type=honbasho_regular` なら T、それ以外は F
* `basho` : string（YYYYMM。イベントが本場所由来の場合のみ埋める。大会の場合は空欄可）
* `day` : int

  * 本場所通常日程：1..15
  * playoff等：16（固定推奨）
  * 大会：大会内の進行に応じる（後付け可）
* `division` : string

  * 本場所：Makuuchi/Juryo/…
  * 大会：`Tournament` 等（後付け可）
* `bout_no` : int（division内の出現順で 1..N 採番）
* `east_rid` : int
* `west_rid` : int
* `winner_side` : string（"E" / "W" / ""）
* `kimarite` : string（決まり手。未記載は ""）
* `east_rank` : string（例：Y1e 等。取得不可は ""）
* `west_rank` : string

列（推奨）：

* `result_type` : string（normal / fusen / kyujo / playoff / unknown）
* `note` : string
* `source_url` : string（取得元URL）
* `source_row_index` : int（ページ内行番号）
* `fetched_at` : string（ISO、任意）

### 6.2 `dim_shikona_by_basho.csv`（本場所：場所×四股名）

**一意キー（確定）**：`(basho, rid)`

列（必須）：

* `basho` : string（YYYYMM）
* `rid` : int
* `shikona_at_basho` : string
* `source_url` : string（Banzuke URL）

列（推奨）：

* `division` : string
* `rank` : string

※本場所以外の大会には番付概念が一致しない可能性があるため、本ディメンションは本場所用途に限定。

### 6.3 `dim_rikishi_current.csv`（任意：最新四股名）

**一意キー**：`rid`

列：

* `rid` : int
* `current_shikona` : string
* `updated_at` : string（ISO）
* `source_url` : string（Rikishi URL）

---

## 7. 入力インターフェース（実装方針は任せる前提での要件）

### 7.1 要件

* 本場所の月次バッチに必要な最小入力は「対象月（YYYYMM）」であること。
* 将来の大会対応（tournament等）を阻害しないこと。
* 手動実行でイベントを指定できること（GitHub Actions workflow_dispatch）。

### 7.2 推奨インターフェース（例：参考）

* 本場所：`--basho YYYYMM` → `event_id=honbasho-YYYYMM`
* 本場所playoff：本場所実行内で自動検出・取得（`event_id=honbasho-YYYYMM-playoff`）
* 大会：`--event-id tournament-YYYY --event-type tournament` のように明示（後付け）

※上記はあくまで推奨。実装上の都合に合わせて変更可。

---

## 8. 処理フロー

### 8.1 イベント決定

* 本場所モードの場合：

  * `event_id = honbasho-YYYYMM`
  * `event_type = honbasho_regular`
  * `is_regular = T`

* playoff が検出できた場合：

  * `event_id = honbasho-YYYYMM-playoff`
  * `event_type = honbasho_playoff`
  * `is_regular = F`
  * `day = 16`（固定推奨）

### 8.2 取得（fetch）

* results：`d=1..15` を順に取得
* banzuke：1回取得
* playoff：導線がある場合に取得（取得できない場合はスキップ）

取得仕様：

* HTTPリトライ：最大3回（指数バックオフ）
* ページ間sleep：0.5〜1.5秒程度ランダム
* User-Agent明示
* rawキャッシュ（ON時）：`data/raw/<event_id>/...` に保存

### 8.3 変換（parse）

#### A) Results → `fact_bout_daily`

* divisionごとにセクションを認識し、取組行を順に処理
* `bout_no`：division内順序で採番
* East/West のリンク先 `Rikishi.aspx?r=...` から rid 抽出
* 勝者判定（○等の記号）→ `winner_side`
* 決まり手→ `kimarite`
* 例外（不戦勝・休場等）→ `result_type` と `note`（判定不能は unknown）

#### B) Banzuke → `dim_shikona_by_basho`

* 力士リンクから rid
* 表示テキストから `shikona_at_basho`
* 可能なら division/rank を取得

#### C) （任意）Rikishi → `dim_rikishi_current`

* 当該実行で出現した rid のうち、未登録/更新対象のみ取得し更新

### 8.4 出力（write / update）

* CSV：ヘッダ付き、UTF-8、改行LF
* 更新方式：場所単位の完全置換（force）またはキー単位 upsert

---

## 9. 更新ルール（重複排除／置換更新）

### 9.1 `--force` 指定時（イベント単位の完全置換）

* `fact_bout_daily.csv`：対象 `event_id` の行を削除 → 新規生成分で置換
* `dim_shikona_by_basho.csv`：対象 `basho` の行を削除 → 新規生成分で置換（本場所のみ）

### 9.2 `--force` なし（upsert）

* 既存CSVに同一キーがある場合は上書き、ない場合は追加
* 適用キー：

  * `fact_bout_daily.csv`：`(event_id, day, division, bout_no)`
  * `dim_shikona_by_basho.csv`：`(basho, rid)`

### 9.3 ソート順（差分レビュー容易化）

* `fact_bout_daily.csv`：`event_id, day, division, bout_no`
* `dim_shikona_by_basho.csv`：`basho, rid`

---

## 10. 例外・障害時の扱い

* HTTP失敗（≠200）：リトライ→失敗でジョブ停止
* HTML構造変更：パース例外→ジョブ停止（rawキャッシュONなら原因特定しやすい）
* playoff検出不能：スキップ（将来改善）
* 本場所でない月：正常終了（no-op）

---

## 11. CLI仕様（最低限）

* 実行：`python -m sumodata ...`
* ログ：INFO/DEBUG
* 出力：更新行数（fact/dim）、対象イベント、処理時間
* 推奨オプション：

  * rawキャッシュON/OFF（Actionsはoff）
  * force
  * playoff取得ON/OFF（既定ON）

※具体的な引数設計は実装者判断（本仕様は要件のみ）。

---

## 12. リポジトリ構成（提案）

```
sumo-data/
  pyproject.toml
  README.md
  src/sumodata/
    __init__.py
    cli.py
    fetch.py
    parse_results.py
    parse_banzuke.py
    parse_rikishi.py
    io_csv.py
    models.py
    util.py
  data/
    raw/            # 任意（.gitignore 推奨）
    fact/
      fact_bout_daily.csv
    dim/
      dim_shikona_by_basho.csv
      dim_rikishi_current.csv
  .github/workflows/
    monthly.yml
  scripts/
    run_local.sh
```

---

## 13. GitHub Actions 仕様（`monthly.yml`）

### 13.1 実行方式

* `workflow_dispatch`（手動）＋ `schedule`（月次）
* schedule例：毎月28日 01:30 JST 相当（= 27日 16:30 UTC）

### 13.2 basho決定

* 手動：入力 `basho`（YYYYMM）があればそれを優先
* 自動：当月（UTC）の `YYYYMM` を算出し、本場所月（1/3/5/7/9/11）のみ実行
* 本場所月でない場合は no-op（正常終了）

### 13.3 更新・コミット

* 生成後に `data/fact/*.csv` と `data/dim/*.csv` を `git add`
* 差分があるときだけ commit/push
* 競合回避：`git pull --rebase`
* 多重実行防止：`concurrency`

### 13.4 `monthly.yml`（具体案）

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
    # 27th 16:30 UTC = 28th 01:30 JST
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
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        run: |
          python -m pip install --upgrade pip
          pip install uv

      - name: Install project dependencies
        run: |
          uv sync --frozen || uv sync

      - name: Compute target basho (YYYYMM)
        id: basho
        run: |
          set -euo pipefail

          INPUT_BASHO="${{ inputs.basho }}"
          if [ -n "${INPUT_BASHO}" ]; then
            echo "basho=${INPUT_BASHO}" >> "$GITHUB_OUTPUT"
            echo "should_run=true" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          YYYY=$(date -u +%Y)
          MM=$(date -u +%m)
          BASHO="${YYYY}${MM}"

          case "${MM}" in
            01|03|05|07|09|11)
              echo "basho=${BASHO}" >> "$GITHUB_OUTPUT"
              echo "should_run=true" >> "$GITHUB_OUTPUT"
              ;;
            *)
              echo "basho=${BASHO}" >> "$GITHUB_OUTPUT"
              echo "should_run=false" >> "$GITHUB_OUTPUT"
              ;;
          esac

      - name: No-op (not a honbasho month)
        if: steps.basho.outputs.should_run != 'true'
        run: |
          echo "Not a honbasho month. Exiting without changes."

      - name: Run pipeline
        if: steps.basho.outputs.should_run == 'true'
        env:
          BASHO: ${{ steps.basho.outputs.basho }}
          FORCE: ${{ inputs.force }}
        run: |
          set -euo pipefail
          echo "Target basho: ${BASHO}"
          if [ "${FORCE}" = "true" ]; then
            uv run python -m sumodata --basho "${BASHO}" --raw-cache off --force --log-level INFO
          else
            uv run python -m sumodata --basho "${BASHO}" --raw-cache off --log-level INFO
          fi

      - name: Commit & push if changed
        if: steps.basho.outputs.should_run == 'true'
        run: |
          set -euo pipefail

          git config user.name "sumo-data-bot"
          git config user.email "sumo-data-bot@users.noreply.github.com"

          git add data/fact/*.csv data/dim/*.csv || true

          if git diff --cached --quiet; then
            echo "No changes to commit."
            exit 0
          fi

          git commit -m "Update sumo data for basho ${{ steps.basho.outputs.basho }}"
          git pull --rebase
          git push
```

---

## 14. 開発計画（Claude Code向け Task 分解）

### Phase 0：土台

1. プロジェクト雛形（pyproject、srcレイアウト、README）
2. CLI骨格（引数、ログ、終了コード）

### Phase 1：取得層（fetch）

3. HTTP fetch（requests）＋リトライ＋sleep＋User-Agent
4. rawキャッシュ保存（ON/OFF、キャッシュヒット時fetch省略）

### Phase 2：パース層（parse）

5. Results パース（division認識、rid抽出、winner_side、kimarite、rank、bout_no採番）
6. playoff検出（導線があれば取得し、event_id/event_type/is_regular/day=16で格納）
7. Banzuke パース（rid、shikona_at_basho、可能ならrank/division）
8. 例外行の取り扱い（fusen/kyujo/unknown）

### Phase 3：出力層（write/update）

9. CSV writer（UTF-8, LF）
10. upsert/replace（確定キー：factは `event_id,day,division,bout_no`、dimは `basho,rid`）
11. `dim_rikishi_current`（差分ridのみ取得、任意）

### Phase 4：運用

12. ローカル実行手順（例：2000-2024の作成フロー）
13. GitHub Actions workflow（monthly.yml、手動実行、schedule）

### Phase 5：品質

14. 単体テスト（raw HTML fixture を固定して回帰）
15. ログの充実（URL、day、division、フェーズ）

---

## 15. 受入条件（Definition of Done）

* 指定入力（本場所：YYYYMM）で `fact_bout_daily.csv` と `dim_shikona_by_basho.csv` が生成/更新される
* 取組は rid で名寄せされ、`event_id/event_type/is_regular` により通常日程と非通常イベントが区別できる
* `bout_no` が採番され、一意キーで upsert/置換が成立する
* GitHub Actions で同一処理が動き、差分があればコミットされる
* rawキャッシュONの場合、再実行でfetchを省略できる

