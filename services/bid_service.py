from datetime import datetime
from services.state_manager import load_json, save_json

def save_final_allocations(buyers, allocations):
    history = load_json("bids_history.json")
    now = datetime.utcnow().isoformat()

    for buyer in buyers:
        buyer_name = buyer["name"]
        buyer_alloc = allocations.get(buyer_name, {})

        for pid, prod in buyer["products"].items():
            history.append({
                "buyer": buyer_name,
                "product": pid,
                "qty_desired": prod["qty_desired"],
                "qty_allocated": buyer_alloc.get(pid, 0),
                "final_price": prod["current_price"],
                "max_price": prod["max_price"],
                "timestamp": now
            })

    save_json("bids_history.json", history)


#### Vider l'historique des enchères 
from services.state_manager import save_json

def reset_bid_history():
    """
    Vide complètement le fichier bid_history.json
    """
    save_json("bids_history.json", [])
