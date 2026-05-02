import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

ISPORTS_API_KEY = os.getenv("ISPORTS_API_KEY")
BASES = [
    "http://api.isportsapi.com",
    "http://api2.isportsapi.com",
]

PATHS = [
    "/sport/basketball/odds/main",
    "/sport/basketball/odds",
    "/sport/basketball/odds/list",
    "/sport/basketball/bookmaker",
    "/sport/basketball/schedule",
]

today = datetime.now(ZoneInfo("Europe/Ljubljana")).strftime("%Y-%m-%d")

if not ISPORTS_API_KEY:
    raise RuntimeError("Missing ISPORTS_API_KEY")

for base in BASES:
    for path in PATHS:
        params = {"api_key": ISPORTS_API_KEY}

        if path.endswith("/schedule"):
            params["date"] = today

        print("=" * 90)
        print(base + path)
        print("PARAMS:", {k: ("***" if k == "api_key" else v) for k, v in params.items()})

        try:
            r = requests.get(base + path, params=params, timeout=30)
            print("STATUS:", r.status_code)
            data = r.json()
            print("CODE:", data.get("code"))
            print("MESSAGE:", data.get("message"))
            print("KEYS:", list(data.keys()))

            d = data.get("data")
            print("DATA TYPE:", type(d).__name__)

            if isinstance(d, list):
                print("DATA LEN:", len(d))
                if d:
                    print("FIRST ITEM:")
                    print(json.dumps(d[0], indent=2, ensure_ascii=False)[:4000])

            elif isinstance(d, dict):
                print("DATA KEYS:", list(d.keys()))
                print("DATA PREVIEW:")
                print(json.dumps(d, indent=2, ensure_ascii=False)[:4000])

            else:
                print("DATA:", d)

        except Exception as e:
            print("ERROR:", e)
