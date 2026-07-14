import json
import sqlite3
from pathlib import Path

# Simulate worker.py logic
token_data = {
    "target": "example.com",
    "cookie": "cf_clearance=test_cookie",
    "ua": "test_ua",
    "headers": json.dumps({"X-Test": "Header"})
}

db_path = Path("files/intelligence.db")
db_path.parent.mkdir(parents=True, exist_ok=True)

print(f"[*] Testing persistence for {token_data['target']}...")

with sqlite3.connect(db_path, timeout=10.0) as conn:
    cursor = conn.cursor()
    # Table should have been created by start.py replace earlier, but just in case:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bypass_intelligence (
            target TEXT PRIMARY KEY,
            cookie TEXT,
            ua TEXT,
            ja3 TEXT,
            headers TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        INSERT INTO bypass_intelligence (target, cookie, ua, headers, last_updated)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(target) DO UPDATE SET
            cookie=excluded.cookie,
            ua=excluded.ua,
            headers=COALESCE(excluded.headers, headers),
            last_updated=CURRENT_TIMESTAMP
    ''', (token_data["target"], token_data["cookie"], token_data["ua"], token_data["headers"]))
    conn.commit()

print("[*] Data inserted. Verifying...")

with sqlite3.connect(db_path) as conn:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bypass_intelligence WHERE target=?', (token_data["target"],))
    row = cursor.fetchone()
    if row:
        print(f"[+] Success! Row found: {dict(row)}")
    else:
        print("[-] Failure! Row not found.")
