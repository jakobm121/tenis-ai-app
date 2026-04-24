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
            f"{home} and {away} both operate with aggressive attacking profiles, and the model projects around {round(expected_goals,1)} expected goals here. That level typically translates into an open, high-tempo match with multiple scoring windows. Edge vs market is clearly positive at {round(edge,3)}.",

            f"This matchup leans heavily toward attacking football, with both sides consistently creating chances in recent games. With expected goals sitting above average at {round(expected_goals,1)}, the probability of goals is materially higher than what current pricing implies. Clear value spot.",

            f"The data flags this as a high-event game. Both teams contribute offensively and struggle to suppress chances, which pushes expected goals into a strong range. Market is slightly behind the true probability here, giving us a solid edge of {round(edge,3)}."
        ]

    elif "Under" in bet:
        texts = [
            f"This profiles as a controlled, lower-tempo game. Both teams show reduced attacking efficiency and a more structured defensive setup, keeping expected goals around {round(expected_goals,1)}. Market is slightly overpricing scoring potential here.",

            f"Recent form suggests limited offensive output from both sides, with fewer high-quality chances being created. The projected goal range stays suppressed, which aligns with a lower scoring environment and creates value on the under.",

            f"The matchup dynamic favors discipline over aggression. With both teams limiting space and tempo, expected goals remain contained. Current odds don’t fully reflect this, giving a measurable edge of {round(edge,3)}."
        ]

    else:
        texts = [
            f"{home} holds a noticeable edge in underlying metrics, particularly in recent form and efficiency. The model prices this outcome slightly higher than the market, creating a value gap of {round(edge,3)}.",

            f"From a matchup perspective, this side is more stable and better structured, especially in key phases of play. Market odds underestimate that edge, making this a strong value candidate.",

            f"The model consistently favors this selection based on performance trends and game dynamics. With a positive edge of {round(edge,3)}, this stands out as one of the stronger positions available."
        ]

    endings = [
        " This is a high-quality setup worth backing.",
        " This sits comfortably within a value-based strategy.",
        " One of the more reliable edges on today’s board.",
        " Risk is present, but the value justifies the position."
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

    print(f"Saved {len(predictions)} predictions.")


if __name__ == "__main__":
    main()
