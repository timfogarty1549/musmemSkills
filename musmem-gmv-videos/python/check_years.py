import json
import sys
import urllib.parse
import urllib.request

for name in sys.argv[1:]:
    url = f"http://localhost:3000/api/contest/years?name={urllib.parse.quote(name)}"
    try:
        data = json.load(urllib.request.urlopen(url, timeout=5))
        years = data.get("data", {}).get("years", [])
        print(f"{name}: {years}")
    except Exception as e:
        print(f"{name}: ERROR {e}")
