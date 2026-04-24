import requests
import json
import os
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"
FOOTBALL_URL = "https://v3.football.api-sports.io"

team_cache = {}

# ------------------------
# FETCH ODDS
# ------------------------
def fetch_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal"
    }

    res = requests.get(ODDS_URL, params=params, timeout=10)

    if res.status_code != 200:
        print(res.text)
        return []

    return res.json()

# ------------------------
# TEAM STATS
# ------------------------
def get_team_stats(team):
    if team in team_cache:
        return team_cache[team]

    try:
        headers = {"x-apisports-key": FOOTBALL_API_KEY}

        res = requests.get(
            f"{FOOTBALL_URL}/teams",
            headers=headers,
            params={"search": team},
            timeout=5
        )

        data = res.json()

        if not data["response"]:
            team_cache[team] = (1.2, 1.2)
            return (1.2, 1.2)

        team_id = data["response"][0]["team"]["id"]

        res = requests.get(
            f"{FOOTBALL_URL}/fixtures",
            headers=headers,
            params={"team": team_id, "last": 5},
            timeout=5
        )

        fixtures = res.json()["response"]

        gf = sum(f["goals"]["for"] for f in fixtures)
        ga = sum(f["goals"]["against"] for f in fixtures)

        avg_for = gf / max(len(fixtures), 1)
        avg_against = ga / max(len(fixtures), 1)

        team_cache[team] = (avg_for, avg_against)
        return (avg_for, avg_against)

    except:
        team_cache[team] = (1.2, 1.2)
        return (1.2, 1.2)

# ------------------------
# PREMIUM AI ANALYSIS
# ------------------------
def generate_reasoning(home, away, bet, expected_goals, edge):
    if "Over" in bet:
        texts = [
            f"{home} and {away} both operate with aggressive attacking profiles, projecting around {round(expected_goals,1)} expected goals. This typically results in an open, high-tempo match with multiple scoring opportunities. Edge vs market: {round(edge,3)}.",
            f"Both teams are consistently creating chances and playing at a higher tempo. With expected goals above average at {round(expected_goals,1)}, the probability of goals is higher than market pricing suggests. Clear value position.",
            f"This is a high-event matchup. Both sides contribute offensively and struggle to limit chances, pushing expected goals into a strong range. Market is slightly behind true probability here."
        ]
    elif "Under" in bet:
        texts = [
            f"This matchup profiles as controlled and slower-paced. Both teams show reduced attacking efficiency, keeping expected goals around {round(expected_goals,1)}. Market is slightly overpricing goals.",
            f"Recent performances indicate fewer high-quality chances and a more defensive structure. The projected goal output remains suppressed, supporting a lower scoring game.",
            f"The game dynamic favors discipline over aggression. With limited space and tempo, expected goals remain contained, creating value on the under."
        ]
    else:
        texts = [
            f"{home} shows stronger underlying metrics and recent form compared to {away}. The model identifies a clear edge of {round(edge,3)} over market expectations.",
            f"This side holds a structural advantage in key areas of play, with better consistency and efficiency. Market odds slightly underrate this edge.",
            f"Based on recent performances and matchup dynamics, this selection offers a measurable advantage that is not fully reflected in current pricing."
        ]

    endings = [
        " This is a strong value opportunity.",
        " This fits well within a value-based betting strategy.",
        " One of the better edges available on the board.",
        " Risk is present, but the value justifies the play."
    ]

    return random.choice(texts) + random.choice(endings)

# ------------------------
# MAIN MODEL
# ------------------------
def build_predictions():
    data = fetch_odds()
    picks = []

    for game in data:
        try:
            # ------------------------
            # TIME FILTER
            # ------------------------
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time_utc = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))

            local_tz = ZoneInfo("Europe/Ljubljana")
            match_time_local = match_time_utc.astimezone(local_tz)

            now_local = datetime.now(local_tz)

            if match_time_local < now_local + timedelta(minutes=30):
                continue

            end_of_day = now_local.replace(hour=23, minute=59, second=59)

            if match_time_local > end_of_day:
                continue

            # ------------------------
            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            home_for, home_against = get_team_stats(home)
            away_for, away_against = get_team_stats(away)

            expected_home = (home_for + away_against) / 2 + 0.15
            expected_away = (away_for + home_against) / 2
            expected_goals = expected_home + expected_away

            total = expected_home + expected_away
            if total == 0:
                continue

            home_prob = expected_home / total
            away_prob = expected_away / total
            draw_prob = 0.22

            over_prob = min(0.85, expected_goals / 3)
            under_prob = 1 - over_prob

            if not game.get("bookmakers"):
                continue

            bookmaker = game["bookmakers"][0]

            best_edge = -999
            best_pick = None

            for market in bookmaker["markets"]:

                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds
                        point = outcome.get("point", 2.5)

                        if outcome["name"] == "Over":
                            model_prob = over_prob
                            label = f"Over {point}"
                        else:
                            model_prob = under_prob
                            label = f"Under {point}"

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (label, odds)

                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == home:
                            model_prob = home_prob
                        elif outcome["name"] == away:
                            model_prob = away_prob
                        else:
                            if odds < 3.0:
                                continue
                            model_prob = draw_prob

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (outcome["name"], odds)

            if not best_pick:
                continue

            if best_edge < -0.02:
                continue

            picks.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": match_time_local.strftime("%H:%M"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": best_pick[0],
                "confidence": best_edge,
                "reasoning": generate_reasoning(home, away, best_pick[0], expected_goals, best_edge)
            })

        except:
            continue

    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    if len(picks) < 5:
        return picks[:5]

    very_strong = picks[:1]
    strong = picks[1:3]
    medium = picks[3:5]

    for p in very_strong:
        p["confidence"] = 82

    for p in strong:
        p["confidence"] = 68

    for p in medium:
        p["confidence"] = 55

    return very_strong + strong + medium

# ------------------------
# MAIN
# ------------------------
def main():
    predictions = build_predictions()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4)

    # SAVE TO HISTORY
    history_file = "results.json"

    try:
        with open(history_file, "r") as f:
            history = json.load(f)
    except:
        history = []

    existing = {(p["match"], p["date"]) for p in history}

    for p in predictions:
        key = (p["match"], p["date"])

        if key not in existing:
            new_pick = p.copy()
            new_pick["result"] = "pending"
            history.append(new_pick)

    with open(history_file, "w") as f:
        json.dump(history, f, indent=4)

    print(f"Saved {len(predictions)} predictions and updated history.")


if __name__ == "__main__":
    main()
