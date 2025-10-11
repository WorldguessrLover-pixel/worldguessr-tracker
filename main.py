import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask

app = Flask(__name__)

DB_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = "https://api.worldguessr.com/api/leaderboard"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Erreur Telegram:", e)

def get_db_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def setup_database():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            username TEXT PRIMARY KEY,
            elo INTEGER,
            rank INTEGER
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def fetch_leaderboard():
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        return data.get("leaderboard", [])
    except Exception as e:
        print("Erreur API:", e)
        return []

def compare_and_update(new_data):
    conn = get_db_connection()
    cur = conn.cursor()

    for rank, player in enumerate(new_data, start=1):
        name = player["username"]
        elo = player["elo"]

        if elo < 8000:
            continue  # on ignore les joueurs < 8000 elo

        cur.execute("SELECT elo FROM players WHERE username = %s", (name,))
        result = cur.fetchone()

        if result:
            old_elo = result["elo"]
            if old_elo != elo:
                # 🔥 Message de changement ELO (unifié, plus de "dépasse 10000")
                msg = f"⚡ #{rank} {name} a changé d’ELO : {old_elo} → {elo}"
                send_telegram_message(msg)
                cur.execute("UPDATE players SET elo = %s, rank = %s WHERE username = %s", (elo, rank, name))
        else:
            # Nouveau joueur haut elo
            cur.execute("INSERT INTO players (username, elo, rank) VALUES (%s, %s, %s)", (name, elo, rank))

    conn.commit()
    cur.close()
    conn.close()

@app.route("/")
def home():
    new_data = fetch_leaderboard()
    if new_data:
        compare_and_update(new_data)
        return "Leaderboard checked successfully ✅", 200
    else:
        return "Erreur lors de la récupération du leaderboard ❌", 500

if __name__ == "__main__":
    setup_database()
    app.run(host="0.0.0.0", port=10000)
