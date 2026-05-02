import requests
import json
import os
import hashlib
import statistics
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"
FOOTBALL_URL = "https://v3.football.api-sports.io"

TZ_NAME = "Europe/Ljubljana"

PREDICTIONS_FILE = "predictions.json"
RESULTS_FILE = "results.json"

DEBUG = True

MINUTES_BEFORE_MATCH = 45
TIME_WINDOW_HOURS = 24

MAX_FINAL_PICKS = 5
MAX_API_FOOTBALL_PREDICTION_CALLS = 12

MIN_BOOKMAKERS_GAME = 4
MIN_TOTAL_BOOKMAKERS = 4
MIN_H2H_BOOKMAKERS = 5

MIN_VALUE_EDGE = 0.035
DRAW_MIN_VALUE_EDGE = 0.065

ODDS_MIN = 1.55
ODDS_MAX = 3.20

DRAW_ODDS_MIN = 2.80
DRAW_ODDS_MAX = 4.20

API_FOOTBALL_SLEEP_SECONDS = 6.2

MARKET_LIMITS = {
    "home": 2,
    "away": 2,
    "draw": 1,
    "over": 2,
    "under": 2,
}

VALID_FOOTBALL_STATUSES = {"NS", "TBD", "PST"}

prediction_calls_used = 0
last_football_api_call = 0.0


def debug(msg):
    if DEBUG:
        print(msg)


def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def normalize(text):
    return " ".join(str(text or "").strip().lower().split())


def clean_team_name(name):
    text = normalize(name)

    replacements = {
        " fc": "",
        " cf": "",
        " afc": "",
        " sc": "",
        " fk": "",
        " sk": "",
        " ac": "",
        " cd": "",
        " ca": "",
        " de": "",
        " the ": " ",
        ".": "",
        "-": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def token_similarity(a, b):
    a_tokens = set(clean_team_name(a).split())
    b_tokens = set(clean_team_name(b).split())

    if not a_tokens or not b_tokens:
        return 0.0

    overlap = len(a_tokens & b_tokens)
    total = len(a_tokens | b_tokens)

    return overlap / total if total else 0.0


def median_or_none(values):
    cleaned = [safe_float(v) for v in values]
    cleaned = [v for v in cleaned if v is not None and v > 1]
    if not cleaned:
        return None
    return float(statistics.median(cleaned))


def clamp(value, low, high):
    return max(low, min(high, value))


def build_pick_id(match, bet, date, time_str, odds):
    raw = f"{match}|{bet}|{date}|{time_str}|{odds}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def load_json(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


def football_headers():
    return {"x-apisports-key": FOOTBALL_API_KEY}


def throttle_football_api():
    global last_football_api_call

    now = time.time()
    elapsed = now - last_football_api_call

    if elapsed < API_FOOTBALL_SLEEP_SECONDS:
        time.sleep(API_FOOTBALL_SLEEP_SECONDS - elapsed)

    last_football_api_call = time.time()


def football_api_get(endpoint, params):
    if not FOOTBALL_API_KEY:
        return {"response": []}

    throttle_football_api()

    url = f"{FOOTBALL_URL}/{endpoint}"
    res = requests.get(url, headers=football_headers(), params=params, timeout=20)

    if res.status_code != 200:
        debug(f"API-FOOTBALL ERROR {endpoint}: {res.status_code} {res.text[:300]}")
        return {"response": []}

    data = res.json()

    errors = data.get("errors") or {}
    if errors:
        debug(f"API-FOOTBALL WARN {endpoint} {params}: {errors}")

    return data


def fetch_odds():
    if not ODDS_API_KEY:
        raise RuntimeError("Missing ODDS_API_KEY_V2 environment variable.")

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
    }

    debug("FETCHING THE ODDS API...")
    res = requests.get(ODDS_URL, params=params, timeout=20)

    debug(f"ODDS API STATUS: {res.status_code}")

    remaining = res.headers.get("x-requests-remaining")
    used = res.headers.get("x-requests-used")

    if remaining is not None:
        debug(f"ODDS API REQUESTS REMAINING: {remaining}")
    if used is not None:
        debug(f"ODDS API REQUESTS USED: {used}")

    if res.status_code != 200:
        print("ODDS API ERROR:", res.status_code, res.text[:500])
        return []

    data = res.json()

    if not isinstance(data, list):
        return []

    debug(f"ODDS API GAMES LOADED: {len(data)}")
    return data


def fetch_api_football_fixtures(start_time, end_time):
    fixtures = []
    current_date = start_time.date()
    end_date = end_time.date()

    while current_date <= end_date:
        try:
            data = football_api_get(
                "fixtures",
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "timezone": TZ_NAME,
                },
            )

            daily = data.get("response", [])
            debug(f"API-FOOTBALL FIXTURES {current_date}: {len(daily)}")
            fixtures.extend(daily)

        except Exception as e:
            debug(f"API-FOOTBALL FIXTURES ERROR {current_date}: {e}")

        current_date += timedelta(days=1)

    return fixtures


def parse_fixture_time(fixture):
    raw = fixture.get("fixture", {}).get("date")
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw).astimezone(ZoneInfo(TZ_NAME))
    except Exception:
        return None


def match_api_football_fixture(odds_game, fixtures):
    odds_home = odds_game.get("home_team")
    odds_away = odds_game.get("away_team")
    commence_time = odds_game.get("commence_time")

    if not odds_home or not odds_away or not commence_time:
        return None, 0.0

    try:
        odds_time = datetime.fromisoformat(
            commence_time.replace("Z", "+00:00")
        ).astimezone(ZoneInfo(TZ_NAME))
    except Exception:
        return None, 0.0

    best_fixture = None
    best_score = 0.0

    for fixture in fixtures:
        fixture_time = parse_fixture_time(fixture)
        if not fixture_time:
            continue

        time_diff_min = abs((fixture_time - odds_time).total_seconds()) / 60

        if time_diff_min > 150:
            continue

        api_home = fixture.get("teams", {}).get("home", {}).get("name", "")
        api_away = fixture.get("teams", {}).get("away", {}).get("name", "")

        home_score = token_similarity(odds_home, api_home)
        away_score = token_similarity(odds_away, api_away)

        score = (home_score * 0.45) + (away_score * 0.45)

        if time_diff_min <= 30:
            score += 0.10
        elif time_diff_min <= 90:
            score += 0.05

        if score > best_score:
            best_score = score
            best_fixture = fixture

    if best_score >= 0.45:
        return best_fixture, best_score

    return None, best_score


def get_api_football_prediction(fixture_id):
    global prediction_calls_used

    if not fixture_id:
        return None

    if prediction_calls_used >= MAX_API_FOOTBALL_PREDICTION_CALLS:
        return None

    prediction_calls_used += 1

    try:
        data = football_api_get("predictions", {"fixture": fixture_id})
        response = data.get("response", [])

        if not response:
            return None

        pred = response[0].get("predictions", {})

        percent = pred.get("percent", {})
        goals = pred.get("goals", {})

        result = {
            "percent_home": safe_float(str(percent.get("home", "")).replace("%", "")),
            "percent_draw": safe_float(str(percent.get("draw", "")).replace("%", "")),
            "percent_away": safe_float(str(percent.get("away", "")).replace("%", "")),
            "goals_home": safe_float(goals.get("home")),
            "goals_away": safe_float(goals.get("away")),
            "advice": pred.get("advice", ""),
        }

        return result

    except Exception as e:
        debug(f"PREDICTION ERROR fixture={fixture_id}: {e}")
        return None


def get_market(bookmaker, key):
    for market in bookmaker.get("markets", []):
        if market.get("key") == key:
            return market
    return None


def collect_h2h_prices(game):
    home = game.get("home_team")
    away = game.get("away_team")

    prices = {
        "home": [],
        "away": [],
        "draw": [],
    }

    for bookmaker in game.get("bookmakers", []):
        market = get_market(bookmaker, "h2h")
        if not market:
            continue

        bookmaker_name = bookmaker.get("title", "Bookmaker")

        for outcome in market.get("outcomes", []):
            name = outcome.get("name")
            odds = safe_float(outcome.get("price"))

            if odds is None or odds <= 1:
                continue

            if name == home:
                prices["home"].append({"bookmaker": bookmaker_name, "odds": odds})
            elif name == away:
                prices["away"].append({"bookmaker": bookmaker_name, "odds": odds})
            elif normalize(name) == "draw":
                prices["draw"].append({"bookmaker": bookmaker_name, "odds": odds})

    return prices


def collect_total_prices(game):
    totals = {}

    for bookmaker in game.get("bookmakers", []):
        market = get_market(bookmaker, "totals")
        if not market:
            continue

        bookmaker_name = bookmaker.get("title", "Bookmaker")

        for outcome in market.get("outcomes", []):
            side = normalize(outcome.get("name"))
            point = safe_float(outcome.get("point"))
            odds = safe_float(outcome.get("price"))

            if point is None or odds is None or odds <= 1:
                continue

            if side not in {"over", "under"}:
                continue

            if point not in totals:
                totals[point] = {"over": [], "under": []}

            totals[point][side].append({
                "bookmaker": bookmaker_name,
                "odds": odds,
            })

    return totals


def best_price(price_rows):
    if not price_rows:
        return None
    return max(price_rows, key=lambda x: x["odds"])


def devig_two_way(over_prices, under_prices):
    over_median = median_or_none([x["odds"] for x in over_prices])
    under_median = median_or_none([x["odds"] for x in under_prices])

    if not over_median or not under_median:
        return None

    over_raw = 1 / over_median
    under_raw = 1 / under_median
    total = over_raw + under_raw

    if total <= 0:
        return None

    return {
        "over_prob": over_raw / total,
        "under_prob": under_raw / total,
        "over_median": over_median,
        "under_median": under_median,
    }


def devig_three_way(home_prices, draw_prices, away_prices):
    home_median = median_or_none([x["odds"] for x in home_prices])
    draw_median = median_or_none([x["odds"] for x in draw_prices])
    away_median = median_or_none([x["odds"] for x in away_prices])

    if not home_median or not draw_median or not away_median:
        return None

    home_raw = 1 / home_median
    draw_raw = 1 / draw_median
    away_raw = 1 / away_median
    total = home_raw + draw_raw + away_raw

    if total <= 0:
        return None

    return {
        "home_prob": home_raw / total,
        "draw_prob": draw_raw / total,
        "away_prob": away_raw / total,
        "home_median": home_median,
        "draw_median": draw_median,
        "away_median": away_median,
    }


def api_football_support_score(pick_type, line, prediction):
    if not prediction:
        return 0, "no_api_football_prediction"

    support = 0
    reason = []

    ph = prediction.get("percent_home")
    pd = prediction.get("percent_draw")
    pa = prediction.get("percent_away")

    gh = prediction.get("goals_home")
    ga = prediction.get("goals_away")

    expected_total = None
    if gh is not None and ga is not None:
        expected_total = gh + ga

    if pick_type == "home" and ph is not None:
        if ph >= 45:
            support += 10
            reason.append("api_home_support")
        elif ph <= 30:
            support -= 10
            reason.append("api_home_conflict")

    if pick_type == "away" and pa is not None:
        if pa >= 42:
            support += 10
            reason.append("api_away_support")
        elif pa <= 28:
            support -= 10
            reason.append("api_away_conflict")

    if pick_type == "draw" and pd is not None:
        if pd >= 28:
            support += 8
            reason.append("api_draw_support")
        elif pd <= 20:
            support -= 8
            reason.append("api_draw_conflict")

    if pick_type == "over" and expected_total is not None and line is not None:
        if expected_total >= line + 0.25:
            support += 10
            reason.append("api_goals_over_support")
        elif expected_total <= line - 0.25:
            support -= 10
            reason.append("api_goals_over_conflict")

    if pick_type == "under" and expected_total is not None and line is not None:
        if expected_total <= line - 0.25:
            support += 10
            reason.append("api_goals_under_support")
        elif expected_total >= line + 0.25:
            support -= 10
            reason.append("api_goals_under_conflict")

    return support, ",".join(reason) if reason else "api_neutral"


def confidence_from_edge(edge, bookmakers_used, odds, market_type, api_support):
    edge_score = clamp(edge / 0.12, 0, 1) * 42
    bookmaker_score = clamp(bookmakers_used / 10, 0, 1) * 22

    if 1.70 <= odds <= 2.20:
        odds_score = 18
    elif 1.55 <= odds <= 2.60:
        odds_score = 12
    else:
        odds_score = 7

    market_score = 8
    if market_type == "draw":
        market_score = 3

    score = edge_score + bookmaker_score + odds_score + market_score + api_support

    return round(clamp(score, 40, 88), 1)


def generate_reasoning(match, bet, odds, median_odds, edge, bookmakers_used, market_type, api_note, fixture_matched):
    edge_pct = round(edge * 100, 1)

    base = (
        f"{bet} is selected as a combined market-value pick. The best available price is {odds:.2f}, "
        f"while the market median is around {median_odds:.2f}. Across {bookmakers_used} bookmakers, "
        f"the estimated value gap is +{edge_pct}%."
    )

    if fixture_matched:
        base += " API-Football validation was matched for this fixture."
    else:
        base += " API-Football validation was not matched, so this remains a market-only signal."

    if api_note and api_note != "no_api_football_prediction":
        base += f" Validation note: {api_note.replace('_', ' ')}."

    if market_type == "draw":
        base += " Draw picks remain high variance and should be treated with lower exposure."

    return base


def make_pick(
    game,
    match_time,
    bet,
    pick_type,
    odds,
    median_odds,
    fair_prob,
    edge,
    bookmakers_used,
    bookmaker_name,
    line=None,
    fixture=None,
    fixture_match_score=0.0,
    prediction=None,
):
    home = game.get("home_team")
    away = game.get("away_team")
    league = game.get("sport_title", "Football")

    match = f"{home} - {away}"
    date_str = match_time.strftime("%Y-%m-%d")
    time_str = match_time.strftime("%H:%M")

    fixture_id = None
    api_note = "no_api_football_match"
    api_support = 0

    if fixture:
        fixture_id = fixture.get("fixture", {}).get("id")
        api_support, api_note = api_football_support_score(
            pick_type=pick_type,
            line=line,
            prediction=prediction,
        )

    confidence = confidence_from_edge(
        edge=edge,
        bookmakers_used=bookmakers_used,
        odds=odds,
        market_type=pick_type,
        api_support=api_support,
    )

    return {
        "pick_id": build_pick_id(match, bet, date_str, time_str, odds),
        "date": date_str,
        "time": time_str,
        "sport": "football",
        "league": league,
        "match": match,
        "bet": bet,
        "line": line,
        "odds": round(odds, 2),
        "market_median_odds": round(median_odds, 2),
        "model_prob": round(fair_prob, 4),
        "implied_prob": round(1 / odds, 4),
        "edge": round(edge, 4),
        "confidence": confidence,
        "bookmakers_used": bookmakers_used,
        "best_bookmaker": bookmaker_name,
        "api_football_fixture_id": fixture_id,
        "api_football_match_score": round(fixture_match_score, 3),
        "api_football_note": api_note,
        "reasoning": generate_reasoning(
            match=match,
            bet=bet,
            odds=odds,
            median_odds=median_odds,
            edge=edge,
            bookmakers_used=bookmakers_used,
            market_type=pick_type,
            api_note=api_note,
            fixture_matched=bool(fixture),
        ),
        "_pick_type": pick_type,
        "_sort_time": match_time.timestamp(),
    }


def build_predictions():
    odds_data = fetch_odds()

    tz = ZoneInfo(TZ_NAME)
    now = datetime.now(tz)

    start_time = now + timedelta(minutes=MINUTES_BEFORE_MATCH)
    end_time = now + timedelta(hours=TIME_WINDOW_HOURS)

    debug(f"NOW: {now}")
    debug(f"WINDOW START: {start_time}")
    debug(f"WINDOW END: {end_time}")

    football_fixtures = fetch_api_football_fixtures(start_time, end_time)

    candidates = []

    stats = {
        "odds_games_total": 0,
        "rejected_time_window": 0,
        "rejected_low_bookmakers": 0,
        "games_checked": 0,
        "api_football_matched": 0,
        "api_football_not_matched": 0,
        "candidates_total": 0,
        "rejected_edge": 0,
        "rejected_odds": 0,
        "rejected_api_conflict": 0,
    }

    prediction_cache = {}

    for game in odds_data:
        stats["odds_games_total"] += 1

        try:
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time = datetime.fromisoformat(
                commence_time.replace("Z", "+00:00")
            ).astimezone(tz)

            if match_time < start_time or match_time > end_time:
                stats["rejected_time_window"] += 1
                continue

            home = game.get("home_team")
            away = game.get("away_team")

            if not home or not away:
                continue

            bookmakers = game.get("bookmakers") or []

            if len(bookmakers) < MIN_BOOKMAKERS_GAME:
                stats["rejected_low_bookmakers"] += 1
                continue

            stats["games_checked"] += 1

            fixture, fixture_score = match_api_football_fixture(game, football_fixtures)

            if fixture:
                status = fixture.get("fixture", {}).get("status", {}).get("short")
                if status and status not in VALID_FOOTBALL_STATUSES:
                    debug(f"SKIP STATUS NOT VALID: {home} - {away} | status={status}")
                    continue

                stats["api_football_matched"] += 1
                fixture_id = fixture.get("fixture", {}).get("id")

                prediction = None
                if fixture_id:
                    if fixture_id not in prediction_cache:
                        prediction_cache[fixture_id] = get_api_football_prediction(fixture_id)
                    prediction = prediction_cache[fixture_id]
            else:
                prediction = None
                stats["api_football_not_matched"] += 1

            debug(f"\nCHECK GAME: {home} - {away} | bookmakers={len(bookmakers)} | api_match={bool(fixture)} score={fixture_score:.2f}")

            # H2H
            h2h = collect_h2h_prices(game)
            h2h_devig = devig_three_way(h2h["home"], h2h["draw"], h2h["away"])

            if h2h_devig:
                h2h_map = [
                    ("home", home, h2h["home"], h2h_devig["home_prob"], h2h_devig["home_median"]),
                    ("draw", "Draw", h2h["draw"], h2h_devig["draw_prob"], h2h_devig["draw_median"]),
                    ("away", away, h2h["away"], h2h_devig["away_prob"], h2h_devig["away_median"]),
                ]

                for pick_type, bet, rows, fair_prob, median_odds in h2h_map:
                    if len(rows) < MIN_H2H_BOOKMAKERS:
                        continue

                    best = best_price(rows)
                    if not best:
                        continue

                    odds = best["odds"]
                    implied = 1 / odds
                    edge = fair_prob - implied

                    if pick_type == "draw":
                        if edge < DRAW_MIN_VALUE_EDGE:
                            stats["rejected_edge"] += 1
                            continue
                        if odds < DRAW_ODDS_MIN or odds > DRAW_ODDS_MAX:
                            stats["rejected_odds"] += 1
                            continue
                    else:
                        if edge < MIN_VALUE_EDGE:
                            stats["rejected_edge"] += 1
                            continue
                        if odds < ODDS_MIN or odds > ODDS_MAX:
                            stats["rejected_odds"] += 1
                            continue

                    api_support, api_note = api_football_support_score(pick_type, None, prediction)
                    if api_support <= -10:
                        stats["rejected_api_conflict"] += 1
                        debug(f"REJECT API CONFLICT: {home} - {away} | {bet} | {api_note}")
                        continue

                    pick = make_pick(
                        game=game,
                        match_time=match_time,
                        bet=bet,
                        pick_type=pick_type,
                        odds=odds,
                        median_odds=median_odds,
                        fair_prob=fair_prob,
                        edge=edge,
                        bookmakers_used=len(rows),
                        bookmaker_name=best["bookmaker"],
                        line=None,
                        fixture=fixture,
                        fixture_match_score=fixture_score,
                        prediction=prediction,
                    )

                    candidates.append(pick)
                    stats["candidates_total"] += 1
                    debug(f"ADD H2H: {pick['match']} | {pick['bet']} | edge={pick['edge']} | conf={pick['confidence']}")

            # Totals
            totals = collect_total_prices(game)

            for point, sides in totals.items():
                if point not in {2.5, 3.5}:
                    continue

                over_rows = sides.get("over", [])
                under_rows = sides.get("under", [])

                if len(over_rows) < MIN_TOTAL_BOOKMAKERS or len(under_rows) < MIN_TOTAL_BOOKMAKERS:
                    continue

                total_devig = devig_two_way(over_rows, under_rows)
                if not total_devig:
                    continue

                totals_map = [
                    ("over", f"Over {point}", over_rows, total_devig["over_prob"], total_devig["over_median"]),
                    ("under", f"Under {point}", under_rows, total_devig["under_prob"], total_devig["under_median"]),
                ]

                for pick_type, bet, rows, fair_prob, median_odds in totals_map:
                    best = best_price(rows)
                    if not best:
                        continue

                    odds = best["odds"]
                    implied = 1 / odds
                    edge = fair_prob - implied

                    if edge < MIN_VALUE_EDGE:
                        stats["rejected_edge"] += 1
                        continue

                    if odds < ODDS_MIN or odds > ODDS_MAX:
                        stats["rejected_odds"] += 1
                        continue

                    api_support, api_note = api_football_support_score(pick_type, point, prediction)
                    if api_support <= -10:
                        stats["rejected_api_conflict"] += 1
                        debug(f"REJECT API CONFLICT: {home} - {away} | {bet} | {api_note}")
                        continue

                    pick = make_pick(
                        game=game,
                        match_time=match_time,
                        bet=bet,
                        pick_type=pick_type,
                        odds=odds,
                        median_odds=median_odds,
                        fair_prob=fair_prob,
                        edge=edge,
                        bookmakers_used=len(rows),
                        bookmaker_name=best["bookmaker"],
                        line=point,
                        fixture=fixture,
                        fixture_match_score=fixture_score,
                        prediction=prediction,
                    )

                    candidates.append(pick)
                    stats["candidates_total"] += 1
                    debug(f"ADD TOTAL: {pick['match']} | {pick['bet']} | edge={pick['edge']} | conf={pick['confidence']}")

        except Exception as e:
            print("GAME ERROR:", e)
            continue

    debug("\n========== BUILD STATS ==========")
    for key, value in stats.items():
        debug(f"{key}: {value}")

    candidates = sorted(
        candidates,
        key=lambda x: (
            x["confidence"],
            x["edge"],
            x["bookmakers_used"],
            x["odds"],
        ),
        reverse=True,
    )

    debug("\n========== TOP CANDIDATES ==========")
    for c in candidates[:15]:
        debug(
            f"{c['match']} | {c['bet']} | odds={c['odds']} | edge={c['edge']} | "
            f"conf={c['confidence']} | books={c['bookmakers_used']} | api={c['api_football_note']}"
        )

    final = []
    used_matches = set()
    counts = {k: 0 for k in MARKET_LIMITS}

    for pick in candidates:
        if len(final) >= MAX_FINAL_PICKS:
            break

        match = pick["match"]
        pick_type = pick["_pick_type"]

        if match in used_matches:
            continue

        if counts.get(pick_type, 0) >= MARKET_LIMITS.get(pick_type, 1):
            continue

        final.append(pick)
        used_matches.add(match)
        counts[pick_type] = counts.get(pick_type, 0) + 1

    final = sorted(final, key=lambda x: x["_sort_time"])

    cleaned = []
    for pick in final:
        item = pick.copy()
        del item["_sort_time"]
        del item["_pick_type"]
        cleaned.append(item)

    debug("\n========== FINAL PICKS ==========")
    for p in cleaned:
        debug(f"{p['date']} {p['time']} | {p['match']} | {p['bet']} | odds={p['odds']} | conf={p['confidence']} | api={p['api_football_note']}")

    return cleaned


def update_history(predictions):
    history = load_json(RESULTS_FILE, [])
    if not isinstance(history, list):
        history = []

    existing_ids = {
        item.get("pick_id")
        for item in history
        if isinstance(item, dict)
    }

    added = 0

    for pick in predictions:
        if pick["pick_id"] in existing_ids:
            debug(f"SKIP HISTORY DUPLICATE: {pick['match']} | {pick['bet']}")
            continue

        new_pick = pick.copy()
        new_pick["result"] = "pending"

        history.append(new_pick)
        existing_ids.add(pick["pick_id"])
        added += 1

    save_json(RESULTS_FILE, history)

    debug(f"HISTORY ADDED: {added}")
    debug(f"HISTORY TOTAL: {len(history)}")

    return added, len(history)


def main():
    predictions = build_predictions()
    save_json(PREDICTIONS_FILE, predictions)

    added, history_total = update_history(predictions)

    print(f"Saved {len(predictions)} predictions.")
    print(f"Added {added} new picks to results.json.")
    print(f"History total: {history_total}")


if __name__ == "__main__":
    main()
