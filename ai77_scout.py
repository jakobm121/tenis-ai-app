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

LEAGUE_STRENGTH = {
    "EPL": 1.10,
    "La Liga": 1.08,
    "Serie A": 1.07,
    "Bundesliga": 1.07,
    "Ligue 1": 1.04,
}


def fetch_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals,btts",
        "oddsFormat": "decimal"
    }

    res = requests.get(ODDS_URL, params=params, timeout=15)

    if res.status_code != 200:
        print(res.text)
        return []

    return res.json()


def get_team_stats(team):
    if team in team_cache:
        return team_cache[team]

    try:
        headers = {"x-apisports-key": FOOTBALL_API_KEY}

        res = requests.get(
            f"{FOOTBALL_URL}/teams",
            headers=headers,
            params={"search": team},
            timeout=6
        )

        data = res.json()

        if not data.get("response"):
            team_cache[team] = (1.2, 1.2)
            return (1.2, 1.2)

        team_id = data["response"][0]["team"]["id"]

        res = requests.get(
            f"{FOOTBALL_URL}/fixtures",
            headers=headers,
            params={"team": team_id, "last": 5},
            timeout=6
        )

        fixtures = res.json().get("response", [])

        goals_for = 0
        goals_against = 0

        for f in fixtures:
            goals_for += f["goals"]["for"] or 0
            goals_against += f["goals"]["against"] or 0

        games = max(len(fixtures), 1)

        avg_for = goals_for / games
        avg_against = goals_against / games

        team_cache[team] = (avg_for, avg_against)
        return (avg_for, avg_against)

    except Exception as e:
        print("Team stats error:", e)
        team_cache[team] = (1.2, 1.2)
        return (1.2, 1.2)


def league_multiplier(league):
    for key, value in LEAGUE_STRENGTH.items():
        if key.lower() in league.lower():
            return value
    return 1.00


def kelly_stake(probability, odds):
    try:
        b = odds - 1
        q = 1 - probability
        stake = ((b * probability) - q) / b

        stake = max(0, min(stake, 0.05))  # max 5% bankroll
        return round(stake * 100, 2)
    except:
        return 0


def generate_reasoning(home, away, bet, edge, odds, expected_goals, stake):
    if "Over" in bet:
        texts = [
            f"Both teams show attacking upside, with projected goals around {round(expected_goals,1)}. {bet} offers value at current odds.",
            f"The goal model expects an open match between {home} and {away}. {bet} is the strongest angle here.",
            f"Recent scoring trends point toward goals. {bet} stands out with a positive market edge."
        ]

    elif "Under" in bet:
        texts = [
            f"The model projects a tighter game with limited goal volume. {bet} looks like the best value.",
            f"Defensive numbers suggest this match may stay controlled. {bet} is supported by the data.",
            f"Expected goal output is modest, making {bet} a logical value position."
        ]

    elif "BTTS" in bet:
        texts = [
            f"Both teams show enough attacking production to support {bet}. The model sees value at odds {odds}.",
            f"Scoring profiles suggest both sides can find the net. {bet} is the preferred market.",
            f"Team goal trends make {bet} an interesting value angle in this matchup."
        ]

    else:
        texts = [
            f"{bet} rates higher in the model than the market suggests. The current odds offer value.",
            f"The model gives {bet} a stronger chance than implied by the odds.",
            f"Recent performance and market pricing point toward value on {bet}."
        ]

    base = random.choice(texts)
    return f"{base} Suggested stake: {stake}% of bankroll."


def build_predictions():
    data = fetch_odds()
    picks = []

    for game in data:
        try:
            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            multiplier = league_multiplier(league)

            home_for, home_against = get_team_stats(home)
            away_for, away_against = get_team_stats(away)

            expected_home = ((home_for + away_against) / 2) + 0.15
            expected_away = (away_for + home_against) / 2
            expected_goals = (expected_home + expected_away) * multiplier

            total_goal_power = max(expected_goals, 0.5)

            home_prob = expected_home / max(expected_home + expected_away, 0.1)
            away_prob = expected_away / max(expected_home + expected_away, 0.1)
            draw_prob = 0.22

            over_prob = min(0.85, total_goal_power / 3)
            under_prob = 1 - over_prob

            btts_yes_prob = min(0.82, ((home_for + away_for) / 4) + 0.35)
            btts_no_prob = 1 - btts_yes_prob

            if not game.get("bookmakers"):
                continue

            bookmaker = game["bookmakers"][0]

            best_edge = -999
            best_pick = None
            best_prob = 0

            for market in bookmaker.get("markets", []):

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
                            best_prob = model_prob

                elif market["key"] == "totals":
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
                            best_prob = model_prob

                elif market["key"] == "btts":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"].lower() in ["yes", "btts yes"]:
                            model_prob = btts_yes_prob
                            label = "BTTS Yes"
                        else:
                            model_prob = btts_no_prob
                            label = "BTTS No"

                        edge = model_prob - implied

                        if edge > best_edge:
                            best_edge = edge
                            best_pick = (label, odds)
                            best_prob = model_prob

            if not best_pick:
                continue

            if best_edge < -0.02:
                continue

            odds = best_pick[1]
            stake = kelly_stake(best_prob, odds)

            confidence = int(50 + best_edge * 400)

            if odds < 2.0:
                confidence += 5
            if odds > 3.5:
                confidence -= 7
            if "Draw" in best_pick[0]:
                confidence -= 8

            confidence = max(55, min(confidence, 92))

            reasoning = generate_reasoning(
                home, away, best_pick[0], best_edge, odds, expected_goals, stake
            )

            picks.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sport": "football",
                "league": league,
                "match": f"{home} - {away}",
                "bet": best_pick[0],
                "confidence": confidence,
                "reasoning": reasoning,
                "odds": odds,
                "edge": round(best_edge, 3),
                "stake": stake
            })

        except Exception as e:
            print("Game error:", e)
            continue

    picks = sorted(picks, key=lambda x: (x["confidence"], x.get("edge", 0)), reverse=True)

    return picks[:3]


def main():
    predictions = build_predictions()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(predictions)} predictions.")


if __name__ == "__main__":
    main()
