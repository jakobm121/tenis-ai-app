import os
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

ISPORTS_API_KEY = os.getenv("ISPORTS_API_KEY")

BASE_URL = "http://api.isportsapi.com"
TZ_NAME = "Europe/Ljubljana"

RESULTS_FILE = "results.json"
REQUEST_TIMEOUT = 30

# iSports football:
# -1 = finished
# -10 / -11 / -14 = cancelled / interrupted / void-like statuses
FINISHED_STATUSES = {-1}
STORNO_STATUSES = {-10, -11, -14}

DEBUG = True


def debug(msg):
    if DEBUG:
        print(msg)


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


def api_get(path, params=None):
    if not ISPORTS_API_KEY:
        raise RuntimeError("Missing ISPORTS_API_KEY environment variable.")

    params = params.copy() if params else {}
    params["api_key"] = ISPORTS_API_KEY

    res = requests.get(
        BASE_URL + path,
        params=params,
        timeout=REQUEST_TIMEOUT
    )

    if res.status_code != 200:
        raise RuntimeError(f"HTTP {res.status_code}: {res.text[:300]}")

    data = res.json()

    if data.get("code") != 0:
        raise RuntimeError(f"API code={data.get('code')}: {data.get('message')}")

    return data.get("data", [])


def fetch_schedule_by_date(date_str):
    debug(f"FETCH schedule date={date_str}")
    return api_get("/sport/football/schedule", {"date": date_str})


def settle_h2h(pick, match):
    home_score = safe_int(match.get("homeScore"))
    away_score = safe_int(match.get("awayScore"))

    if home_score is None or away_score is None:
        return "pending"

    home = str(match.get("homeName", "")).strip()
    away = str(match.get("awayName", "")).strip()
    bet = str(pick.get("bet", "")).strip()

    if home_score > away_score:
        winner = home
    elif away_score > home_score:
        winner = away
    else:
        winner = "Draw"

    return "win" if bet == winner else "loss"


def settle_total(pick, match):
    home_score = safe_int(match.get("homeScore"))
    away_score = safe_int(match.get("awayScore"))

    if home_score is None or away_score is None:
        return "pending"

    total = home_score + away_score

    line = safe_float(pick.get("line"))

    if line is None:
        parts = str(pick.get("bet", "")).split()
        if len(parts) >= 2:
            line = safe_float(parts[-1])

    if line is None:
        return "pending"

    bet = str(pick.get("bet", "")).lower()

    if "over" in bet:
        if total > line:
            return "win"
        if total == line:
            return "storno"
        return "loss"

    if "under" in bet:
        if total < line:
            return "win"
        if total == line:
            return "storno"
        return "loss"

    return "pending"


def settle_pick(pick, match):
    status = safe_int(match.get("status"))
    home_score = safe_int(match.get("homeScore"))
    away_score = safe_int(match.get("awayScore"))

    debug(
        f"CHECK {pick.get('match')} | {pick.get('bet')} | "
        f"status={status} | score={home_score}:{away_score}"
    )

    # Cancelled / abandoned / void-like statuses.
    # iSports can still show 0:0 on these, so trust the status.
    if status in STORNO_STATUSES:
        return "storno"

    # IMPORTANT:
    # Do not settle football on live statuses like 1, 2, 3.
    # Only status -1 is safe to settle by score.
    if status not in FINISHED_STATUSES:
        return "pending"

    bucket = str(pick.get("bucket", "")).lower()
    bet = str(pick.get("bet", "")).lower()

    if bucket in {"home", "away", "draw"}:
        return settle_h2h(pick, match)

    if "over" in bucket or "under" in bucket or "over" in bet or "under" in bet:
        return settle_total(pick, match)

    return "pending"


def unique_dates_for_pending(history):
    return sorted({
        item.get("date")
        for item in history
        if isinstance(item, dict)
        and str(item.get("result", "")).lower() == "pending"
        and item.get("date")
    })


def build_match_map_for_dates(dates):
    match_map = {}

    for date in dates:
        try:
            schedule = fetch_schedule_by_date(date)
            debug(f"DATE {date}: {len(schedule)} matches")

            for match in schedule:
                match_id = str(match.get("matchId") or "")
                if match_id:
                    match_map[match_id] = match

            time.sleep(1)

        except Exception as e:
            debug(f"ERROR date={date}: {e}")

    return match_map


def reset_bad_early_settles(history):
    """
    Safety repair:
    If a previous version settled a pick while the API status was live/non-final,
    this can restore it to pending when settled_status is not final/storno.

    It does NOT touch properly finished (-1) or storno statuses.
    """
    repaired = 0

    for item in history:
        if not isinstance(item, dict):
            continue

        result = str(item.get("result", "")).lower()
        settled_status = safe_int(item.get("settled_status"))

        if result not in {"win", "loss"}:
            continue

        if settled_status is None:
            continue

        if settled_status in FINISHED_STATUSES or settled_status in STORNO_STATUSES:
            continue

        item["result"] = "pending"
        item.pop("settled_at", None)
        item.pop("settled_status", None)
        item.pop("final_score", None)

        repaired += 1

    return repaired


def main():
    history = load_json(RESULTS_FILE, [])

    if not isinstance(history, list):
        history = []

    repaired = reset_bad_early_settles(history)
    if repaired:
        debug(f"REPAIRED EARLY SETTLES: {repaired}")

    pending = [
        item for item in history
        if isinstance(item, dict)
        and str(item.get("result", "")).lower() == "pending"
    ]

    debug(f"PENDING PICKS: {len(pending)}")

    if not pending:
        save_json(RESULTS_FILE, history)
        print("SETTLE DONE: no pending picks.")
        return

    dates = unique_dates_for_pending(history)
    debug(f"PENDING DATES: {dates}")

    match_map = build_match_map_for_dates(dates)

    updated = 0
    still_pending = 0
    not_found = 0

    for item in history:
        if not isinstance(item, dict):
            continue

        if str(item.get("result", "")).lower() != "pending":
            continue

        match_id = str(item.get("match_id") or item.get("fixture_id") or "")

        if not match_id:
            not_found += 1
            continue

        match = match_map.get(match_id)

        if not match:
            not_found += 1
            debug(f"NO MATCH FOUND: {item.get('match')} | match_id={match_id}")
            continue

        new_result = settle_pick(item, match)

        if new_result != "pending":
            status = safe_int(match.get("status"))
            home_score = safe_int(match.get("homeScore"))
            away_score = safe_int(match.get("awayScore"))

            item["result"] = new_result
            item["settled_at"] = datetime.now(ZoneInfo(TZ_NAME)).isoformat()
            item["settled_status"] = status

            if status in FINISHED_STATUSES:
                item["final_score"] = f"{home_score}:{away_score}"
            else:
                item["final_score"] = ""

            updated += 1

            debug(
                f"SETTLED {item.get('match')} | {item.get('bet')} | "
                f"status={status} | score={home_score}:{away_score} -> {new_result}"
            )
        else:
            still_pending += 1

    save_json(RESULTS_FILE, history)

    print(
        f"SETTLE DONE: updated={updated} "
        f"still_pending={still_pending} not_found={not_found}"
    )


if __name__ == "__main__":
    main()
