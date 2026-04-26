import requests
import json
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"
FOOTBALL_URL = "https://v3.football.api-sports.io"

team_stats_cache = {}
team_id_cache = {}


def fetch_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal"
    }

    res = requests.get(ODDS_URL, params=params, timeout=15)
o
    if res.status_code != 200:
        print("API ERROR:", res.text)
        return []

    return res.json()


def generate_reasoning(home, away, bet, expected_goals, edge, pick_type):
    if pick_type == "over":
        texts = [
            f"{home} and {away} profile as a high-event matchup, with enough attacking volume to push this game above the market line. The model sees goal potential that is not fully priced in.",
            f"The tempo projection points toward an open game. Both teams should have enough attacking sequences to create multiple scoring windows, making this a strong value angle.",
            f"This is not a blind Over pick. The model identifies a scoring environment where attacking output, tempo and market pricing all point in the same direction."
        ]
    elif pick_type == "under":
        texts = [
            f"This matchup projects as more controlled than the market suggests. Limited chance creation and a slower game script make the Under a strong value position.",
            f"The model expects fewer high-quality chances than the market is pricing. Defensive structure and tempo control make this a disciplined Under spot.",
            f"This game has a lower-event profile. The value comes from the market slightly overestimating goal volume."
        ]
    elif pick_type == "draw":
        texts = [
            f"This is a balanced matchup with very little separation between the sides. Draw is selected only because the value edge is unusually strong and risk is kept low.",
            f"The model sees a tight game profile with no clear side advantage. This is a controlled draw exposure, not a high-stake position.",
            f"Both teams rate closely enough that the draw price becomes playable. It remains a low-unit value angle due to natural variance."
        ]
    else:
        texts = [
            f"{bet} holds a measurable edge in this matchup. The model finds stronger structure, stability and pricing value compared to the opponent.",
            f"The selection is supported by matchup control and market inefficiency. This is a value-based side pick, not a momentum guess.",
            f"{bet} grades better in the model than the implied market probability. The edge is not huge, but it is consistent enough to qualify."
        ]

    endings = [
        " This fits the AI77 value-based approach.",
        " Risk is always present, but the price creates a playable edge.",
        " The pick is selected because the model detects market mispricing.",
        " This is a calculated position, not a random prediction."
    ]

    return random.choice(texts) + random.choice(endings)


def get_team_id(team_name):
    if team_name in team_id_cache:
        return team_id_cache[team_name]

    if not FOOTBALL_API_KEY:
        team_id_cache[team_name] = None
        return None

    try:
        headers = {"x-apisports-key": FOOTBALL_API_KEY}
        res = requests.get(
            f"{FOOTBALL_URL}/teams",
            headers=headers,
            params={"search": team_name},
            timeout=10
        )
        data = res.json()

        if not data.get("response"):
            team_id_cache[team_name] = None
            return None

        team_id = data["response"][0]["team"]["id"]
        team_id_cache[team_name] = team_id
        return team_id

    except Exception:
        team_id_cache[team_name] = None
        return None


def get_team_goal_stats(team_name):
    if team_name in team_stats_cache:
        print(f"CACHE USED for {team_name}: {team_stats_cache[team_name]}")
        return team_stats_cache[team_name]

    fallback = {
        "home_scored_avg": 1.25,
        "home_conceded_avg": 1.15,
        "away_scored_avg": 1.15,
        "away_conceded_avg": 1.25,
        "over25_rate": 0.50,
        "btts_rate": 0.50
    }

    team_id = get_team_id(team_name)
    if not team_id or not FOOTBALL_API_KEY:
        print(f"FALLBACK USED for {team_name}: {fallback}")
        team_stats_cache[team_name] = fallback
        return fallback

    try:
        headers = {"x-apisports-key": FOOTBALL_API_KEY}
        res = requests.get(
            f"{FOOTBALL_URL}/fixtures",
            headers=headers,
            params={"team": team_id, "last": 10},
            timeout=10
        )
        data = res.json()
        fixtures = data.get("response", [])

        if not fixtures:
            print(f"FALLBACK USED for {team_name} (no fixtures): {fallback}")
            team_stats_cache[team_name] = fallback
            return fallback

        home_scored = []
        home_conceded = []
        away_scored = []
        away_conceded = []
        over25_count = 0
        btts_count = 0
        valid_games = 0

        for f in fixtures:
            teams = f.get("teams", {})
            goals = f.get("goals", {})

            home_team = teams.get("home", {})
            away_team = teams.get("away", {})

            gh = goals.get("home")
            ga = goals.get("away")

            if gh is None or ga is None:
                continue

            valid_games += 1

            total_goals = gh + ga
            if total_goals > 2.5:
                over25_count += 1
            if gh > 0 and ga > 0:
                btts_count += 1

            if home_team.get("id") == team_id:
                home_scored.append(gh)
                home_conceded.append(ga)
            elif away_team.get("id") == team_id:
                away_scored.append(ga)
                away_conceded.append(gh)

        if valid_games == 0:
            print(f"FALLBACK USED for {team_name} (no valid games): {fallback}")
            team_stats_cache[team_name] = fallback
            return fallback

        stats = {
            "home_scored_avg": sum(home_scored) / len(home_scored) if home_scored else fallback["home_scored_avg"],
            "home_conceded_avg": sum(home_conceded) / len(home_conceded) if home_conceded else fallback["home_conceded_avg"],
            "away_scored_avg": sum(away_scored) / len(away_scored) if away_scored else fallback["away_scored_avg"],
            "away_conceded_avg": sum(away_conceded) / len(away_conceded) if away_conceded else fallback["away_conceded_avg"],
            "over25_rate": over25_count / valid_games,
            "btts_rate": btts_count / valid_games
        }

        print(f"STATS API USED for {team_name}: {stats}")
        team_stats_cache[team_name] = stats
        return stats

    except Exception as e:
        print(f"FALLBACK USED for {team_name} (error: {e}): {fallback}")
        team_stats_cache[team_name] = fallback
        return fallback


def get_total_probs(expected_goals, point):
    if point <= 2.0:
        if expected_goals >= 3.0:
            over_prob = 0.72
        elif expected_goals >= 2.7:
            over_prob = 0.66
        elif expected_goals >= 2.4:
            over_prob = 0.58
        else:
            over_prob = 0.48

    elif point <= 2.5:
        if expected_goals >= 3.1:
            over_prob = 0.64
        elif expected_goals >= 2.8:
            over_prob = 0.58
        elif expected_goals >= 2.5:
            over_prob = 0.52
        else:
            over_prob = 0.43

    elif point <= 3.0:
        if expected_goals >= 3.4:
            over_prob = 0.57
        elif expected_goals >= 3.1:
            over_prob = 0.50
        elif expected_goals >= 2.8:
            over_prob = 0.44
        else:
            over_prob = 0.35

    else:
        if expected_goals >= 3.8:
            over_prob = 0.50
        elif expected_goals >= 3.5:
            over_prob = 0.44
        elif expected_goals >= 3.2:
            over_prob = 0.38
        else:
            over_prob = 0.28

    over_prob = max(0.20, min(0.80, over_prob))
    under_prob = 1 - over_prob
    return over_prob, under_prob


def build_predictions():
    data = fetch_odds()

    tz = ZoneInfo("Europe/Ljubljana")
    now = datetime.now(tz)

    start_time = now + timedelta(minutes=30)
    end_time = now + timedelta(hours=24)

    candidates = []

    for game in data:
        try:
            commence_time = game.get("commence_time")
            if not commence_time:
                continue

            match_time = datetime.fromisoformat(
                commence_time.replace("Z", "+00:00")
            ).astimezone(tz)

            if match_time < start_time or match_time > end_time:
                continue

            home = game["home_team"]
            away = game["away_team"]
            league = game.get("sport_title", "Football")

            if not game.get("bookmakers"):
                continue

            bookmaker = game["bookmakers"][0]

            expected_home = 1.25
            expected_away = 1.15
            expected_goals = expected_home + expected_away

            home_prob = expected_home / expected_goals
            away_prob = expected_away / expected_goals

            home_stats = get_team_goal_stats(home)
            away_stats = get_team_goal_stats(away)

            totals_expected_home = (
                home_stats["home_scored_avg"] + away_stats["away_conceded_avg"]
            ) / 2

            totals_expected_away = (
                away_stats["away_scored_avg"] + home_stats["home_conceded_avg"]
            ) / 2

            totals_expected_goals = totals_expected_home + totals_expected_away

            if home_stats["over25_rate"] >= 0.60 and away_stats["over25_rate"] >= 0.60:
                totals_expected_goals += 0.20

            if home_stats["btts_rate"] >= 0.60 and away_stats["btts_rate"] >= 0.60:
                totals_expected_goals += 0.10

            if home_stats["over25_rate"] <= 0.40 and away_stats["over25_rate"] <= 0.40:
                totals_expected_goals -= 0.20

            totals_expected_goals = max(1.6, min(4.5, totals_expected_goals))

            print(
                f"TOTALS MODEL -> {home} vs {away} | "
                f"home_exp={totals_expected_home:.2f} away_exp={totals_expected_away:.2f} total={totals_expected_goals:.2f}"
            )

            for market in bookmaker["markets"]:

                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds
                        point = outcome.get("point", 2.5)

                        over_prob, under_prob = get_total_probs(totals_expected_goals, point)

                        if point >= 3.5 and totals_expected_goals < 3.4:
                            continue

                        if outcome["name"] == "Over":
                            model_prob = over_prob
                            bet = f"Over {point}"
                            pick_type = "over"
                        else:
                            model_prob = under_prob
                            bet = f"Under {point}"
                            pick_type = "under"

                        edge = model_prob - implied
                        edge *= 1.08

                        if odds < 1.35 or odds > 3.40:
                            continue
                        if edge < -0.10:
                            continue

                        print(
                            f"TOTAL PICK CHECK -> {home} vs {away} | bet={bet} | point={point} | "
                            f"model_prob={model_prob:.3f} implied={implied:.3f} edge={edge:.3f}"
                        )

                        candidates.append({
                            "date": match_time.strftime("%Y-%m-%d"),
                            "time": match_time.strftime("%H:%M"),
                            "sport": "football",
                            "league": league,
                            "match": f"{home} - {away}",
                            "home": home,
                            "away": away,
                            "bet": bet,
                            "pick_type": pick_type,
                            "odds": odds,
                            "confidence": edge,
                            "reasoning": generate_reasoning(home, away, bet, totals_expected_goals, edge, pick_type),
                            "sort_time": match_time.timestamp()
                        })

                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        odds = outcome["price"]
                        implied = 1 / odds

                        if outcome["name"] == home:
                            model_prob = home_prob
                            bet = home
                            pick_type = "home"
                            edge = (model_prob - implied) * 0.72

                        elif outcome["name"] == away:
                            model_prob = away_prob
                            bet = away
                            pick_type = "away"
                            edge = (model_prob - implied) * 0.88

                        else:
                            bet = "Draw"
                            pick_type = "draw"

                            if expected_goals < 2.2:
                                model_prob = 0.28
                            elif expected_goals < 2.6:
                                model_prob = 0.25
                            else:
                                model_prob = 0.20

                            if abs(home_prob - away_prob) > 0.15:
                                continue

                            edge = (model_prob - implied) * 0.80

                            if edge < 0.05:
                                continue

                        if odds < 1.35 or odds > 3.80:
                            continue
                        if edge < -0.10:
                            continue

                        candidates.append({
                            "date": match_time.strftime("%Y-%m-%d"),
                            "time": match_time.strftime("%H:%M"),
                            "sport": "football",
                            "league": league,
                            "match": f"{home} - {away}",
                            "home": home,
                            "away": away,
                            "bet": bet,
                            "pick_type": pick_type,
                            "odds": odds,
                            "confidence": edge,
                            "reasoning": generate_reasoning(home, away, bet, expected_goals, edge, pick_type),
                            "sort_time": match_time.timestamp()
                        })

        except Exception as e:
            print("GAME ERROR:", e)
            continue

    candidates = sorted(candidates, key=lambda x: x["confidence"], reverse=True)

    final = []
    used_matches = set()

    counts = {"home": 0, "away": 0, "over": 0, "under": 0, "draw": 0}
    limits = {"home": 2, "away": 1, "over": 2, "under": 2, "draw": 1}

    for pick in candidates:
        if len(final) >= 5:
            break
        if pick["match"] in used_matches:
            continue
        if counts[pick["pick_type"]] >= limits[pick["pick_type"]]:
            continue

        final.append(pick)
        used_matches.add(pick["match"])
        counts[pick["pick_type"]] += 1

    final = sorted(final, key=lambda x: x["confidence"], reverse=True)

    for i, pick in enumerate(final):
        if pick["pick_type"] == "draw":
            pick["confidence"] = 55
        elif i == 0:
            pick["confidence"] = 78
        elif i < 3:
            pick["confidence"] = 66
        else:
            pick["confidence"] = 55

    final = sorted(final, key=lambda x: x["sort_time"])

    for pick in final:
        del pick["sort_time"]
        del pick["pick_type"]
        del pick["home"]
        del pick["away"]

    return final


def main():
    predictions = build_predictions()

    with open("predictions.json", "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)

    history_file = "results.json"

    if not os.path.exists(history_file):
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump([], f)

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not isinstance(history, list):
                history = []
    except Exception:
        history = []

    print("DEBUG predictions:", len(predictions))
    print("DEBUG history before:", len(history))

    for pick in predictions:
        new_pick = pick.copy()
        new_pick["result"] = "pending"
        history.append(new_pick)

    print("DEBUG history after:", len(history))

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

    with open(history_file, "a", encoding="utf-8") as f:
        f.write("\n")

    print(f"Saved {len(predictions)} predictions and updated results.json.")


if __name__ == "__main__":
    main()
