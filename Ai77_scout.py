import requests
import json
from datetime import datetime, timedelta

# --- KONFIGURACIJA ---
API_KEY = "7b08a67045mshf14f43b059212bfp17e1eajsnb9a13dec679a"
HOST = "football-prediction-api.p.rapidapi.com"
# Lige, ki jih spremljamo (39=Premier League, 140=La Liga, 135=Serie A, 78=Bundesliga)
LEAGUES = [39, 140, 135, 78]

def get_top_matches():
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    
    # Pridobimo tekme za jutri
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    all_predictions = []

    for league in LEAGUES:
        # 1. Poiščemo tekme v tej ligi za jutri
        fixtures_url = f"https://{HOST}/fixtures?league={league}&date={tomorrow}"
        response = requests.get(fixtures_url, headers=headers).json()
        
        if not response.get('response'):
            continue

        # Vzamemo max 2 tekmi na ligo, da ni preveč
        for item in response['response'][:2]:
            fixture_id = item['fixture']['id']
            
            # 2. Za vsako tekmo vprašamo API za AI napoved
            pred_url = f"https://{HOST}/predictions?fixture={fixture_id}"
            pred_res = requests.get(pred_url, headers=headers).json()
            
            if pred_res.get('response'):
                data = pred_res['response'][0]
                
                # Izvlečemo pametne podatke
                match_name = f"{item['teams']['home']['name']} - {item['teams']['away']['name']}"
                league_name = item['league']['name']
                advice = data['predictions']['advice']
                confidence = data['predictions']['percent']['home'] # poenostavljeno
                
                # Ustvarimo "Reasoning" na podlagi statistike iz API-ja
                h2h = data['comparison']['h2h']['home']
                goals = data['comparison']['goals']['home']
                reason = f"AI Analysis: {match_name} shows a strong {advice}. Home team H2H strength is at {h2h}, with an expected goal conversion of {goals}."

                all_predictions.append({
                    "date": tomorrow,
                    "sport": "football",
                    "league": league_name,
                    "match": match_name,
                    "bet": advice,
                    "confidence": int(float(confidence.replace('%',''))),
                    "reasoning": reason
                })

    # Shranimo v tvoj JSON
    with open('predictions.json', 'w', encoding='utf-8') as f:
        json.dump(all_predictions[:3], f, indent=4) # Vzamemo top 3 tekme skupaj
    print("Predictions updated successfully!")

if __name__ == "__main__":
    get_top_matches()

