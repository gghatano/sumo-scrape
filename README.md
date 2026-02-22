# SumoDB Scraping & CSV Generation

## Overview

Fetches sumo bout data from SumoDB, parses results and banzuke pages, and generates CSVs with r-id consolidation.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)

## Install

```bash
uv sync
```

## Usage

```bash
uv run python -m sumodata --basho 202501
```

### Options

| Option | Description | Default |
|---|---|---|
| `--basho YYYYMM` | Target basho in YYYYMM format (required) | -- |
| `--force` | Force replace rows for the target event (instead of upsert) | off |
| `--raw-cache on\|off` | HTML cache mode | `on` |
| `--playoff on\|off` | Playoff detection and fetch | `on` |
| `--log-level INFO\|DEBUG` | Logging level | `INFO` |

## Output Files

| File | Description |
|---|---|
| `data/fact/fact_bout_daily.csv` | Daily bout records (fact table) |
| `data/dim/dim_shikona_by_basho.csv` | Shikona-by-basho dimension table |

## Historical Data

To fetch historical honbasho data (2000--2024), use the helper script:

```bash
./scripts/run_local.sh historical
```

See `scripts/run_local.sh` for details.
