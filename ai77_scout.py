import requests
import json
import os
import random
from datetime import datetime

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
# TEAM STATS (GOALS FOR / AGAINST)
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

        gf = 0
        ga = 0

        for f in fixtures:
            gf += f["goals"]["for"]
            ga += f["goals"]["against"]

        avg_for = gf / max(len(fixtures), 1)
        avg_against = ga / max(len(fixtures), 1)

        team_cache[team] = (avg_for, avg_against)
        return (avg_for, avg_against)

    except:
        team_cache[team] = (1.2, 1.2)
        return (1.2, 1.2)

# ------------------------
# AI REASONING
# ------------------------
def generate_reasoning(home, away, bet, expected_goals):
    if "Over" in bet:
        texts = [
            f"{home} and {away} both show attacking potential. Expect goals here.",
            f"The match projects as open with around {round(expected_goals,1)} expected goals.",
            f"Offensive numbers suggest a high-scoring game."
        ]
    elif "Under" in bet:
        texts = [
            f"A tighter game is expected between {home} and {away}.",
            f"Defensive trends suggest fewer chances in this matchup.",
            f"Lower goal output is likely based on recent data."
        ]
    else:
        texts = [
            f"{bet} shows stronger underlying performance in this matchup.",
            f"Model slightly favors {bet} based on recent form.",
            f"{bet} appears to have the edge in this fixture."
        ]

    return random.choice(texts)

# ------------------------
# MODEL
# ------------------------
def build_predictions():
    data = fetch_odds()
    picks = []

    for game in data:
        try:
            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            home_for, home_against = get_team_stats(home)
            away_for, away_against = get_team_stats(away)

            # expected goals model
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

                # OVER / UNDER
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

                # MATCH WINNER (z draw filtrom)
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == home:
                            model_prob = home_prob
                        elif outcome["name"] == away:
                            model_prob = away_prob
                        else:
                            # draw filter
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

            odds = best_pick[1]

            # confidence
            confidence = int(50 + best_edge * 400)

            if odds < 2.0:
                confidence += 5
            if odds > 3.5:
                confidence -= 7
            if "Draw" in best_pick[0]:
                confidence -= 8

            confidence = max(55, min(confidence, 92))

            reasoning = generate_reasoning(
                home, away, best_pick[0], expected_goals
            )

            picks.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": best_pick[0],
                "confidence": confidence,
                "reasoning": reasoning
            })

        except Exception as e:
            continue

    picks = sorted(picks, key=lambda x: x["confidence"], reverse=True)

    return picks[:3]

# ------------------------
def main():
    predictions = build_predictions()

    if not predictions:
        print("No value bets found")
        predictions = []

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4)

    print(f"Saved {len(predictions)} predictions.")

if __name__ == "__main__":
    main()
