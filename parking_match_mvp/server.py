import json
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
DB = ROOT / "parking_match.db"
INDEX = ROOT / "index.html"


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = connect()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS vehicles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      plate TEXT UNIQUE NOT NULL,
      guest_name TEXT NOT NULL,
      reservation_ref TEXT,
      category TEXT NOT NULL DEFAULT 'guest',
      active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS recognitions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      plate TEXT NOT NULL,
      confidence REAL,
      camera TEXT,
      recognized_at TEXT NOT NULL,
      match_status TEXT NOT NULL,
      guest_name TEXT,
      reservation_ref TEXT
    );
    """)
    if db.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO vehicles(plate,guest_name,reservation_ref,category) VALUES(?,?,?,?)",
            [("ABC-1234", "王先生", "BK-20261101-001", "guest"),
             ("XYZ-7788", "白石顧問團隊", "STAFF-001", "staff"),
             ("KLM-5566", "李小姐", "VISITOR-20261101-03", "visitor")],
        )
    db.commit()
    db.close()


def normalize_plate(value):
    return "".join(ch for ch in value.upper().strip() if ch.isalnum() or ch == "-")


def classify(db, plate):
    row = db.execute("SELECT * FROM vehicles WHERE plate=? AND active=1", (plate,)).fetchone()
    if row is None:
        return "unknown", None
    return row["category"], row


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/vehicles":
            db = connect()
            rows = [dict(r) for r in db.execute("SELECT * FROM vehicles ORDER BY id DESC")]
            db.close()
            self.send_json(rows)
            return
        if path == "/api/recognitions":
            db = connect()
            rows = [dict(r) for r in db.execute("SELECT * FROM recognitions ORDER BY id DESC LIMIT 50")]
            db.close()
            self.send_json(rows)
            return
        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return
        if path == "/api/recognitions":
            plate = normalize_plate(str(data.get("plate", "")))
            if not plate:
                self.send_json({"error": "plate is required"}, 400)
                return
            db = connect()
            status, match = classify(db, plate)
            now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
            db.execute(
                "INSERT INTO recognitions(plate,confidence,camera,recognized_at,match_status,guest_name,reservation_ref) VALUES(?,?,?,?,?,?,?)",
                (plate, data.get("confidence"), data.get("camera", "入口車道"), now, status,
                 match["guest_name"] if match else None, match["reservation_ref"] if match else None),
            )
            db.commit()
            result = {"plate": plate, "confidence": data.get("confidence"), "camera": data.get("camera", "入口車道"),
                      "recognized_at": now, "match_status": status,
                      "guest_name": match["guest_name"] if match else None,
                      "reservation_ref": match["reservation_ref"] if match else None}
            db.close()
            self.send_json(result, 201)
            return
        self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    init_db()
    print("Parking Match MVP: http://127.0.0.1:8080")
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
