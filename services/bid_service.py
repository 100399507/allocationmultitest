from datetime import datetime
from services.state_manager import load_json, save_json

def place_bid(buyer_id, product_id, qty, max_price, auto_bid=True):
    products = load_json("products.json")
    history = load_json("bids_history.json")

    product = products[product_id]

    current_price = max(
        product["starting_price"],
        product["bids"].get(buyer_id, {}).get("current_price", product["starting_price"])
    )

    product["bids"][buyer_id] = {
        "qty_desired": qty,
        "current_price": current_price,
        "max_price": max_price,
        "auto_bid": auto_bid,
        "last_update": datetime.utcnow().isoformat()
    }

    history.append({
        "buyer": buyer_id,
        "product": product_id,
        "price": current_price,
        "max_price": max_price,
        "timestamp": datetime.utcnow().isoformat()
    })

    save_json("products.json", products)
    save_json("bids_history.json", history)
