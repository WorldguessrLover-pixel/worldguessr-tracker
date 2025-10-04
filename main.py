import os
import requests
import psycopg2

API_URL = "https://api.worldguessr.com/api/leaderboard"

# Variables d'environnement
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Connexion PostgreSQL ---
def get_db_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            username TEXT PRIMARY KEY,
            elo INTEGER NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# --- Telegram ---
def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Erreur envoi Telegram:", e)

# --- API ---
def fetch_leaderboard():
    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json()
        # ✅ On récupère bien la liste de joueurs sous la clé "leaderboard"
        return data.get("leaderboard", [])
    else:
        print("Erreur API:", response.status_code)
        return []

# --- Comparaison ---
def compare_and_update(players):
    conn = get_db_conn()
    cur = conn.cursor()

    for player in players:
        name = player.get("username")
        elo = player.get("elo")

        if elo is None:
            continue

        if elo >= 8000:
            cur.execute("SELECT elo FROM players WHERE username = %s", (name,))
            result = cur.fetchone()

            if result:
                old_elo = result[0]
                if elo != old_elo:
                    if elo >= 10000:
                        send_telegram_message(f"⚡ ALERT: {name} est passé de {old_elo} → {elo} (10000+)")
                    else:
                        send_telegram_message(f"🔔 {name} est passé de {old_elo} → {elo}")
                    cur.execute("UPDATE players SET elo = %s WHERE username = %s", (elo, name))
            else:
                cur.execute("INSERT INTO players (username, elo) VALUES (%s, %s)", (name, elo))
                if elo >= 10000:
                    send_telegram_message(f"🔥 Nouveau joueur {name} avec {elo} ELO (10000+)")
                else:
                    send_telegram_message(f"🆕 Nouveau joueur {name} avec {elo} ELO")

    conn.commit()
    cur.close()
    conn.close()

def main():
    init_db()
    players = fetch_leaderboard()
    if players:
        compare_and_update(players)
    else:
        print("⚠️ Aucun joueur récupéré depuis l'API.")

if __name__ == "__main__":
    main()
