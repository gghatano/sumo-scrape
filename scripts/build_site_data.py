"""Build JSON data files for the sumo visualization website.

Usage:
    uv run python scripts/build_site_data.py
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACT_CSV = ROOT / "data" / "fact" / "fact_bout_daily.csv"
DIM_CSV = ROOT / "data" / "dim" / "dim_shikona_by_basho.csv"
OUT_DIR = ROOT / "docs" / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rank_to_numeric(rank: str) -> int | None:
    """Convert a rank string to a numeric value for comparison.

    Lower number = higher rank.
    Y=0, O=1, S=2, K=3, M1=4, M2=5, ...
    J1=20+, Ms=100+, Sd=200+, Jd=300+, Jk=400+
    """
    if not rank:
        return None
    # Strip east/west suffix
    r = rank.rstrip("ew")
    if r == "Y":
        return 0
    if r == "O":
        return 1
    if r.startswith("S"):
        n = re.sub(r"^S", "", r)
        return 2 if not n else 2  # S1, S2 are all sekiwake
    if r.startswith("K"):
        n = re.sub(r"^K", "", r)
        return 3 if not n else 3
    if r.startswith("M") and not r.startswith("Ms"):
        n = re.sub(r"^M", "", r)
        return 3 + int(n) if n else 4  # M1=4, M2=5, ...
    if r.startswith("J") and not r.startswith("Jd") and not r.startswith("Jk"):
        n = re.sub(r"^J", "", r)
        return 20 + (int(n) if n else 1)
    if r.startswith("Ms"):
        n = re.sub(r"^Ms", "", r)
        return 100 + (int(n) if n else 1)
    if r.startswith("Sd"):
        n = re.sub(r"^Sd", "", r)
        return 200 + (int(n) if n else 1)
    if r.startswith("Jd"):
        n = re.sub(r"^Jd", "", r)
        return 300 + (int(n) if n else 1)
    if r.startswith("Jk"):
        n = re.sub(r"^Jk", "", r)
        return 400 + (int(n) if n else 1)
    return None


def load_bouts() -> list[dict]:
    with open(FACT_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_dim() -> list[dict]:
    with open(DIM_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def latest_shikona(dim_rows: list[dict]) -> dict[int, str]:
    """Return {rid: shikona} using the latest basho for each rid."""
    best: dict[int, tuple[str, str]] = {}
    for row in dim_rows:
        rid = int(row["rid"])
        basho = row["basho"]
        if rid not in best or basho > best[rid][0]:
            best[rid] = (basho, row["shikona_at_basho"])
    return {rid: v[1] for rid, v in best.items()}


def write_json(filename: str, data: object) -> None:
    path = OUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  wrote {path} ({path.stat().st_size:,} bytes)")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_kimarite_ranking(bouts: list[dict]) -> dict:
    maku_counts: dict[str, int] = defaultdict(int)
    all_counts: dict[str, int] = defaultdict(int)
    maku_total = 0
    all_total = 0

    for b in bouts:
        if b["result_type"] == "fusen":
            continue
        k = b["kimarite"]
        all_counts[k] += 1
        all_total += 1
        if b["division"] == "Makuuchi":
            maku_counts[k] += 1
            maku_total += 1

    def top20(counts: dict[str, int], total: int) -> list[dict]:
        items = sorted(counts.items(), key=lambda x: -x[1])[:20]
        return [
            {"kimarite": k, "count": c, "pct": round(c / total * 100, 1)}
            for k, c in items
        ]

    return {
        "makuuchi": top20(maku_counts, maku_total),
        "all": top20(all_counts, all_total),
    }


def build_kimarite_trend(bouts: list[dict]) -> dict:
    # Find top 5 kimarite in makuuchi overall
    counts: dict[str, int] = defaultdict(int)
    for b in bouts:
        if b["division"] == "Makuuchi" and b["result_type"] != "fusen":
            counts[b["kimarite"]] += 1
    top5 = [k for k, _ in sorted(counts.items(), key=lambda x: -x[1])[:5]]

    # Per year counts
    year_total: dict[int, int] = defaultdict(int)
    year_tech: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for b in bouts:
        if b["division"] == "Makuuchi" and b["result_type"] != "fusen":
            year = int(b["basho"][:4])
            year_total[year] += 1
            k = b["kimarite"]
            if k in top5:
                year_tech[year][k] += 1

    years = sorted(year_total.keys())
    techniques = {}
    for t in top5:
        techniques[t] = [
            round(year_tech[y].get(t, 0) / year_total[y] * 100, 1) if year_total[y] else 0
            for y in years
        ]
    return {"years": years, "techniques": techniques}


def build_rikishi_wins(bouts: list[dict], dim_rows: list[dict]) -> list[dict]:
    shikona_map = latest_shikona(dim_rows)
    wins: dict[int, int] = defaultdict(int)
    losses: dict[int, int] = defaultdict(int)
    basho_set: dict[int, set] = defaultdict(set)

    for b in bouts:
        if b["division"] != "Makuuchi":
            continue
        east = int(b["east_rid"])
        west = int(b["west_rid"])
        basho = b["basho"]
        basho_set[east].add(basho)
        basho_set[west].add(basho)
        if b["winner_side"] == "E":
            wins[east] += 1
            losses[west] += 1
        else:
            wins[west] += 1
            losses[east] += 1

    # Sort by wins descending
    ranked = sorted(wins.keys(), key=lambda r: -wins[r])[:30]
    result = []
    for i, rid in enumerate(ranked, 1):
        w = wins[rid]
        l = losses[rid]
        result.append({
            "rank": i,
            "shikona": shikona_map.get(rid, str(rid)),
            "wins": w,
            "losses": l,
            "basho_count": len(basho_set[rid]),
            "win_rate": round(w / (w + l) * 100, 1) if (w + l) else 0,
        })
    return result


def build_yokozuna_dominance(bouts: list[dict], dim_rows: list[dict]) -> dict:
    shikona_map = latest_shikona(dim_rows)

    # Find yokozuna rids and their yokozuna basho
    yokozuna_basho: dict[int, set[str]] = defaultdict(set)
    for row in dim_rows:
        if row["rank"] in ("Ye", "Yw"):
            yokozuna_basho[int(row["rid"])].add(row["basho"])

    yokozuna_rids = set(yokozuna_basho.keys())

    # Accumulate wins/losses per rid per basho in makuuchi
    stats: dict[int, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"wins": 0, "losses": 0})
    )
    for b in bouts:
        if b["division"] != "Makuuchi":
            continue
        basho = b["basho"]
        east = int(b["east_rid"])
        west = int(b["west_rid"])
        if east in yokozuna_rids and basho in yokozuna_basho[east]:
            if b["winner_side"] == "E":
                stats[east][basho]["wins"] += 1
            else:
                stats[east][basho]["losses"] += 1
        if west in yokozuna_rids and basho in yokozuna_basho[west]:
            if b["winner_side"] == "W":
                stats[west][basho]["wins"] += 1
            else:
                stats[west][basho]["losses"] += 1

    rikishi_list = []
    for rid in sorted(yokozuna_rids):
        data = []
        for basho in sorted(stats[rid].keys()):
            s = stats[rid][basho]
            w, l = s["wins"], s["losses"]
            total = w + l
            data.append({
                "basho": basho,
                "wins": w,
                "losses": l,
                "win_rate": round(w / total * 100, 1) if total else 0,
            })
        if data:
            rikishi_list.append({
                "shikona": shikona_map.get(rid, str(rid)),
                "rid": rid,
                "data": data,
            })

    return {"rikishi": rikishi_list}


def build_upset_index(bouts: list[dict]) -> dict:
    basho_total: dict[str, int] = defaultdict(int)
    basho_upset: dict[str, int] = defaultdict(int)

    for b in bouts:
        if b["division"] != "Makuuchi":
            continue
        basho = b["basho"]
        east_num = rank_to_numeric(b["east_rank"])
        west_num = rank_to_numeric(b["west_rank"])
        if east_num is None or west_num is None:
            continue
        basho_total[basho] += 1
        # Upset = lower-ranked (higher number) beats higher-ranked (lower number)
        if east_num != west_num:
            if b["winner_side"] == "E" and east_num > west_num:
                basho_upset[basho] += 1
            elif b["winner_side"] == "W" and west_num > east_num:
                basho_upset[basho] += 1

    basho_list = sorted(basho_total.keys())
    upset_rates = []
    for bs in basho_list:
        total = basho_total[bs]
        rate = round(basho_upset[bs] / total * 100, 1) if total else 0
        upset_rates.append(rate)

    avg = round(sum(upset_rates) / len(upset_rates), 1) if upset_rates else 0
    return {
        "basho_list": basho_list,
        "upset_rate": upset_rates,
        "avg_upset_rate": avg,
    }


def build_winning_streaks(bouts: list[dict], dim_rows: list[dict]) -> list[dict]:
    shikona_map = latest_shikona(dim_rows)

    # Filter makuuchi bouts, sorted by basho then day then bout_no
    maku = [b for b in bouts if b["division"] == "Makuuchi"]
    maku.sort(key=lambda b: (b["basho"], int(b["day"]), int(b["bout_no"])))

    # Track per-rikishi streaks
    # current_streak[rid] = (count, start_basho, start_day)
    current: dict[int, tuple[int, str, int]] = {}
    best: dict[int, tuple[int, str, int, str, int]] = {}  # rid -> (count, start_basho, start_day, end_basho, end_day)

    def update_best(rid: int, streak: int, start_basho: str, start_day: int, end_basho: str, end_day: int) -> None:
        if rid not in best or streak > best[rid][0]:
            best[rid] = (streak, start_basho, start_day, end_basho, end_day)

    for b in maku:
        if b["result_type"] == "fusen":
            # fusen does not count as win or break streak — skip entirely
            continue
        east = int(b["east_rid"])
        west = int(b["west_rid"])
        basho = b["basho"]
        day = int(b["day"])
        winner = east if b["winner_side"] == "E" else west
        loser = west if b["winner_side"] == "E" else east

        # Winner extends streak
        if winner in current:
            cnt, sb, sd = current[winner]
            current[winner] = (cnt + 1, sb, sd)
        else:
            current[winner] = (1, basho, day)

        # Loser ends streak
        if loser in current:
            cnt, sb, sd = current[loser]
            update_best(loser, cnt, sb, sd, basho, day)
            del current[loser]

    # Flush remaining streaks
    for rid, (cnt, sb, sd) in current.items():
        # We don't know the exact end, use last bout info — approximate
        update_best(rid, cnt, sb, sd, "", 0)

    # Build ranking
    all_streaks = [(rid, *v) for rid, v in best.items()]
    all_streaks.sort(key=lambda x: -x[1])
    top20 = all_streaks[:20]

    result = []
    for i, (rid, streak, sb, sd, eb, ed) in enumerate(top20, 1):
        result.append({
            "rank": i,
            "shikona": shikona_map.get(rid, str(rid)),
            "streak": streak,
            "start_basho": sb,
            "end_basho": eb,
            "start_day": sd,
            "end_day": ed,
        })
    return result


def build_summary_stats(bouts: list[dict], dim_rows: list[dict]) -> dict:
    shikona_map = latest_shikona(dim_rows)
    total_bouts = len(bouts)
    basho_set = {b["basho"] for b in bouts}
    rid_set = {int(b["east_rid"]) for b in bouts} | {int(b["west_rid"]) for b in bouts}
    years = sorted({b["basho"][:4] for b in bouts})
    maku_bouts = sum(1 for b in bouts if b["division"] == "Makuuchi")

    # Most common kimarite (excluding fusen)
    ki_counts: dict[str, int] = defaultdict(int)
    for b in bouts:
        if b["result_type"] != "fusen":
            ki_counts[b["kimarite"]] += 1
    most_ki = max(ki_counts, key=ki_counts.get) if ki_counts else ""

    # Most wins rikishi (makuuchi)
    wins: dict[int, int] = defaultdict(int)
    for b in bouts:
        if b["division"] == "Makuuchi":
            winner_rid = int(b["east_rid"]) if b["winner_side"] == "E" else int(b["west_rid"])
            wins[winner_rid] += 1
    top_rid = max(wins, key=wins.get) if wins else 0

    return {
        "total_bouts": total_bouts,
        "total_basho": len(basho_set),
        "total_rikishi": len(rid_set),
        "year_range": f"{years[0]}-{years[-1]}" if years else "",
        "makuuchi_bouts": maku_bouts,
        "most_common_kimarite": most_ki,
        "most_wins_rikishi": shikona_map.get(top_rid, str(top_rid)),
    }


# ---------------------------------------------------------------------------
# 7-7 Senshuraku & Star Trading Analysis
# ---------------------------------------------------------------------------

def _compute_records_entering_day15(bouts: list[dict]) -> dict[str, dict[int, tuple[int, int]]]:
    """Compute each wrestler's W-L record entering day 15 for each basho.

    Returns {basho: {rid: (wins, losses)}} for Makuuchi bouts on days 1-14.
    Only includes regular bouts (no playoffs).
    """
    records: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))

    for b in bouts:
        if b["division"] != "Makuuchi":
            continue
        if b["result_type"] == "playoff":
            continue
        day = int(b["day"])
        if day >= 15:
            continue
        basho = b["basho"]
        east = int(b["east_rid"])
        west = int(b["west_rid"])
        if b["winner_side"] == "E":
            records[basho][east][0] += 1
            records[basho][west][1] += 1
        else:
            records[basho][west][0] += 1
            records[basho][east][1] += 1

    return {
        basho: {rid: (wl[0], wl[1]) for rid, wl in rids.items()}
        for basho, rids in records.items()
    }


def build_nanahachi_analysis(bouts: list[dict], dim_rows: list[dict]) -> dict:
    """Analyze day-15 win rate for wrestlers entering with 7-7 records."""
    shikona_map = latest_shikona(dim_rows)
    records = _compute_records_entering_day15(bouts)

    # Collect day 15 bouts
    day15_bouts = [
        b for b in bouts
        if b["division"] == "Makuuchi"
        and int(b["day"]) == 15
        and b["result_type"] != "playoff"
    ]

    # --- Overall 7-7 win rate ---
    overall_bouts = 0
    overall_wins = 0

    # --- By opponent record ---
    by_opp: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # "W-L" -> [bouts, wins]

    # --- By year ---
    by_year: dict[int, list[int]] = defaultdict(lambda: [0, 0])

    # --- Both 7-7 ---
    both_77_bouts = 0
    both_77_east_wins = 0

    # --- Baseline: non-7-7 bouts on day 15 ---
    baseline_bouts = 0
    baseline_higher_rank_wins = 0

    for b in day15_bouts:
        basho = b["basho"]
        east = int(b["east_rid"])
        west = int(b["west_rid"])
        year = int(basho[:4])

        east_rec = records.get(basho, {}).get(east)
        west_rec = records.get(basho, {}).get(west)
        if east_rec is None or west_rec is None:
            continue

        east_77 = east_rec == (7, 7)
        west_77 = west_rec == (7, 7)

        if east_77 and west_77:
            both_77_bouts += 1
            if b["winner_side"] == "E":
                both_77_east_wins += 1

        if east_77 or west_77:
            # Perspective of the 7-7 wrestler
            for is_east in [True, False]:
                rid_77 = east if is_east else west
                rid_opp = west if is_east else east
                rec_77 = east_rec if is_east else west_rec
                rec_opp = west_rec if is_east else east_rec

                if rec_77 != (7, 7):
                    continue
                if rec_77 == (7, 7) and rec_opp == (7, 7):
                    # Skip double-counting: only count from east perspective
                    if not is_east:
                        continue

                won = (is_east and b["winner_side"] == "E") or (
                    not is_east and b["winner_side"] == "W"
                )
                overall_bouts += 1
                if won:
                    overall_wins += 1

                opp_label = f"{rec_opp[0]}-{rec_opp[1]}"
                by_opp[opp_label][0] += 1
                if won:
                    by_opp[opp_label][1] += 1

                by_year[year][0] += 1
                if won:
                    by_year[year][1] += 1

    # Build by_opponent_record sorted by frequency
    opp_list = []
    for label, (cnt, wins) in sorted(by_opp.items(), key=lambda x: -x[1][0]):
        opp_list.append({
            "opp_record": label,
            "bouts": cnt,
            "wins": wins,
            "win_rate": round(wins / cnt * 100, 1) if cnt else 0,
        })

    # Build by_year
    year_list = []
    for y in sorted(by_year.keys()):
        cnt, wins = by_year[y]
        year_list.append({
            "year": y,
            "bouts": cnt,
            "wins": wins,
            "win_rate": round(wins / cnt * 100, 1) if cnt else 0,
        })

    return {
        "overall": {
            "total_bouts": overall_bouts,
            "wins": overall_wins,
            "win_rate": round(overall_wins / overall_bouts * 100, 1) if overall_bouts else 0,
            "expected_rate": 50.0,
        },
        "by_opponent_record": opp_list,
        "by_year": year_list,
        "both_77": {
            "total_bouts": both_77_bouts,
            "east_wins": both_77_east_wins,
            "note": "Both 7-7: no incentive asymmetry, expect ~50%",
        },
    }


def build_star_trading_analysis(bouts: list[dict], dim_rows: list[dict]) -> dict:
    """Detect potential star trading patterns.

    Analyzes:
    1. Record matchup matrix on day 15 (win rate by wrestler/opponent record combo)
    2. Yearly trend of 7-7 vs kachikoshi win rate
    3. Reciprocity: If A beat B when A was 7-7, does B later beat A when B is 7-7?
    """
    shikona_map = latest_shikona(dim_rows)
    records = _compute_records_entering_day15(bouts)

    day15_bouts = [
        b for b in bouts
        if b["division"] == "Makuuchi"
        and int(b["day"]) == 15
        and b["result_type"] != "playoff"
    ]

    # --- 1. Record matchup matrix ---
    # Key: (wrestler_record_str, opponent_record_str) -> [bouts, wrestler_wins]
    matchup: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])

    for b in day15_bouts:
        basho = b["basho"]
        east = int(b["east_rid"])
        west = int(b["west_rid"])
        east_rec = records.get(basho, {}).get(east)
        west_rec = records.get(basho, {}).get(west)
        if east_rec is None or west_rec is None:
            continue

        # From east perspective
        e_label = f"{east_rec[0]}-{east_rec[1]}"
        w_label = f"{west_rec[0]}-{west_rec[1]}"
        e_won = b["winner_side"] == "E"

        matchup[(e_label, w_label)][0] += 1
        if e_won:
            matchup[(e_label, w_label)][1] += 1
        matchup[(w_label, e_label)][0] += 1
        if not e_won:
            matchup[(w_label, e_label)][1] += 1

    # Focus on key matchups
    key_matchups = []
    for (wr, opr), (cnt, wins) in sorted(matchup.items(), key=lambda x: -x[1][0]):
        if cnt < 10:
            continue
        w_wins = int(wr.split("-")[0])
        w_losses = int(wr.split("-")[1])
        if w_wins + w_losses != 14:
            continue  # Only full 14-day records
        key_matchups.append({
            "wrestler_record": wr,
            "opponent_record": opr,
            "bouts": cnt,
            "wrestler_wins": wins,
            "win_rate": round(wins / cnt * 100, 1),
        })

    # --- 2. Yearly trend: 7-7 vs kachikoshi (8-6 or better) ---
    #   Baseline: same wrestlers' win rate on days 1-14 (non-critical bouts)
    yearly_77: dict[int, list[int]] = defaultdict(lambda: [0, 0])

    for b in day15_bouts:
        basho = b["basho"]
        year = int(basho[:4])
        east = int(b["east_rid"])
        west = int(b["west_rid"])
        east_rec = records.get(basho, {}).get(east)
        west_rec = records.get(basho, {}).get(west)
        if east_rec is None or west_rec is None:
            continue

        for is_east in [True, False]:
            rec_me = east_rec if is_east else west_rec
            rec_opp = west_rec if is_east else east_rec
            won = (is_east and b["winner_side"] == "E") or (
                not is_east and b["winner_side"] == "W"
            )

            if rec_me == (7, 7) and rec_opp[0] >= 8:
                yearly_77[year][0] += 1
                if won:
                    yearly_77[year][1] += 1

    # Baseline: win rate of lower-ranked wrestler on days 1-14 in Makuuchi
    yearly_baseline: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for b in bouts:
        if b["division"] != "Makuuchi" or b["result_type"] != "normal":
            continue
        day = int(b["day"])
        if day >= 15:
            continue
        year = int(b["basho"][:4])
        e_num = rank_to_numeric(b["east_rank"])
        w_num = rank_to_numeric(b["west_rank"])
        if e_num is None or w_num is None or e_num == w_num:
            continue
        # From perspective of the lower-ranked (higher number) wrestler
        lower_is_east = e_num > w_num
        lower_won = (lower_is_east and b["winner_side"] == "E") or (
            not lower_is_east and b["winner_side"] == "W"
        )
        yearly_baseline[year][0] += 1
        if lower_won:
            yearly_baseline[year][1] += 1

    yearly_trend = []
    for y in sorted(set(list(yearly_77.keys()) + list(yearly_baseline.keys()))):
        n_cnt, n_wins = yearly_77.get(y, [0, 0])
        b_cnt, b_wins = yearly_baseline.get(y, [0, 0])
        yearly_trend.append({
            "year": y,
            "nanahachi_vs_kachikoshi_bouts": n_cnt,
            "nanahachi_vs_kachikoshi_rate": round(n_wins / n_cnt * 100, 1) if n_cnt else None,
            "baseline_bouts": b_cnt,
            "baseline_rate": round(b_wins / b_cnt * 100, 1) if b_cnt else None,
        })

    # --- 3. Reciprocity analysis ---
    # Track: when A was 7-7 and beat B, record this as a "favor"
    # Later, when B is 7-7 and faces A, does B win more often?
    favors: dict[tuple[int, int], list[str]] = defaultdict(list)  # (winner, loser) -> [basho, ...]

    for b in day15_bouts:
        basho = b["basho"]
        east = int(b["east_rid"])
        west = int(b["west_rid"])
        east_rec = records.get(basho, {}).get(east)
        west_rec = records.get(basho, {}).get(west)
        if east_rec is None or west_rec is None:
            continue

        winner = east if b["winner_side"] == "E" else west
        loser = west if b["winner_side"] == "E" else east
        winner_rec = east_rec if b["winner_side"] == "E" else west_rec
        loser_rec = west_rec if b["winner_side"] == "E" else east_rec

        # 7-7 wrestler won against kachikoshi opponent
        if winner_rec == (7, 7) and loser_rec[0] >= 8:
            favors[(winner, loser)].append(basho)

    # Now check: for each favor, did the loser later get a "return favor"?
    reciprocal_total = 0
    reciprocal_returned = 0

    for (orig_winner, orig_loser), basho_list in favors.items():
        # Check if orig_loser was ever 7-7 and beat orig_winner later
        return_favors = favors.get((orig_loser, orig_winner), [])
        for b1 in basho_list:
            for b2 in return_favors:
                if b2 > b1:
                    reciprocal_total += 1
                    reciprocal_returned += 1
                    break
            else:
                # Check if they even faced each other with reversed roles
                reciprocal_total += 1

    # Simpler approach: just count pairs with mutual favors
    mutual_pairs = 0
    total_favor_pairs = 0
    for (w, l) in favors:
        if (l, w) in favors:
            # Check temporal ordering: at least one case where l,w happened after w,l
            if any(b2 > b1 for b1 in favors[(w, l)] for b2 in favors[(l, w)]):
                mutual_pairs += 1
        total_favor_pairs += 1

    # Top reciprocal pairs
    pair_details = []
    seen = set()
    for (w, l) in favors:
        pair_key = (min(w, l), max(w, l))
        if pair_key in seen:
            continue
        seen.add(pair_key)
        a_to_b = len(favors.get((w, l), []))
        b_to_a = len(favors.get((l, w), []))
        if a_to_b > 0 and b_to_a > 0:
            pair_details.append({
                "rikishi_a": shikona_map.get(w, str(w)),
                "rikishi_b": shikona_map.get(l, str(l)),
                "a_favors_b": a_to_b,
                "b_favors_a": b_to_a,
                "total": a_to_b + b_to_a,
            })
    pair_details.sort(key=lambda x: -x["total"])

    return {
        "record_matchup_matrix": key_matchups[:30],
        "yearly_trend": yearly_trend,
        "reciprocity": {
            "total_favor_pairs": total_favor_pairs,
            "mutual_pairs": mutual_pairs,
            "mutual_rate": round(mutual_pairs / total_favor_pairs * 100, 1) if total_favor_pairs else 0,
            "top_pairs": pair_details[:15],
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading data...")
    bouts = load_bouts()
    dim = load_dim()
    print(f"  {len(bouts):,} bouts, {len(dim):,} dim rows")

    print("Building kimarite_ranking.json...")
    write_json("kimarite_ranking.json", build_kimarite_ranking(bouts))

    print("Building kimarite_trend.json...")
    write_json("kimarite_trend.json", build_kimarite_trend(bouts))

    print("Building rikishi_wins.json...")
    write_json("rikishi_wins.json", build_rikishi_wins(bouts, dim))

    print("Building yokozuna_dominance.json...")
    write_json("yokozuna_dominance.json", build_yokozuna_dominance(bouts, dim))

    print("Building upset_index.json...")
    write_json("upset_index.json", build_upset_index(bouts))

    print("Building winning_streaks.json...")
    write_json("winning_streaks.json", build_winning_streaks(bouts, dim))

    print("Building summary_stats.json...")
    write_json("summary_stats.json", build_summary_stats(bouts, dim))

    print("Building nanahachi_analysis.json...")
    write_json("nanahachi_analysis.json", build_nanahachi_analysis(bouts, dim))

    print("Building star_trading_analysis.json...")
    write_json("star_trading_analysis.json", build_star_trading_analysis(bouts, dim))

    print("Done!")


if __name__ == "__main__":
    main()
