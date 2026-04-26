import requests
import json
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DEBUG = True

ODDS_API_KEY = os.getenv("ODDS_API_KEY_V2")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"
FOOTBALL_URL = "https://v3.football.api-sports.io"

team_form_cache = {}
fixture_prediction_cache = {}
fixture_odds_cache = {}


def dprint(*args):
    if DEBUG:
        print(*args)


def fetch_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    res = requests.get(ODDS_URL, params=params, timeout=15)

    if res.status_code != 200:
        print("ODDS API ERROR:", res.text)
        return []

    return res.json()


def football_headers():
    return {"x-apisports-key": FOOTBALL_API_KEY}


def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def build_stats_sentence(stats_summary, pick_type):
    if not stats_summary:
        return ""

    snippets = []

    exp_goals = stats_summary.get("expected_goals")
    over_rate = stats_summary.get("combined_over25_rate")
    btts_rate = stats_summary.get("combined_btts_rate")
    home_scored = stats_summary.get("home_scored_avg")
    away_scored = stats_summary.get("away_scored_avg")
    home_conceded = stats_summary.get("home_conceded_avg")
    away_conceded = stats_summary.get("away_conceded_avg")

    if pick_type in ["over", "under"]:
        if exp_goals is not None:
            snippets.append(f"The projected goal output sits around {exp_goals:.2f}.")
        if over_rate is not None:
            snippets.append(f"The combined recent Over 2.5 profile is roughly {over_rate * 100:.0f}%.")
        if home_scored is not None and away_scored is not None:
            snippets.append(
                f"Relevant attacking splits point to around {home_scored:.2f} home goals and {away_scored:.2f} away goals."
            )

    elif pick_type in ["btts_yes", "btts_no"]:
        if btts_rate is not None:
            snippets.append(f"The recent BTTS profile comes in around {btts_rate * 100:.0f}%.")
        if home_scored is not None and away_scored is not None:
            snippets.append(
                f"Both attacks project into a game state with about {home_scored:.2f} home goals and {away_scored:.2f} away goals on current splits."
            )

    elif pick_type in ["home", "away", "draw"]:
        if home_scored is not None and away_scored is not None and home_conceded is not None and away_conceded is not None:
            snippets.append(
                f"Recent split data shows about {home_scored:.2f} goals for the home side and {away_scored:.2f} for the away side, with defensive levels close enough to create pricing tension."
            )

    if not snippets:
        return ""

    return " " + random.choice(snippets)


def generate_reasoning(home, away, bet, expected_goals, edge, pick_type, stats_summary=None):
    if pick_type == "over":
        texts = [
            f"{home} and {away} project as a more open matchup than the market line suggests.",
            f"The tempo setup points toward a game with enough attacking sequences to threaten the total.",
            f"This Over is backed by a scoring profile that looks slightly stronger than the market number.",
            f"The matchup shape suggests more transitions and more usable chances than the current line implies.",
            f"There is enough offensive pressure on both sides for this total to become playable."
        ]
    elif pick_type == "under":
        texts = [
            f"This matchup projects as more controlled than the market suggests, which keeps the Under in play.",
            f"The model expects fewer clean chances than the current total line is pricing in.",
            f"This game carries a lower-event profile than the market is implying.",
            f"The likely match script looks tighter and more compact than the total number suggests.",
            f"The projection leans toward a disciplined, lower-volume game rather than a wide-open exchange."
        ]
    elif pick_type == "draw":
        texts = [
            f"This looks like a fairly balanced matchup with little separation between the sides.",
            f"The model sees a tight game profile with no strong side advantage, which brings the draw into range.",
            f"Both teams grade closely enough for the draw price to become interesting.",
            f"There is not much between these teams on the model, so the draw line deserves attention.",
            f"The match projects more evenly than the market suggests, which makes the draw playable on price."
        ]
    elif pick_type == "btts_yes":
        texts = [
            f"This matchup profiles well for both teams to get on the scoresheet.",
            f"There is enough two-way attacking threat here to keep BTTS Yes live.",
            f"The model sees a balanced scoring environment where both sides should create enough danger.",
            f"The game does not need to become wild to land BTTS; it just needs normal two-sided pressure.",
            f"Both attacks look capable of producing at least one meaningful scoring moment."
        ]
    elif pick_type == "btts_no":
        texts = [
            f"This game projects with limited two-sided scoring, which supports BTTS No.",
            f"One side looks less likely to contribute enough attacking output, making BTTS No more attractive.",
            f"The model leans toward an uneven or lower-quality scoring script rather than a clean two-team exchange.",
            f"The underlying profile points more toward one team blanking than both teams trading goals.",
            f"This is a spot where structure or weak finishing on one side can kill the BTTS line."
        ]
    elif pick_type == "home":
        texts = [
            f"{home} rates slightly stronger than the market is implying in this matchup.",
            f"The model gives {home} a better price-adjusted chance than the line suggests.",
            f"{home} comes out ahead on matchup balance, structure and value.",
            f"The number looks a bit too generous against {home} here.",
            f"{home} shows enough model support to justify a value position at this price."
        ]
    elif pick_type == "away":
        texts = [
            f"{away} looks underrated by the market in this spot.",
            f"The away side holds a better value profile than the current odds suggest.",
            f"{away} grades well enough on the model to become a live side pick.",
            f"The market appears to give {away} slightly less respect than the numbers do.",
            f"{away} has enough price value here to justify inclusion."
        ]
    else:
        texts = [
            f"The selection is supported by matchup balance and market inefficiency.",
            f"This is a value-based position rather than a momentum-based one.",
            f"The line looks a little off relative to the model’s view of the game.",
            f"The price is the real trigger here, not just the narrative around the match.",
            f"This is a calculated spot where the number creates interest."
        ]

    endings = [
        " This fits the AI77 value-based approach.",
        " Risk is always present, but the price creates a playable edge.",
        " The pick is selected because the model detects market mispricing.",
        " This is a calculated position, not a random prediction.",
        " It is not a lock, but it is strong enough to stay on the card."
    ]

    edge_sentence = ""
    if edge is not None:
        if edge >= 0.18:
            edge_sentence = " The value edge stands out clearly compared to most of the slate."
        elif edge >= 0.10:
            edge_sentence = " The edge is meaningful enough to justify selection."
        elif edge >= 0.04:
            edge_sentence = " The edge is moderate, but still strong enough to stay in range."

    stats_sentence = build_stats_sentence(stats_summary, pick_type)

    return random.choice(texts) + stats_sentence + edge_sentence + random.choice(endings)


def fetch_api_football_fixtures(start_time, end_time, tz_name):
    if not FOOTBALL_API_KEY:
        dprint("NO FOOTBALL_API_KEY -> no totals/btts from API-Football")
        return []

    fixtures = []

    current_date = start_time.date()
    while current_date <= end_time.date():
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
            dprint(f"API-FOOTBALL FIXTURES {current_date}: {len(daily)}")
            fixtures.extend(daily)
        except Exception as e:
            dprint(f"FIXTURES FETCH ERROR for {current_date}: {e}")

        current_date += timedelta(days=1)

    filtered = []

    for fixture in fixtures:
        try:
            fixture_dt_raw = fixture.get("fixture", {}).get("date")
            if not fixture_dt_raw:
                continue

            fixture_time = datetime.fromisoformat(fixture_dt_raw).astimezone(ZoneInfo(tz_name))

            if fixture_time < start_time or fixture_time > end_time:
                continue

            status_short = fixture.get("fixture", {}).get("status", {}).get("short")
            if status_short not in ["NS", "TBD", "PST"]:
                continue

            filtered.append(fixture)

        except Exception as e:
            dprint("FIXTURE FILTER ERROR:", e)

    dprint(f"API-FOOTBALL FILTERED FIXTURES: {len(filtered)}")
    return filtered


def get_recent_team_form(team_id):
    if team_id in team_form_cache:
        dprint(f"TEAM FORM CACHE USED for team_id={team_id}")
        return team_form_cache[team_id]

    fallback = {
        "home_scored_avg": 1.25,
        "home_conceded_avg": 1.15,
        "away_scored_avg": 1.15,
        "away_conceded_avg": 1.25,
        "over25_rate": 0.50,
        "btts_rate": 0.50,
        "used_fallback": True
    }

    if not team_id or not FOOTBALL_API_KEY:
        team_form_cache[team_id] = fallback
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
            dprint(f"TEAM FORM FALLBACK for team_id={team_id}")
            team_form_cache[team_id] = fallback
            return fallback

        stats = {
            "home_scored_avg": sum(home_scored) / len(home_scored) if home_scored else fallback["home_scored_avg"],
            "home_conceded_avg": sum(home_conceded) / len(home_conceded) if home_conceded else fallback["home_conceded_avg"],
            "away_scored_avg": sum(away_scored) / len(away_scored) if away_scored else fallback["away_scored_avg"],
            "away_conceded_avg": sum(away_conceded) / len(away_conceded) if away_conceded else fallback["away_conceded_avg"],
            "over25_rate": over25_count / valid_games,
            "btts_rate": btts_count / valid_games,
            "used_fallback": False
        }

        dprint(f"TEAM FORM USED for {team_id}: {stats}")
        team_form_cache[team_id] = stats
        return stats

    except Exception as e:
        dprint(f"TEAM FORM ERROR for {team_id}: {e}")
        team_form_cache[team_id] = fallback
        return fallback


def get_fixture_prediction_data(fixture_id):
    if fixture_id in fixture_prediction_cache:
        dprint(f"PREDICTION CACHE USED for fixture={fixture_id}")
        return fixture_prediction_cache[fixture_id]

    result = {
        "advice": "",
        "goals_home": None,
        "goals_away": None,
        "winner_name": None,
        "winner_comment": None
    }

    if not FOOTBALL_API_KEY or not fixture_id:
        fixture_prediction_cache[fixture_id] = result
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
            dprint(f"PREDICTION EMPTY for fixture {fixture_id}")
            fixture_prediction_cache[fixture_id] = result
            return result

        pred = response[0].get("predictions", {})
        result["advice"] = pred.get("advice", "")

        goals = pred.get("goals", {})
        gh = safe_float(goals.get("home"))
        ga = safe_float(goals.get("away"))

        if gh is not None and gh >= 0:
            result["goals_home"] = gh
        if ga is not None and ga >= 0:
            result["goals_away"] = ga

        winner = pred.get("winner", {})
        result["winner_name"] = winner.get("name")
        result["winner_comment"] = winner.get("comment")

        dprint(f"PREDICTION USED for fixture {fixture_id}: {result}")
        fixture_prediction_cache[fixture_id] = result
        return result

    except Exception as e:
        dprint(f"PREDICTION ERROR for fixture {fixture_id}: {e}")
        fixture_prediction_cache[fixture_id] = result
        return result


def get_fixture_odds_markets(fixture_id):
    if fixture_id in fixture_odds_cache:
        dprint(f"ODDS CACHE USED for fixture={fixture_id}")
        return fixture_odds_cache[fixture_id]

    markets = {
        "totals": [],
        "btts": []
    }

    if not FOOTBALL_API_KEY or not fixture_id:
        fixture_odds_cache[fixture_id] = markets
        return markets

    allowed_total_points = {2.0, 2.5, 3.0, 3.5}

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
            dprint(f"ODDS EMPTY for fixture {fixture_id}")
            fixture_odds_cache[fixture_id] = markets
            return markets

        totals_map = {}
        btts_map = {}

        for item in response:
            bookmakers = item.get("bookmakers", [])

            for bookmaker in bookmakers:
                bets = bookmaker.get("bets", [])

                for bet in bets:
                    bet_name = str(bet.get("name", "")).lower()
                    values = bet.get("values", [])

                    if "both teams" in bet_name or "both team" in bet_name or "btts" in bet_name:
                        for v in values:
                            value = str(v.get("value", "")).strip().lower()
                            odd = safe_float(v.get("odd"))
                            if odd is None:
                                continue
                            if value not in ["yes", "no"]:
                                continue

                            key = value
                            if key not in btts_map:
                                btts_map[key] = {
                                    "name": "Yes" if value == "yes" else "No",
                                    "best_odds": odd,
                                    "implied_probs": [1 / odd]
                                }
                            else:
                                btts_map[key]["best_odds"] = max(btts_map[key]["best_odds"], odd)
                                btts_map[key]["implied_probs"].append(1 / odd)

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

                            point = round(point, 2)
                            if point not in allowed_total_points:
                                continue

                            name = "Over" if lower_val.startswith("over") else "Under"
                            key = (name, point)

                            if key not in totals_map:
                                totals_map[key] = {
                                    "name": name,
                                    "point": point,
                                    "best_odds": odd,
                                    "implied_probs": [1 / odd]
                                }
                            else:
                                totals_map[key]["best_odds"] = max(totals_map[key]["best_odds"], odd)
                                totals_map[key]["implied_probs"].append(1 / odd)

        for _, entry in totals_map.items():
            avg_implied = sum(entry["implied_probs"]) / len(entry["implied_probs"])
            markets["totals"].append({
                "name": entry["name"],
                "point": entry["point"],
                "price": entry["best_odds"],
                "avg_implied": avg_implied
            })

        for _, entry in btts_map.items():
            avg_implied = sum(entry["implied_probs"]) / len(entry["implied_probs"])
            markets["btts"].append({
                "name": entry["name"],
                "price": entry["best_odds"],
                "avg_implied": avg_implied
            })

        dprint(
            f"ODDS MARKETS for fixture {fixture_id}: "
            f"totals={len(markets['totals'])}, btts={len(markets['btts'])}"
        )

        fixture_odds_cache[fixture_id] = markets
        return markets

    except Exception as e:
        dprint(f"ODDS ERROR for fixture {fixture_id}: {e}")
        fixture_odds_cache[fixture_id] = markets
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

            stats_summary = {
                "expected_goals": expected_goals,
                "combined_over25_rate": (home_stats["over25_rate"] + away_stats["over25_rate"]) / 2,
                "combined_btts_rate": (home_stats["btts_rate"] + away_stats["btts_rate"]) / 2,
                "home_scored_avg": home_stats["home_scored_avg"],
                "away_scored_avg": away_stats["away_scored_avg"],
                "home_conceded_avg": home_stats["home_conceded_avg"],
                "away_conceded_avg": away_stats["away_conceded_avg"]
            }

            dprint(
                f"API-FOOTBALL TOTALS MODEL -> {home} vs {away} | "
                f"fixture={fixture_id} | total={expected_goals:.2f}"
            )

            for market in odds_markets["totals"]:
                odds = market["price"]
                implied = market["avg_implied"]
                point = market["point"]

                over_prob, under_prob = get_total_probs(expected_goals, point)

                if point >= 3.5 and expected_goals < 3.45 and market["name"] == "Over":
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
                edge *= 1.05

                if odds < 1.35 or odds > 3.40:
                    continue
                if edge < -0.10:
                    continue

                dprint(
                    f"API-FOOTBALL TOTAL PICK CHECK -> {home} vs {away} | "
                    f"bet={bet} | model_prob={model_prob:.3f} avg_implied={implied:.3f} best_odds={odds:.3f} edge={edge:.3f}"
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
                    "reasoning": generate_reasoning(home, away, bet, expected_goals, edge, pick_type, stats_summary),
                    "sort_time": match_time.timestamp()
                })

            for market in odds_markets["btts"]:
                odds = market["price"]
                implied = market["avg_implied"]

                btts_yes_prob = ((home_stats["btts_rate"] + away_stats["btts_rate"]) / 2)

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

                dprint(
                    f"API-FOOTBALL BTTS CHECK -> {home} vs {away} | "
                    f"bet={bet} | model_prob={model_prob:.3f} avg_implied={implied:.3f} best_odds={odds:.3f} edge={edge:.3f}"
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
                    "reasoning": generate_reasoning(home, away, bet, expected_goals, edge, pick_type, stats_summary),
                    "sort_time": match_time.timestamp()
                })

        except Exception as e:
            dprint("API-FOOTBALL CANDIDATE ERROR:", e)
            continue

    return candidates


def build_predictions():
    data = fetch_odds()

    tz = ZoneInfo("Europe/Ljubljana")
    now = datetime.now(tz)

    start_time = now + timedelta(minutes=30)
    end_time = now + timedelta(hours=24)

    h2h_candidates = []
    goal_candidates = []

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

            stats_summary = {
                "expected_goals": expected_goals,
                "home_scored_avg": expected_home,
                "away_scored_avg": expected_away,
                "home_conceded_avg": expected_away,
                "away_conceded_avg": expected_home
            }

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

                        h2h_candidates.append({
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
                            "reasoning": generate_reasoning(home, away, bet, expected_goals, edge, pick_type, stats_summary),
                            "sort_time": match_time.timestamp()
                        })

        except Exception as e:
            dprint("GAME ERROR:", e)
            continue

    goal_candidates = build_total_and_btts_candidates(
        start_time=start_time,
        end_time=end_time,
        tz_name="Europe/Ljubljana"
    )

    h2h_candidates = sorted(h2h_candidates, key=lambda x: x["confidence"], reverse=True)
    goal_candidates = sorted(goal_candidates, key=lambda x: x["confidence"], reverse=True)

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

    h2h_limits = {"home": 2, "away": 1, "draw": 1}
    goal_limits = {"over": 2, "under": 2, "btts_yes": 1, "btts_no": 1}

    btts_total_count = 0
    goals_total_count = 0

    # 3 H2H
    for pick in h2h_candidates:
        if len(final) >= 3:
            break
        if pick["match"] in used_matches:
            continue
        if counts[pick["pick_type"]] >= h2h_limits[pick["pick_type"]]:
            continue

        final.append(pick)
        used_matches.add(pick["match"])
        counts[pick["pick_type"]] += 1

    # 2 goals
    for pick in goal_candidates:
        if len(final) >= 5:
            break
        if goals_total_count >= 2:
            break
        if pick["match"] in used_matches:
            continue
        if counts[pick["pick_type"]] >= goal_limits[pick["pick_type"]]:
            continue
        if pick["pick_type"] in ["btts_yes", "btts_no"] and btts_total_count >= 1:
            continue

        final.append(pick)
        used_matches.add(pick["match"])
        counts[pick["pick_type"]] += 1
        goals_total_count += 1

        if pick["pick_type"] in ["btts_yes", "btts_no"]:
            btts_total_count += 1

    # fallback fill
    if len(final) < 5:
        combined_fallback = sorted(h2h_candidates + goal_candidates, key=lambda x: x["confidence"], reverse=True)

        for pick in combined_fallback:
            if len(final) >= 5:
                break
            if pick["match"] in used_matches:
                continue

            pt = pick["pick_type"]

            if pt in h2h_limits:
                if counts[pt] >= h2h_limits[pt]:
                    continue
            elif pt in goal_limits:
                if counts[pt] >= goal_limits[pt]:
                    continue
                if pt in ["btts_yes", "btts_no"] and btts_total_count >= 1:
                    continue
                if goals_total_count >= 2:
                    continue

            final.append(pick)
            used_matches.add(pick["match"])
            counts[pt] += 1

            if pt in ["over", "under", "btts_yes", "btts_no"]:
                goals_total_count += 1
            if pt in ["btts_yes", "btts_no"]:
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

    dprint("DEBUG predictions:", len(predictions))
    dprint("DEBUG history before:", len(history))

    for pick in predictions:
        new_pick = pick.copy()
        new_pick["result"] = "pending"
        history.append(new_pick)

    dprint("DEBUG history after:", len(history))

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

    with open(history_file, "a", encoding="utf-8") as f:
        f.write("\n")

    print(f"Saved {len(predictions)} predictions and updated results.json.")


if __name__ == "__main__":
    main()
