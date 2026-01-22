import copy
from core.allocation_algo import solve_model

def simulate_optimal_bid(buyers, products, user_qtys, user_prices, new_buyer_name="__SIMULATION__", max_rounds=30):
    """
    Simule le prix minimal à proposer pour atteindre les quantités désirées.
    Utilise la même logique que run_auto_bid_aggressive.
    """
    buyers_copy = copy.deepcopy(buyers)
    recommendations = {}

    min_step = 0.1
    pct_step = 0.05

    # Buyer temporaire
    temp_buyer = {
        "name": new_buyer_name,
        "auto_bid": True,
        "products": {}
    }
    for pid, qty in user_qtys.items():
        temp_buyer["products"][pid] = {
            "qty_desired": qty,
            "current_price": user_prices.get(pid, 0),
            "max_price": 1e6,
            "moq": next(p["seller_moq"] for p in products if p["id"] == pid)
        }
    buyers_copy.append(temp_buyer)

    # Auto-bid sur copie
    for _ in range(max_rounds):
        changes_made = False
        buyers_sorted = sorted(
            buyers_copy,
            key=lambda b: max(p["max_price"] for p in b["products"].values()),
            reverse=True
        )

        for buyer in buyers_sorted:
            if not buyer.get("auto_bid", False):
                continue
            for pid, prod_conf in buyer["products"].items():
                current_price = prod_conf["current_price"]
                max_price = prod_conf["max_price"]
                qty_desired = prod_conf["qty_desired"]

                allocations, _ = solve_model(buyers_copy, products)
                current_alloc = allocations[buyer["name"]].get(pid, 0)
                if current_alloc >= qty_desired:
                    continue

                test_price = current_price
                while test_price < max_price:
                    step = max(min_step, test_price * pct_step)
                    next_price = min(test_price + step, max_price)
                    prod_conf["current_price"] = next_price

                    new_allocs, _ = solve_model(buyers_copy, products)
                    new_alloc = new_allocs[buyer["name"]].get(pid, 0)

                    if new_alloc >= qty_desired:
                        test_price = next_price
                        changes_made = True
                        break
                    test_price = next_price
                    changes_made = True

                prod_conf["current_price"] = round(test_price, 2)

        if not changes_made:
            break

    # Retourne les recommandations
    for pid in user_qtys:
        recommendations[pid] = {
            "recommended_price": temp_buyer["products"][pid]["current_price"],
            "recommended_qty": temp_buyer["products"][pid]["qty_desired"]
        }

    return recommendations
