import os
import json
import requests

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"

GAME_ID = "493685"

res = requests.get(
    BASE_URL + "/odds",
    headers={"x-apisports-key": API_KEY},
    params={"game": GAME_ID},
    timeout=30,
)

print("STATUS:", res.status_code)
data = res.json()
print(json.dumps(data, indent=2, ensure_ascii=False)[:6000])
