import requests
import json
import os

API_URL = "https://api.worldguessr.com/api/leaderboard"
STORAGE_FILE = "storage.json"

# Charger l'ancien état
def load_old_data():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return {}

# Sauvegarder le nouvel état
def save_new_data(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Récupérer les données actuelles
def fetch_leaderboard():
    response = requests.get(API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        print("Erreur API:", response.status_code)
        return None

# Comparer
def compare_and_notify(old, new):
    if not old:
        print("Pas de données anciennes, initialisation…")
        return
    
    for player in new:
        name = player["username"]
        elo = player["elo"]

        if elo >= 8000:
            old_elo = old.get(name, 0)
            if elo != old_elo:
                if elo >= 10000:
                    print(f"⚡ ALERT: {name} a changé d'ELO ({old_elo} → {elo}) et dépasse 10000 !")
                else:
                    print(f"🔔 {name} a changé d'ELO ({old_elo} → {elo})")

def main():
    old_data = load_old_data()
    new_data = fetch_leaderboard()

    if new_data:
        # Transformer en dict {username: elo}
        new_dict = {player["username"]: player["elo"] for player in new_data}
        
        compare_and_notify(old_data, new_dict)
        save_new_data(new_dict)

if __name__ == "__main__":
    main()
