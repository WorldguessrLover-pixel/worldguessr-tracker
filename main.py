import os
import requests
import psycopg2
import threading
from flask import Flask, jsonify

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def get_data():
    try:
        resp = requests.get("https://api.worldguessr.com/api/leaderboard", timeout=8)
        resp.raise_for_status()
        return resp.json().get("leaderboard", [])
    except Exception as e:
        print("❌ Erreur get_data:", e)
        return []


def compare_and_update():
    print("🟢 Début du check Elo")
    data = get_data()
    if not data:
        print("⚠️ Aucune donnée récupérée.")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            username TEXT PRIMARY KEY,
            elo INTEGER
        )
    """)
    conn.commit()

    for player in data:
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
                    msg += " ⚡"
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
                )
                print("📨", msg)
        else:
            cur.execute("INSERT INTO players (username, elo) VALUES (%s, %s)", (name, elo))
            conn.commit()
            msg = f"🆕 Nouveau joueur au-dessus de 8000 ELO : {name} ({elo})"
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
            )
            print("📨", msg)

    cur.close()
    conn.close()
    print("✅ Check terminé.")


@app.route("/", methods=["GET", "HEAD"])
def home():
    return "✅ WorldGuessr Tracker is running!", 200


@app.route("/check", methods=["GET", "HEAD"])
def check():
    if os.getenv("DEBUG"):  # Pour éviter double check en dev
        print("🔎 Requête reçue sur /check")

    # Si c’est un HEAD (cas d’UptimeRobot gratuit)
    # on répond tout de suite sans exécuter le code
    if "HEAD" in str(requests.Request).upper():
        return "", 200

    # Sinon on lance le check en parallèle
    threading.Thread(target=compare_and_update, daemon=True).start()
    return jsonify({"status": "started"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"🚀 Démarrage sur le port {port}")
    app.run(host="0.0.0.0", port=port)
