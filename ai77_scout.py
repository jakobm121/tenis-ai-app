import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")
ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"

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
        print("API ERROR:", res.text)
        return []

    return res.json()

# ------------------------
# AI ANALYSIS
# ------------------------
def generate_reasoning(home, away, bet, expected_goals):
    if "Over" in bet:
        return f"{home} and {away} project an open game with strong attacking output. Expected goals suggest above-average scoring."

    elif "Under" in bet:
        return f"This game trends toward control and structure. Limited chances point to a lower scoring outcome."

    elif "Draw" in bet:
        return f"Balanced matchup with similar team strength. Game dynamics suggest a tight contest with potential stalemate."

    else:
        return f"{home} shows stronger consistency and structure compared to {away}, giving them a slight edge."

# ------------------------
# MAIN MODEL
# ------------------------
def build_predictions():
    data = fetch_odds()
    picks = []

    tz = ZoneInfo("Europe/Ljubljana")
    now = datetime.now(tz)

    start_time = now + timedelta(minutes=30)
    end_time = now + timedelta(hours=24)

    # BALANCE
    over_count = 0
    under_count = 0
    home_count = 0
    away_count = 0
    draw_count = 0

    for game in data:
        try:
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00")).astimezone(tz)

            if match_time < start_time or match_time > end_time:
                continue

            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            # ------------------------
            # MODEL (bolj realen)
            # ------------------------
            expected_home = 1.25
            expected_away = 1.15
            expected_goals = expected_home + expected_away

            total = expected_goals
            home_prob = expected_home / total
            away_prob = expected_away / total

            # ------------------------
            # SMART TOTALS
            # ------------------------
            if expected_goals > 2.8:
                over_prob = 0.62
            elif expected_goals > 2.4:
                over_prob = 0.57
            else:
                over_prob = 0.50

            under_prob = 1 - over_prob

            if not game.get("bookmakers"):
                continue

            bookmaker = game["bookmakers"][0]

            best_edge = -999
            best_pick = None
            best_type = None

            for market in bookmaker["markets"]:

                # ------------------------
                # TOTALS
                # ------------------------
                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds
                        point = outcome.get("point", 2.5)

                        if outcome["name"] == "Over":
                            model_prob = over_prob
                            label = f"Over {point}"
                            pick_type = "over"
                        else:
                            model_prob = under_prob
                            label = f"Under {point}"
                            pick_type = "under"

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (label, odds)
                            best_type = pick_type

                # ------------------------
                # H2H + SMART DRAW
                # ------------------------
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:

                        odds = outcome["price"]
                        implied = 1 / odds

                        # HOME
                        if outcome["name"] == home:
                            model_prob = home_prob
                            edge = model_prob - implied
                            edge *= 0.95  # manj home bias

                            if edge > best_edge:
                                best_edge = edge
                                best_pick = (home, odds)
                                best_type = "home"

                        # AWAY
                        elif outcome["name"] == away:
                            model_prob = away_prob
                            edge = model_prob - implied

                            if edge > best_edge:
                                best_edge = edge
                                best_pick = (away, odds)
                                best_type = "away"

                        # DRAW (SMART)
                        else:
                            # expected goals logic
                            if expected_goals < 2.2:
                                model_prob = 0.28
                            elif expected_goals < 2.6:
                                model_prob = 0.25
                            else:
                                model_prob = 0.20

                            # samo izenačene tekme
                            if abs(home_prob - away_prob) > 0.15:
                                continue

                            edge = model_prob - implied
                            edge *= 0.9

                            if edge > 0.06 and draw_count == 0:
                                if edge > best_edge:
                                    best_edge = edge
                                    best_pick = ("Draw", odds)
                                    best_type = "draw"

            if not best_pick:
                continue

            odds = best_pick[1]

            # FILTER
            if best_edge < -0.04:
                continue

            if odds < 1.4 or odds > 3.2:
                continue

            # ------------------------
            # BALANCE PICKS
            # ------------------------
            if best_type == "over" and over_count >= 2:
                continue
            if best_type == "under" and under_count >= 2:
                continue
            if best_type == "home" and home_count >= 2:
                continue
            if best_type == "away" and away_count >= 2:
                continue
            if best_type == "draw" and draw_count >= 1:
                continue

            # increment
            if best_type == "over":
                over_count += 1
            elif best_type == "under":
                under_count += 1
            elif best_type == "home":
                home_count += 1
            elif best_type == "away":
                away_count += 1
            elif best_type == "draw":
                draw_count += 1

            picks.append({
                "date": now.strftime("%Y-%m-%d"),
                "time": match_time.strftime("%H:%M"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": best_pick[0],
                "confidence": best_edge,
                "reasoning": generate_reasoning(home, away, best_pick[0], expected_goals),
                "sort_time": match_time.timestamp()
            })

        except:
            continue

    # SORT
    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)
    picks = picks[:5]

    # ------------------------
    # UNIT SYSTEM (TVOJ)
    # ------------------------
    for i, p in enumerate(picks):

        if p["bet"] == "Draw":
            p["confidence"] = 55
            continue

        if i == 0:
            p["confidence"] = 78
        elif i < 3:
            p["confidence"] = 66
        else:
            p["confidence"] = 55

    picks = sorted(picks, key=lambda x: x["sort_time"])

    for p in picks:
        del p["sort_time"]

    return picks

# ------------------------
# MAIN
# ------------------------
def main():
    predictions = build_predictions()

    with open("predictions.json", "w") as f:
        json.dump(predictions, f, indent=4)

    try:
        with open("results.json", "r") as f:
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

    with open("results.json", "w") as f:
        json.dump(history, f, indent=4)

    print(f"Saved {len(predictions)} predictions.")

if __name__ == "__main__":
    main()
