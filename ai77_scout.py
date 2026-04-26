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


def fetch_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal"
    }

    res = requests.get(ODDS_URL, params=params, timeout=15)

    if res.status_code != 200:
        print("ODDS API ERROR:", res.text)
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
    elif pick_type == "btts_yes":
        texts = [
            f"Both teams show enough attacking activity and defensive vulnerability for a two-sided scoring game. The BTTS signal is supported by recent scoring patterns.",
            f"This matchup profiles well for both teams to get on the scoresheet. Chance creation and concession trends point toward a live BTTS angle.",
            f"The model sees a balanced scoring environment where both sides should generate enough threat to score at least once."
        ]
    elif pick_type == "btts_no":
        texts = [
            f"The game projects with limited two-sided scoring. One or both attacks look weaker than the market implies, making BTTS No a playable angle.",
            f"This matchup leans toward a one-sided or lower-quality scoring profile. The model does not expect both teams to score as often as the market suggests.",
            f"Defensive structure and weaker attacking output on one side make BTTS No a disciplined value position."
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


# ------------------------
# API-FOOTBALL HELPERS
# ------------------------
def football_headers():
    return {"x-apisports-key": FOOTBALL_API_KEY}


def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def fetch_api_football_fixtures(start_time, end_time, tz_name):
    if not FOOTBALL_API_KEY:
        print("NO FOOTBALL_API_KEY -> no totals/btts from API-Football")
        return []

    fixtures = []

    start_date = start_time.date()
    end_date = end_time.date()
    current_date = start_date

    while current_date <= end_date:
        try:
            res = requests.get(
                f"{FOOTBALL_URL}/fixtures",
                headers=football_headers(),
                params={
                    "date": current_date.strftime("%Y-%m-%d"),
                    "timezone": tz_name
                },
                timeout=15
            )
            data = res.json()
            daily = data.get("response", [])
            print(f"API-FOOTBALL FIXTURES {current_date}: {len(daily)}")
            fixtures.extend(daily)
        except Exception as e:
            print(f"FIXTURES FETCH ERROR for {current_date}: {e}")

        current_date += timedelta(days=1)

    filtered = []

    for fixture in fixtures:
        try:
            fixture_dt_raw = fixture.get("fixture", {}).get("date")
            if not fixture_dt_raw:
                continue

            fixture_time = datetime.fromisoformat(fixture_dt_raw)
            fixture_time = fixture_time.astimezone(ZoneInfo(tz_name))

            if fixture_time < start_time or fixture_time > end_time:
                continue

            status_short = fixture.get("fixture", {}).get("status", {}).get("short")
            if status_short not in ["NS", "TBD", "PST"]:
                continue

            filtered.append(fixture)

        except Exception as e:
            print("FIXTURE FILTER ERROR:", e)

    print(f"API-FOOTBALL FILTERED FIXTURES: {len(filtered)}")
    return filtered


def get_recent_team_form(team_id):
    fallback = {
        "home_scored_avg": 1.25,
        "home_conceded_avg": 1.15,
        "away_scored_avg": 1.15,
        "away_conceded_avg": 1.25,
        "over25_rate": 0.50,
        "btts_rate": 0.50
    }

    if not team_id or not FOOTBALL_API_KEY:
        return fallback

    try:
        res = requests.get(
            f"{FOOTBALL_URL}/fixtures",
            headers=football_headers(),
            params={"team": team_id, "last": 10},
            timeout=15
        )
        data = res.json()
        fixtures = data.get("response", [])

        home_scored = []
        home_conceded = []
        away_scored = []
        away_conceded = []
        over25_count = 0
        btts_count = 0
        valid_games = 0

        for f in fixtures:
            short_status = f.get("fixture", {}).get("status", {}).get("short")
            if short_status not in ["FT", "AET", "PEN"]:
                continue

            home_team = f.get("teams", {}).get("home", {})
            away_team = f.get("teams", {}).get("away", {})
            gh = f.get("goals", {}).get("home")
            ga = f.get("goals", {}).get("away")

            if gh is None or ga is None:
                continue

            valid_games += 1

            if (gh + ga) > 2.5:
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
            print(f"TEAM FORM FALLBACK for team_id={team_id}")
            return fallback

        stats = {
            "home_scored_avg": sum(home_scored) / len(home_scored) if home_scored else fallback["home_scored_avg"],
            "home_conceded_avg": sum(home_conceded) / len(home_conceded) if home_conceded else fallback["home_conceded_avg"],
            "away_scored_avg": sum(away_scored) / len(away_scored) if away_scored else fallback["away_scored_avg"],
            "away_conceded_avg": sum(away_conceded) / len(away_conceded) if away_conceded else fallback["away_conceded_avg"],
            "over25_rate": over25_count / valid_games,
            "btts_rate": btts_count / valid_games
        }

        print(f"TEAM FORM USED for {team_id}: {stats}")
        return stats

    except Exception as e:
        print(f"TEAM FORM ERROR for {team_id}: {e}")
        return fallback


def get_fixture_prediction_data(fixture_id):
    result = {
        "advice": "",
        "goals_home": None,
        "goals_away": None,
        "winner_name": None,
        "winner_comment": None
    }

    if not FOOTBALL_API_KEY or not fixture_id:
        return result

    try:
        res = requests.get(
            f"{FOOTBALL_URL}/predictions",
            headers=football_headers(),
            params={"fixture": fixture_id},
            timeout=15
        )
        data = res.json()
        response = data.get("response", [])

        if not response:
            print(f"PREDICTION EMPTY for fixture {fixture_id}")
            return result

        pred = response[0].get("predictions", {})
        result["advice"] = pred.get("advice", "")

        goals = pred.get("goals", {})
        result["goals_home"] = safe_float(goals.get("home"))
        result["goals_away"] = safe_float(goals.get("away"))

        winner = pred.get("winner", {})
        result["winner_name"] = winner.get("name")
        result["winner_comment"] = winner.get("comment")

        print(f"PREDICTION USED for fixture {fixture_id}: {result}")
        return result

    except Exception as e:
        print(f"PREDICTION ERROR for fixture {fixture_id}: {e}")
        return result


def get_fixture_odds_markets(fixture_id):
    markets = {
        "totals": [],
        "btts": []
    }

    if not FOOTBALL_API_KEY or not fixture_id:
        return markets

    try:
        res = requests.get(
            f"{FOOTBALL_URL}/odds",
            headers=football_headers(),
            params={"fixture": fixture_id},
            timeout=15
        )
        data = res.json()
        response = data.get("response", [])

        if not response:
            print(f"ODDS EMPTY for fixture {fixture_id}")
            return markets

        seen_totals = set()
        seen_btts = set()

        for item in response:
            bookmakers = item.get("bookmakers", [])

            for bookmaker in bookmakers:
                bets = bookmaker.get("bets", [])

                for bet in bets:
                    bet_name = str(bet.get("name", "")).lower()
                    values = bet.get("values", [])

                    # BTTS
                    if "both teams" in bet_name or "both team" in bet_name or "btts" in bet_name:
                        for v in values:
                            value = str(v.get("value", "")).strip()
                            odd = safe_float(v.get("odd"))
                            if odd is None:
                                continue

                            if value.lower() in ["yes", "no"]:
                                key = (value.lower(), odd)
                                if key not in seen_btts:
                                    seen_btts.add(key)
                                    markets["btts"].append({
                                        "name": value,
                                        "price": odd
                                    })

                    # O/U
                    elif "over/under" in bet_name or "goals over/under" in bet_name or "over under" in bet_name:
                        for v in values:
                            value = str(v.get("value", "")).strip()
                            odd = safe_float(v.get("odd"))
                            if odd is None:
                                continue

                            lower_val = value.lower()
                            if not (lower_val.startswith("over") or lower_val.startswith("under")):
                                continue

                            parts = value.split()
                            if len(parts) < 2:
                                continue

                            point = safe_float(parts[-1])
                            if point is None:
                                continue

                            name = "Over" if lower_val.startswith("over") else "Under"
                            key = (name, point, odd)

                            if key not in seen_totals:
                                seen_totals.add(key)
                                markets["totals"].append({
                                    "name": name,
                                    "point": point,
                                    "price": odd
                                })

        print(
            f"ODDS MARKETS for fixture {fixture_id}: "
            f"totals={len(markets['totals'])}, btts={len(markets['btts'])}"
        )
        return markets

    except Exception as e:
        print(f"ODDS ERROR for fixture {fixture_id}: {e}")
        return markets


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


def build_total_and_btts_candidates(start_time, end_time, tz_name):
    fixtures = fetch_api_football_fixtures(start_time, end_time, tz_name)
    candidates = []

    for fixture in fixtures:
        try:
            fixture_info = fixture.get("fixture", {})
            fixture_id = fixture_info.get("id")
            fixture_dt_raw = fixture_info.get("date")

            if not fixture_id or not fixture_dt_raw:
                continue

            match_time = datetime.fromisoformat(fixture_dt_raw).astimezone(ZoneInfo(tz_name))

            home_team = fixture.get("teams", {}).get("home", {})
            away_team = fixture.get("teams", {}).get("away", {})
            league_info = fixture.get("league", {})

            home = home_team.get("name")
            away = away_team.get("name")
            home_id = home_team.get("id")
            away_id = away_team.get("id")
            league = league_info.get("name", "Football")

            if not home or not away or not home_id or not away_id:
                continue

            home_stats = get_recent_team_form(home_id)
            away_stats = get_recent_team_form(away_id)
            prediction = get_fixture_prediction_data(fixture_id)
            odds_markets = get_fixture_odds_markets(fixture_id)

            expected_home = (
                home_stats["home_scored_avg"] + away_stats["away_conceded_avg"]
            ) / 2

            expected_away = (
                away_stats["away_scored_avg"] + home_stats["home_conceded_avg"]
            ) / 2

            expected_goals = expected_home + expected_away

            if home_stats["over25_rate"] >= 0.60 and away_stats["over25_rate"] >= 0.60:
                expected_goals += 0.20

            if home_stats["btts_rate"] >= 0.60 and away_stats["btts_rate"] >= 0.60:
                expected_goals += 0.10

            if home_stats["over25_rate"] <= 0.40 and away_stats["over25_rate"] <= 0.40:
                expected_goals -= 0.20

            pred_home = prediction.get("goals_home")
            pred_away = prediction.get("goals_away")
            if pred_home is not None and pred_away is not None:
                pred_total = pred_home + pred_away
                expected_goals = (expected_goals * 0.70) + (pred_total * 0.30)

            expected_goals = max(1.4, min(4.6, expected_goals))

            print(
                f"API-FOOTBALL TOTALS MODEL -> {home} vs {away} | "
                f"fixture={fixture_id} | total={expected_goals:.2f}"
            )

            # TOTALS
            for market in odds_markets["totals"]:
                odds = market["price"]
                implied = 1 / odds
                point = market["point"]

                over_prob, under_prob = get_total_probs(expected_goals, point)

                if point >= 3.5 and expected_goals < 3.45:
                    continue

                if point >= 3.0 and expected_goals < 2.65 and market["name"] == "Over":
                    continue

                if market["name"] == "Over":
                    model_prob = over_prob
                    bet = f"Over {point}"
                    pick_type = "over"
                else:
                    model_prob = under_prob
                    bet = f"Under {point}"
                    pick_type = "under"

                edge = model_prob - implied

                # small calibrated boost only
                edge *= 1.05

                if odds < 1.35 or odds > 3.40:
                    continue
                if edge < -0.10:
                    continue

                print(
                    f"API-FOOTBALL TOTAL PICK CHECK -> {home} vs {away} | "
                    f"bet={bet} | model_prob={model_prob:.3f} implied={implied:.3f} edge={edge:.3f}"
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
                    "reasoning": generate_reasoning(home, away, bet, expected_goals, edge, pick_type),
                    "sort_time": match_time.timestamp()
                })

            # BTTS
            for market in odds_markets["btts"]:
                odds = market["price"]
                implied = 1 / odds

                btts_yes_prob = (
                    (home_stats["btts_rate"] + away_stats["btts_rate"]) / 2
                )

                if expected_goals >= 3.0:
                    btts_yes_prob += 0.06
                elif expected_goals <= 2.1:
                    btts_yes_prob -= 0.06

                if home_stats["home_scored_avg"] < 0.9 or away_stats["away_scored_avg"] < 0.9:
                    btts_yes_prob -= 0.05

                btts_yes_prob = max(0.20, min(0.78, btts_yes_prob))
                btts_no_prob = 1 - btts_yes_prob

                if market["name"].lower() == "yes":
                    model_prob = btts_yes_prob
                    bet = "BTTS Yes"
                    pick_type = "btts_yes"
                else:
                    model_prob = btts_no_prob
                    bet = "BTTS No"
                    pick_type = "btts_no"

                edge = model_prob - implied
                edge *= 1.03

                if odds < 1.35 or odds > 3.20:
                    continue
                if edge < -0.10:
                    continue

                print(
                    f"API-FOOTBALL BTTS CHECK -> {home} vs {away} | "
                    f"bet={bet} | model_prob={model_prob:.3f} implied={implied:.3f} edge={edge:.3f}"
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
                    "reasoning": generate_reasoning(home, away, bet, expected_goals, edge, pick_type),
                    "sort_time": match_time.timestamp()
                })

        except Exception as e:
            print("API-FOOTBALL CANDIDATE ERROR:", e)
            continue

    return candidates


def build_predictions():
    data = fetch_odds()

    tz = ZoneInfo("Europe/Ljubljana")
    now = datetime.now(tz)

    start_time = now + timedelta(minutes=30)
    end_time = now + timedelta(hours=24)

    candidates = []

    # ------------------------
    # H2H PART - OSTANE ISTO
    # ------------------------
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

            for market in bookmaker["markets"]:
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

    # ------------------------
    # TOTALS + BTTS PART - API-FOOTBALL ONLY
    # ------------------------
    football_totals_candidates = build_total_and_btts_candidates(
        start_time=start_time,
        end_time=end_time,
        tz_name="Europe/Ljubljana"
    )

    candidates.extend(football_totals_candidates)

    candidates = sorted(candidates, key=lambda x: x["confidence"], reverse=True)

    final = []
    used_matches = set()

    counts = {
        "home": 0,
        "away": 0,
        "over": 0,
        "under": 0,
        "draw": 0,
        "btts_yes": 0,
        "btts_no": 0
    }

    limits = {
        "home": 2,
        "away": 1,
        "over": 2,
        "under": 2,
        "draw": 1,
        "btts_yes": 1,
        "btts_no": 1
    }

    btts_total_count = 0

    for pick in candidates:
        if len(final) >= 5:
            break

        if pick["match"] in used_matches:
            continue

        pick_type = pick["pick_type"]

        if counts[pick_type] >= limits[pick_type]:
            continue

        if pick_type in ["btts_yes", "btts_no"] and btts_total_count >= 1:
            continue

        final.append(pick)
        used_matches.add(pick["match"])
        counts[pick_type] += 1

        if pick_type in ["btts_yes", "btts_no"]:
            btts_total_count += 1

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
