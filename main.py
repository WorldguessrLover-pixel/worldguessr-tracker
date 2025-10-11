import os
import requests
import psycopg2
from flask import Flask

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_data():
    resp = requests.get("https://api.worldguessr.com/api/leaderboard")
    resp.raise_for_status()
    return resp.json().get("leaderboard", [])

def compare_and_update(new_data):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            username TEXT PRIMARY KEY,
            elo INTEGER
        )
    """)
    conn.commit()

    for player in new_data:
        name = player["username"]
        elo = player["elo"]

        if elo < 8000:
            continue

        cur.execute("SELECT elo FROM players WHERE username = %s", (name,))
        result = cur.fetchone()

        if result:
            old_elo = result[0]
            if old_elo != elo:
                cur.execute("UPDATE players SET elo = %s WHERE username = %s", (elo, name))
                conn.commit()
                msg = f"🔔 {name} a changé d’ELO : {old_elo} → {elo}"
                if elo >= 10000:
                    msg = f"⚡ {name} dépasse les 10 000 ELO ! ({old_elo} → {elo})"
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                              json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        else:
            cur.execute("INSERT INTO players (username, elo) VALUES (%s, %s)", (name, elo))
            conn.commit()
            if elo >= 8000:
                msg = f"🆕 Nouveau joueur au-dessus de 8000 ELO : {name} ({elo})"
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                              json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

    cur.close()
    conn.close()


@app.route("/")
def home():
    return "✅ WorldGuessr Tracker is running!", 200


@app.route("/check")
def check():
    compare_and_update(get_data())
    return "✅ Check completed", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
