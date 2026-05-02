import os
import json
import requests

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://v1.basketball.api-sports.io"

res = requests.get(
    BASE_URL + "/games",
    headers={"x-apisports-key": API_KEY},
    params={"team": 1381, "season": 2026},
    timeout=30,
)

print(res.status_code)
print(json.dumps(res.json(), indent=2, ensure_ascii=False)[:5000])
