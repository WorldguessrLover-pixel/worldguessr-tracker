import os
import psycopg2
import requests

# --- Variables d'environnement ---
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_URL = "https://api.worldguessr.com/api/leaderboard"

# --- Connexion PostgreSQL ---
def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            username TEXT PRIMARY KEY,
            elo INTEGER
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# --- Envoi Telegram ---
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Erreur envoi Telegram:", e)

# --- Récupération API ---
def fetch_data():
    try:
        resp = requests.get(API_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("Erreur API:", e)
        return None

# --- Comparaison et update ---
def compare_and_update(data):
    conn = get_connection()
    cur = conn.cursor()

    for idx, player in enumerate(data["leaderboard"]):
        name = player["username"]
        elo = player["elo"]
        position = idx + 1  # 1er joueur = position 1, etc.

        # Vérifie si le joueur est déjà en base
        cur.execute("SELECT elo FROM players WHERE username=%s", (name,))
        row = cur.fetchone()

        if row:
            old_elo = row[0]
            if elo != old_elo:
                # Différentes notifs selon le seuil
                if elo >= 10000:
                    message = f"⚡ #{position} {name} a changé d’ELO : {old_elo} ➝ {elo}"
                elif elo >= 8000:
                    message = f"🔔 #{position} {name} a changé d’ELO : {old_elo} ➝ {elo}"
                else:
                    continue

                # Ajoute distinction si 1er ou 2ème
                if position == 1:
                    message = "👑 " + message  # Premier mondial
                elif position == 2:
                    message = "🥈 " + message  # Deuxième mondial

                send_telegram(message)
                cur.execute("UPDATE players SET elo=%s WHERE username=%s", (elo, name))

        else:
            # Nouveau joueur au-dessus de 8000
            if elo >= 8000:
                message = f"🆕 Nouveau joueur #{position} : {name} ➝ {elo} ELO"
                if position == 1:
                    message = "👑 " + message
                elif position == 2:
                    message = "🥈 " + message
                send_telegram(message)
            cur.execute("INSERT INTO players (username, elo) VALUES (%s, %s)", (name, elo))

    conn.commit()
    cur.close()
    conn.close()

# --- Main ---
def main():
    init_db()
    data = fetch_data()
    if data:
        compare_and_update(data)

if __name__ == "__main__":
    main()
