import json
from pathlib import Path

# -----------------------------
# Chemin vers le dossier data
# -----------------------------
DATA_PATH = Path("data")
DATA_PATH.mkdir(exist_ok=True)  # Crée le dossier s'il n'existe pas

# -----------------------------
# Fonctions génériques
# -----------------------------
def load_json(filename):
    filepath = DATA_PATH / filename
    if not filepath.exists():
        return []  # retourne liste vide si le fichier n'existe pas
    with open(filepath, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(DATA_PATH / filename, "w") as f:
        json.dump(data, f, indent=2)

# -----------------------------
# Fonctions spécifiques
# -----------------------------
def load_products():
    """Retourne la liste des produits"""
    return load_json("products.json")

def save_products(products):
    """Sauvegarde la liste des produits"""
    save_json("products.json", products)

def load_buyers():
    """Retourne la liste des acheteurs"""
    return load_json("buyers.json")

def save_buyers(buyers):
    """Sauvegarde la liste des acheteurs"""
    save_json("buyers.json", buyers)

def load_bids_history():
    """Retourne l'historique des enchères"""
    return load_json("bids_history.json")

def save_bids_history(history):
    """Sauvegarde l'historique des enchères"""
    save_json("bids_history.json", history)
