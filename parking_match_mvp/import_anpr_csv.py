import csv
import json
import sys
import urllib.request

if len(sys.argv) != 2:
    raise SystemExit("用法：python import_anpr_csv.py plates.csv")
with open(sys.argv[1], newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        plate = row.get("plate") or row.get("text") or row.get("license_plate")
        if not plate:
            continue
        payload = json.dumps({"plate": plate, "confidence": row.get("confidence"), "camera": "ANPR CSV"}).encode()
        req = urllib.request.Request("http://127.0.0.1:8080/api/recognitions", data=payload, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req) as response:
            print(response.read().decode())
