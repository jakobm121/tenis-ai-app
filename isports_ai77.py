import os
import json
import math
import time
import hashlib
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

ISPORTS_API_KEY = os.getenv("ISPORTS_API_KEY")

BASE_URL = "http://api.isportsapi.com"
TZ_NAME = "Europe/Ljubljana"

PREDICTIONS_FILE = "predictions.json"
RESULTS_FILE = "results.json"
CACHE_DIR = "isports_cache"

DEBUG = True

REQUEST_TIMEOUT = 30

TIME_WINDOW_MIN_MINUTES = 45
TIME_WINDOW_MAX_HOURS = 24

MAX_FINAL_PICKS = 5
MAX_MATCHES_TO_PROCESS = 80
MAX_LEAGUE_HISTORY_CALLS = 14

LEAGUE_CACHE_HOURS = 24

MIN_LEAGUE_HISTORY_MATCHES = 40
MIN_TEAM_HISTORY_MATCHES = 5
TEAM_FORM_MATCHES = 10

MIN_BOOKMAKERS_H2H = 5
MIN_BOOKMAKERS_TOTALS = 5

MIN_EDGE = 0.035
MIN_QUALITY_SCORE = 58

ODDS_MIN = 1.45
ODDS_MAX = 3.60

ENABLE_DRAW = False

MARKET_LIMITS = {
    "home": 2,
    "away": 2,
    "over_2_5": 2,
    "under_2_5": 2,
    "draw": 1,
}

BLOCKED_LEAGUE_KEYWORDS = [
    "women",
    "(w)",
    "u17",
    "u18",
    "u19",
    "u20",
    "u21",
    "u23",
    "youth",
    "junior",
    "junioren",
    "reserve",
    "reserves",
    "amateur",
    "friendly",
    "friendlies",
    "exhibition",
    "esoccer",
    "virtual",
]

ALLOWED_STATUS_UPCOMING = {0}
FINISHED_STATUSES = {-1}
STORNO_STATUSES = {-10, -11, -14}


def debug(msg):
    if DEBUG:
        print(msg)


def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)


def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=None):
    try:
        return int(value)
    except Exception:
        return default


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def normalize(text):
    return " ".join(str(text or "").strip().lower().split())


def median_or_none(values):
    cleaned = [safe_float(v) for v in values]
    cleaned = [v for v in cleaned if v is not None and v > 1.0]
    if not cleaned:
        return None
    return float(statistics.median(cleaned))


def mean_or_none(values):
    cleaned = [safe_float(v) for v in values]
    cleaned = [v for v in cleaned if v is not None]
    if not cleaned:
        return None
    return sum(cleaned) / len(cleaned)


def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def timestamp_to_local(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), ZoneInfo(TZ_NAME))


def build_pick_id(match_id, bucket, bet, line):
    raw = f"{match_id}|{bucket}|{bet}|{line}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def load_json(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, type(default)):
                return data
            return default
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


def api_get(path, params=None):
    if not ISPORTS_API_KEY:
        raise RuntimeError("Missing ISPORTS_API_KEY environment variable.")

    params = params.copy() if params else {}
    params["api_key"] = ISPORTS_API_KEY

    url = BASE_URL + path

    res = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

    if res.status_code != 200:
        raise RuntimeError(f"HTTP {res.status_code} for {path}: {res.text[:300]}")

    data = res.json()

    code = data.get("code")
    if code != 0:
        raise RuntimeError(f"API code={code} for {path}: {data.get('message')}")

    return data.get("data", [])


def fetch_schedule_by_date(date_str):
    debug(f"FETCH schedule date={date_str}")
    return api_get("/sport/football/schedule", {"date": date_str})


def fetch_league_history(league_id):
    ensure_dirs()

    cache_path = os.path.join(CACHE_DIR, f"league_{league_id}.json")

    if os.path.exists(cache_path):
        age_seconds = time.time() - os.path.getmtime(cache_path)
        if age_seconds < LEAGUE_CACHE_HOURS * 3600:
            data = load_json(cache_path, [])
            if isinstance(data, list) and data:
                debug(f"CACHE league={league_id} matches={len(data)}")
                return data

    debug(f"FETCH league history leagueID={league_id}")
    data = api_get("/sport/football/schedule", {"leagueID": str(league_id)})

    save_json(cache_path, data)
    return data


def fetch_odds_main():
    debug("FETCH odds/main")
    data = api_get("/sport/football/odds/main")

    if not isinstance(data, dict):
        return {}

    return data


def is_blocked_league(league_name):
    n = normalize(league_name)

    for word in BLOCKED_LEAGUE_KEYWORDS:
        if word in n:
            return True

    return False


def parse_europe_odds(rows):
    """
    Format:
    matchId, companyId, currentHome, currentDraw, currentAway,
    openingHome, openingDraw, openingAway, updateTime, closed, status
    """
    by_match = defaultdict(lambda: {
        "home": [],
        "draw": [],
        "away": [],
        "open_home": [],
        "open_draw": [],
        "open_away": [],
        "bookmakers": set(),
    })

    for row in rows or []:
        parts = str(row).split(",")

        if len(parts) < 11:
            continue

        match_id = parts[0]
        company_id = parts[1]

        home = safe_float(parts[2])
        draw = safe_float(parts[3])
        away = safe_float(parts[4])

        open_home = safe_float(parts[5])
        open_draw = safe_float(parts[6])
        open_away = safe_float(parts[7])

        closed = str(parts[9]).lower() == "true"

        if closed:
            continue

        if home and home > 1:
            by_match[match_id]["home"].append(home)
        if draw and draw > 1:
            by_match[match_id]["draw"].append(draw)
        if away and away > 1:
            by_match[match_id]["away"].append(away)

        if open_home and open_home > 1:
            by_match[match_id]["open_home"].append(open_home)
        if open_draw and open_draw > 1:
            by_match[match_id]["open_draw"].append(open_draw)
        if open_away and open_away > 1:
            by_match[match_id]["open_away"].append(open_away)

        by_match[match_id]["bookmakers"].add(company_id)

    return by_match


def hk_to_decimal(value):
    v = safe_float(value)
    if v is None:
        return None
    return round(v + 1.0, 4)


def parse_over_under(rows):
    """
    Format:
    matchId, companyId, currentLine, currentOverHK, currentUnderHK,
    openingLine, openingOverHK, openingUnderHK, updateTime, closed, status
    """
    by_match = defaultdict(lambda: defaultdict(lambda: {
        "over": [],
        "under": [],
        "open_line": [],
        "open_over": [],
        "open_under": [],
        "bookmakers": set(),
    }))

    for row in rows or []:
        parts = str(row).split(",")

        if len(parts) < 11:
            continue

        match_id = parts[0]
        company_id = parts[1]

        line = safe_float(parts[2])
        over_dec = hk_to_decimal(parts[3])
        under_dec = hk_to_decimal(parts[4])

        open_line = safe_float(parts[5])
        open_over_dec = hk_to_decimal(parts[6])
        open_under_dec = hk_to_decimal(parts[7])

        closed = str(parts[9]).lower() == "true"

        if closed:
            continue

        if line is None:
            continue

        if over_dec and over_dec > 1:
            by_match[match_id][line]["over"].append(over_dec)
        if under_dec and under_dec > 1:
            by_match[match_id][line]["under"].append(under_dec)

        if open_line is not None:
            by_match[match_id][line]["open_line"].append(open_line)
        if open_over_dec and open_over_dec > 1:
            by_match[match_id][line]["open_over"].append(open_over_dec)
        if open_under_dec and open_under_dec > 1:
            by_match[match_id][line]["open_under"].append(open_under_dec)

        by_match[match_id][line]["bookmakers"].add(company_id)

    return by_match


def best_odds(values):
    cleaned = [safe_float(v) for v in values]
    cleaned = [v for v in cleaned if v is not None and v > 1]
    if not cleaned:
        return None
    return max(cleaned)


def implied_prob(odds):
    if odds is None or odds <= 1:
        return None
    return 1 / odds


def devig_two_way(over_odds, under_odds):
    over_med = median_or_none(over_odds)
    under_med = median_or_none(under_odds)

    if not over_med or not under_med:
        return None

    over_raw = 1 / over_med
    under_raw = 1 / under_med
    total = over_raw + under_raw

    if total <= 0:
        return None

    return {
        "over_prob": over_raw / total,
        "under_prob": under_raw / total,
        "over_median": over_med,
        "under_median": under_med,
    }


def devig_three_way(home_odds, draw_odds, away_odds):
    home_med = median_or_none(home_odds)
    draw_med = median_or_none(draw_odds)
    away_med = median_or_none(away_odds)

    if not home_med or not draw_med or not away_med:
        return None

    home_raw = 1 / home_med
    draw_raw = 1 / draw_med
    away_raw = 1 / away_med
    total = home_raw + draw_raw + away_raw

    if total <= 0:
        return None

    return {
        "home_prob": home_raw / total,
        "draw_prob": draw_raw / total,
        "away_prob": away_raw / total,
        "home_median": home_med,
        "draw_median": draw_med,
        "away_median": away_med,
    }


def finished_matches_only(matches, before_ts=None):
    out = []

    for m in matches:
        status = safe_int(m.get("status"))
        if status not in FINISHED_STATUSES:
            continue

        mt = safe_int(m.get("matchTime"))
        if before_ts and mt and mt >= before_ts:
            continue

        hs = safe_int(m.get("homeScore"))
        aw = safe_int(m.get("awayScore"))

        if hs is None or aw is None:
            continue

        out.append(m)

    out.sort(key=lambda x: safe_int(x.get("matchTime"), 0), reverse=True)
    return out


def build_team_stats(team_id, league_history, match_time_ts):
    finished = finished_matches_only(league_history, before_ts=match_time_ts)

    team_matches = []

    home_only = []
    away_only = []

    for m in finished:
        home_id = str(m.get("homeId"))
        away_id = str(m.get("awayId"))

        if str(team_id) not in {home_id, away_id}:
            continue

        team_matches.append(m)

        if str(team_id) == home_id:
            home_only.append(m)
        elif str(team_id) == away_id:
            away_only.append(m)

    recent = team_matches[:TEAM_FORM_MATCHES]
    recent_home = home_only[:TEAM_FORM_MATCHES]
    recent_away = away_only[:TEAM_FORM_MATCHES]

    def summarize(matches, mode):
        scored = []
        conceded = []
        totals = []
        btts = 0
        over25 = 0
        over35 = 0
        wins = 0
        draws = 0
        losses = 0
        corners_for = []
        corners_against = []

        for m in matches:
            hs = safe_int(m.get("homeScore"), 0)
            aw = safe_int(m.get("awayScore"), 0)

            hc = safe_int(m.get("homeCorner"), 0)
            ac = safe_int(m.get("awayCorner"), 0)

            is_home = str(m.get("homeId")) == str(team_id)

            gf = hs if is_home else aw
            ga = aw if is_home else hs

            cf = hc if is_home else ac
            ca = ac if is_home else hc

            scored.append(gf)
            conceded.append(ga)
            totals.append(hs + aw)

            corners_for.append(cf)
            corners_against.append(ca)

            if hs > 0 and aw > 0:
                btts += 1
            if hs + aw >= 3:
                over25 += 1
            if hs + aw >= 4:
                over35 += 1

            if gf > ga:
                wins += 1
            elif gf == ga:
                draws += 1
            else:
                losses += 1

        n = len(matches)
        if n == 0:
            return {
                "games": 0,
                "scored_avg": 1.20,
                "conceded_avg": 1.20,
                "total_avg": 2.40,
                "over25_rate": 0.50,
                "over35_rate": 0.25,
                "btts_rate": 0.50,
                "win_rate": 0.33,
                "draw_rate": 0.28,
                "loss_rate": 0.39,
                "corners_for_avg": 4.5,
                "corners_against_avg": 4.5,
            }

        return {
            "games": n,
            "scored_avg": mean_or_none(scored) or 1.20,
            "conceded_avg": mean_or_none(conceded) or 1.20,
            "total_avg": mean_or_none(totals) or 2.40,
            "over25_rate": over25 / n,
            "over35_rate": over35 / n,
            "btts_rate": btts / n,
            "win_rate": wins / n,
            "draw_rate": draws / n,
            "loss_rate": losses / n,
            "corners_for_avg": mean_or_none(corners_for) or 4.5,
            "corners_against_avg": mean_or_none(corners_against) or 4.5,
        }

    return {
        "overall": summarize(recent, "overall"),
        "home": summarize(recent_home, "home"),
        "away": summarize(recent_away, "away"),
        "total_team_matches": len(team_matches),
    }


def build_league_stats(league_history, match_time_ts):
    finished = finished_matches_only(league_history, before_ts=match_time_ts)

    recent = finished[:120]

    totals = []
    btts = 0
    draws = 0
    home_wins = 0
    away_wins = 0

    for m in recent:
        hs = safe_int(m.get("homeScore"), 0)
        aw = safe_int(m.get("awayScore"), 0)

        totals.append(hs + aw)

        if hs > 0 and aw > 0:
            btts += 1
        if hs == aw:
            draws += 1
        elif hs > aw:
            home_wins += 1
        else:
            away_wins += 1

    n = len(recent)
    if n == 0:
        return {
            "matches": 0,
            "avg_goals": 2.45,
            "btts_rate": 0.50,
            "draw_rate": 0.27,
            "home_win_rate": 0.43,
            "away_win_rate": 0.30,
        }

    return {
        "matches": n,
        "avg_goals": mean_or_none(totals) or 2.45,
        "btts_rate": btts / n,
        "draw_rate": draws / n,
        "home_win_rate": home_wins / n,
        "away_win_rate": away_wins / n,
    }


def expected_goals(home_stats, away_stats, league_stats):
    home_home = home_stats["home"]
    away_away = away_stats["away"]

    home_overall = home_stats["overall"]
    away_overall = away_stats["overall"]

    league_avg = league_stats["avg_goals"]

    home_attack = (
        home_home["scored_avg"] * 0.38
        + away_away["conceded_avg"] * 0.34
        + home_overall["scored_avg"] * 0.14
        + away_overall["conceded_avg"] * 0.14
    )

    away_attack = (
        away_away["scored_avg"] * 0.38
        + home_home["conceded_avg"] * 0.34
        + away_overall["scored_avg"] * 0.14
        + home_overall["conceded_avg"] * 0.14
    )

    home_form = home_overall["win_rate"] - home_overall["loss_rate"]
    away_form = away_overall["win_rate"] - away_overall["loss_rate"]

    home_attack += home_form * 0.10
    away_attack += away_form * 0.10

    current_total = home_attack + away_attack
    if current_total > 0:
        blended_total = (current_total * 0.72) + (league_avg * 0.28)
        scale = blended_total / current_total
        home_attack *= scale
        away_attack *= scale

    home_attack = clamp(home_attack, 0.35, 3.20)
    away_attack = clamp(away_attack, 0.25, 2.90)

    return home_attack, away_attack, home_attack + away_attack


def total_probs_from_expected(expected_total):
    max_goals = 10
    over25 = 0.0
    over35 = 0.0

    for g in range(max_goals + 1):
        p = poisson_pmf(g, expected_total)

        if g >= 3:
            over25 += p
        if g >= 4:
            over35 += p

    return {
        "over_2_5": clamp(over25, 0.05, 0.90),
        "under_2_5": clamp(1 - over25, 0.05, 0.90),
        "over_3_5": clamp(over35, 0.03, 0.82),
        "under_3_5": clamp(1 - over35, 0.10, 0.95),
    }


def h2h_probs_from_expected(exp_home, exp_away, league_stats):
    max_goals = 8

    home_win = 0.0
    draw = 0.0
    away_win = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_pmf(h, exp_home) * poisson_pmf(a, exp_away)

            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

    total = home_win + draw + away_win
    if total <= 0:
        return {
            "home": 0.43,
            "draw": league_stats["draw_rate"],
            "away": 0.30,
        }

    home_win /= total
    draw /= total
    away_win /= total

    league_draw = league_stats["draw_rate"]
    draw = draw * 0.82 + league_draw * 0.18

    total = home_win + draw + away_win

    return {
        "home": home_win / total,
        "draw": draw / total,
        "away": away_win / total,
    }


def movement_score(current_median, opening_median, side):
    if not current_median or not opening_median:
        return 0.0

    if side in {"home", "away", "draw"}:
        diff = opening_median - current_median
        return clamp(diff / 0.35, -1.0, 1.0) * 0.015

    return 0.0


def confidence_score(edge, bookmakers, odds, model_prob, implied, sample_ok):
    edge_score = clamp(edge / 0.12, 0.0, 1.0) * 42
    book_score = clamp(bookmakers / 12.0, 0.0, 1.0) * 20

    odds_score = 0
    if 1.70 <= odds <= 2.20:
        odds_score = 18
    elif 1.45 <= odds <= 2.80:
        odds_score = 12
    else:
        odds_score = 6

    separation_score = clamp(abs(model_prob - implied) / 0.20, 0.0, 1.0) * 12

    sample_score = 8 if sample_ok else 0

    return round(clamp(edge_score + book_score + odds_score + separation_score + sample_score, 1, 92), 1)


def quality_score(edge, confidence, bookmakers, expected_total=None, line=None):
    score = 0
    score += clamp(edge / 0.12, 0, 1) * 38
    score += clamp(confidence / 100, 0, 1) * 24
    score += clamp(bookmakers / 12, 0, 1) * 18

    if expected_total is not None and line is not None:
        goal_gap = abs(expected_total - line)
        score += clamp(goal_gap / 0.85, 0, 1) * 20
    else:
        score += 12

    return round(clamp(score, 1, 99), 1)


def build_reasoning(match, bet, odds, median_odds, edge, bookmakers, exp_home, exp_away, expected_total, league_name):
    edge_pct = round(edge * 100, 1)

    if "Over" in bet:
        return (
            f"{match} rates as a higher-goal spot in the AI77 iSports model. "
            f"The projected total is {expected_total:.2f}, supported by recent team scoring profiles and league baseline. "
            f"The best available price is {odds:.2f} versus a market median near {median_odds:.2f}, "
            f"creating an estimated value gap of +{edge_pct}% across {bookmakers} bookmakers."
        )

    if "Under" in bet:
        return (
            f"{match} projects as a more controlled scoring environment. "
            f"The model total is {expected_total:.2f}, with recent form and league tempo not fully supporting a high-event game. "
            f"The best available price is {odds:.2f} versus a market median near {median_odds:.2f}, "
            f"leaving an estimated value gap of +{edge_pct}% across {bookmakers} bookmakers."
        )

    return (
        f"{bet} is selected as a side-value position in {league_name}. "
        f"The expected goals profile is {exp_home:.2f} - {exp_away:.2f}. "
        f"The best price is {odds:.2f}, while the market median is around {median_odds:.2f}, "
        f"creating an estimated value gap of +{edge_pct}% across {bookmakers} bookmakers."
    )


def make_pick(match, bucket, bet, line, odds, median_odds, model_prob, bookmakers, exp_home, exp_away, expected_total, league_stats):
    local_dt = timestamp_to_local(match.get("matchTime"))

    implied = implied_prob(odds)
    edge = model_prob - implied

    league_name = match.get("leagueName", "Football")
    match_name = f"{match.get('homeName')} - {match.get('awayName')}"

    sample_ok = league_stats["matches"] >= MIN_LEAGUE_HISTORY_MATCHES

    confidence = confidence_score(
        edge=edge,
        bookmakers=bookmakers,
        odds=odds,
        model_prob=model_prob,
        implied=implied,
        sample_ok=sample_ok,
    )

    quality = quality_score(
        edge=edge,
        confidence=confidence,
        bookmakers=bookmakers,
        expected_total=expected_total if bucket in {"over_2_5", "under_2_5"} else None,
        line=line if bucket in {"over_2_5", "under_2_5"} else None,
    )

    return {
        "pick_id": build_pick_id(match.get("matchId"), bucket, bet, line),
        "match_id": match.get("matchId"),
        "fixture_id": match.get("matchId"),
        "model_version": "isports_ai77_v1_stats_odds",
        "date": local_dt.strftime("%Y-%m-%d") if local_dt else "",
        "time": local_dt.strftime("%H:%M") if local_dt else "",
        "sport": "football",
        "league": league_name,
        "league_id": match.get("leagueId"),
        "match": match_name,
        "bet": bet,
        "bucket": bucket,
        "line": line,
        "odds": round(odds, 2),
        "market_median_odds": round(median_odds, 2),
        "model_prob": round(model_prob, 4),
        "implied_prob": round(implied, 4),
        "edge": round(edge, 4),
        "expected_home_goals": round(exp_home, 2),
        "expected_away_goals": round(exp_away, 2),
        "expected_total_goals": round(expected_total, 2),
        "bookmakers_used": bookmakers,
        "confidence": confidence,
        "quality_score": quality,
        "stake": 1,
        "result": "pending",
        "reasoning": build_reasoning(
            match=match_name,
            bet=bet,
            odds=odds,
            median_odds=median_odds,
            edge=edge,
            bookmakers=bookmakers,
            exp_home=exp_home,
            exp_away=exp_away,
            expected_total=expected_total,
            league_name=league_name,
        ),
    }


def append_unique_history(predictions):
    history = load_json(RESULTS_FILE, [])
    if not isinstance(history, list):
        history = []

    existing = {
        item.get("pick_id")
        for item in history
        if isinstance(item, dict)
    }

    added = 0

    for pick in predictions:
        if pick["pick_id"] in existing:
            continue

        history.append(pick.copy())
        existing.add(pick["pick_id"])
        added += 1

    save_json(RESULTS_FILE, history)

    debug(f"HISTORY added={added} total={len(history)}")


def build_predictions():
    ensure_dirs()

    tz = ZoneInfo(TZ_NAME)
    now = datetime.now(tz)
    start_dt = now + timedelta(minutes=TIME_WINDOW_MIN_MINUTES)
    end_dt = now + timedelta(hours=TIME_WINDOW_MAX_HOURS)

    date_str = now.strftime("%Y-%m-%d")

    debug(f"NOW: {now}")
    debug(f"WINDOW: {start_dt} -> {end_dt}")

    schedule = fetch_schedule_by_date(date_str)
    odds_raw = fetch_odds_main()

    europe_odds = parse_europe_odds(odds_raw.get("europeOdds", []))
    over_under = parse_over_under(odds_raw.get("overUnder", []))

    debug(f"SCHEDULE matches={len(schedule)}")
    debug(f"EUROPE ODDS matches={len(europe_odds)}")
    debug(f"OVER/UNDER matches={len(over_under)}")

    upcoming = []

    for m in schedule:
        status = safe_int(m.get("status"))
        if status not in ALLOWED_STATUS_UPCOMING:
            continue

        local_dt = timestamp_to_local(m.get("matchTime"))
        if not local_dt:
            continue

        if local_dt < start_dt or local_dt > end_dt:
            continue

        league_name = m.get("leagueName", "")
        if is_blocked_league(league_name):
            continue

        match_id = str(m.get("matchId"))
        if match_id not in europe_odds and match_id not in over_under:
            continue

        upcoming.append(m)

    upcoming.sort(key=lambda x: safe_int(x.get("matchTime"), 0))

    if MAX_MATCHES_TO_PROCESS and len(upcoming) > MAX_MATCHES_TO_PROCESS:
        upcoming = upcoming[:MAX_MATCHES_TO_PROCESS]

    debug(f"UPCOMING filtered={len(upcoming)}")

    candidates = []
    league_history_cache = {}
    league_history_calls = 0

    for m in upcoming:
        try:
            match_id = str(m.get("matchId"))
            league_id = str(m.get("leagueId"))
            league_name = m.get("leagueName", "Football")
            home_id = str(m.get("homeId"))
            away_id = str(m.get("awayId"))
            match_time_ts = safe_int(m.get("matchTime"))

            if league_id not in league_history_cache:
                if league_history_calls >= MAX_LEAGUE_HISTORY_CALLS:
                    debug(f"SKIP league history call limit: {league_id} {league_name}")
                    continue

                league_history_cache[league_id] = fetch_league_history(league_id)
                league_history_calls += 1

            history = league_history_cache[league_id]

            league_stats = build_league_stats(history, match_time_ts)
            if league_stats["matches"] < MIN_LEAGUE_HISTORY_MATCHES:
                debug(f"SKIP low league sample {league_name}: {league_stats['matches']}")
                continue

            home_stats = build_team_stats(home_id, history, match_time_ts)
            away_stats = build_team_stats(away_id, history, match_time_ts)

            if home_stats["total_team_matches"] < MIN_TEAM_HISTORY_MATCHES:
                debug(f"SKIP low home sample {m.get('homeName')}: {home_stats['total_team_matches']}")
                continue

            if away_stats["total_team_matches"] < MIN_TEAM_HISTORY_MATCHES:
                debug(f"SKIP low away sample {m.get('awayName')}: {away_stats['total_team_matches']}")
                continue

            exp_home, exp_away, exp_total = expected_goals(home_stats, away_stats, league_stats)

            total_probs = total_probs_from_expected(exp_total)
            h2h_probs = h2h_probs_from_expected(exp_home, exp_away, league_stats)

            # 1X2 candidates
            h2h_market = europe_odds.get(match_id)
            if h2h_market:
                devig = devig_three_way(
                    h2h_market["home"],
                    h2h_market["draw"],
                    h2h_market["away"],
                )

                if devig:
                    h2h_candidates = [
                        ("home", m.get("homeName"), h2h_market["home"], h2h_market["open_home"], h2h_probs["home"], devig["home_median"]),
                        ("away", m.get("awayName"), h2h_market["away"], h2h_market["open_away"], h2h_probs["away"], devig["away_median"]),
                    ]

                    if ENABLE_DRAW:
                        h2h_candidates.append(
                            ("draw", "Draw", h2h_market["draw"], h2h_market["open_draw"], h2h_probs["draw"], devig["draw_median"])
                        )

                    for bucket, bet, odds_list, open_list, prob, median_odds in h2h_candidates:
                        bookmakers = len(odds_list)
                        if bookmakers < MIN_BOOKMAKERS_H2H:
                            continue

                        odds = best_odds(odds_list)
                        if not odds:
                            continue

                        if odds < ODDS_MIN or odds > ODDS_MAX:
                            continue

                        open_median = median_or_none(open_list)
                        prob = clamp(prob + movement_score(median_odds, open_median, bucket), 0.02, 0.95)

                        edge = prob - (1 / odds)
                        if edge < MIN_EDGE:
                            continue

                        pick = make_pick(
                            match=m,
                            bucket=bucket,
                            bet=bet,
                            line=None,
                            odds=odds,
                            median_odds=median_odds,
                            model_prob=prob,
                            bookmakers=bookmakers,
                            exp_home=exp_home,
                            exp_away=exp_away,
                            expected_total=exp_total,
                            league_stats=league_stats,
                        )

                        if pick["quality_score"] >= MIN_QUALITY_SCORE:
                            candidates.append(pick)

            # Over/Under 2.5 candidates
            totals_market = over_under.get(match_id)
            if totals_market:
                line_data = totals_market.get(2.5)

                if line_data:
                    bookmakers = min(len(line_data["over"]), len(line_data["under"]))

                    if bookmakers >= MIN_BOOKMAKERS_TOTALS:
                        devig_total = devig_two_way(line_data["over"], line_data["under"])

                        if devig_total:
                            total_candidates = [
                                ("over_2_5", "Over 2.5", line_data["over"], total_probs["over_2_5"], devig_total["over_median"]),
                                ("under_2_5", "Under 2.5", line_data["under"], total_probs["under_2_5"], devig_total["under_median"]),
                            ]

                            for bucket, bet, odds_list, prob, median_odds in total_candidates:
                                odds = best_odds(odds_list)
                                if not odds:
                                    continue

                                if odds < ODDS_MIN or odds > ODDS_MAX:
                                    continue

                                edge = prob - (1 / odds)
                                if edge < MIN_EDGE:
                                    continue

                                pick = make_pick(
                                    match=m,
                                    bucket=bucket,
                                    bet=bet,
                                    line=2.5,
                                    odds=odds,
                                    median_odds=median_odds,
                                    model_prob=prob,
                                    bookmakers=bookmakers,
                                    exp_home=exp_home,
                                    exp_away=exp_away,
                                    expected_total=exp_total,
                                    league_stats=league_stats,
                                )

                                if pick["quality_score"] >= MIN_QUALITY_SCORE:
                                    candidates.append(pick)

        except Exception as e:
            debug(f"MATCH BUILD ERROR {m.get('homeName')} - {m.get('awayName')}: {e}")

    candidates.sort(
        key=lambda x: (
            x["quality_score"],
            x["confidence"],
            x["edge"],
            x["bookmakers_used"],
            x["odds"],
        ),
        reverse=True,
    )

    debug("\nTOP CANDIDATES:")
    for c in candidates[:20]:
        debug(
            f"{c['match']} | {c['bet']} | odds={c['odds']} | edge={c['edge']} | "
            f"conf={c['confidence']} | q={c['quality_score']} | books={c['bookmakers_used']}"
        )

    final = []
    used_matches = set()
    counts = defaultdict(int)

    for c in candidates:
        if len(final) >= MAX_FINAL_PICKS:
            break

        if c["match_id"] in used_matches:
            continue

        bucket = c["bucket"]
        if counts[bucket] >= MARKET_LIMITS.get(bucket, 1):
            continue

        final.append(c)
        used_matches.add(c["match_id"])
        counts[bucket] += 1

    final.sort(key=lambda x: (x["date"], x["time"]))

    debug("\nFINAL PICKS:")
    for p in final:
        debug(
            f"{p['date']} {p['time']} | {p['match']} | {p['bet']} | "
            f"odds={p['odds']} | edge={p['edge']} | conf={p['confidence']} | q={p['quality_score']}"
        )

    return final


def main():
    predictions = build_predictions()

    save_json(PREDICTIONS_FILE, predictions)
    append_unique_history(predictions)

    print(f"Saved {len(predictions)} predictions to {PREDICTIONS_FILE}.")


if __name__ == "__main__":
    main()
