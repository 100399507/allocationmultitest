import copy
from core.allocation_algo import solve_model

def run_auto_bid_aggressive(buyers, products, max_rounds=30):
    """
    Incrémente les prix automatiquement pour atteindre les quantités désirées
    tout en respectant les max_price des acheteurs.
    """
    current_buyers = copy.deepcopy(buyers)
    min_step = 0.1
    pct_step = 0.05

    for _ in range(max_rounds):
        changes_made = False

        buyers_sorted = sorted(
            current_buyers,
            key=lambda b: max(p["max_price"] for p in b["products"].values()),
            reverse=True
        )

        for buyer in buyers_sorted:
            if not buyer.get("auto_bid", False):
                continue

            buyer_name = buyer["name"]

            for prod_id, prod_conf in buyer["products"].items():
                current_price = prod_conf["current_price"]
                max_price = prod_conf["max_price"]
                qty_desired = prod_conf["qty_desired"]

                allocations, _ = solve_model(current_buyers, products)
                current_alloc = allocations[buyer_name][prod_id]

                if current_alloc >= qty_desired:
                    continue

                # Test max possible
                prod_conf["current_price"] = max_price
                max_allocs, _ = solve_model(current_buyers, products)
                target_alloc = min(max_allocs[buyer_name][prod_id], qty_desired)
                if target_alloc <= current_alloc:
                    prod_conf["current_price"] = current_price
                    continue

                # Incrément progressif
                test_price = current_price
                while test_price < max_price:
                    step = max(min_step, test_price * pct_step)
                    next_price = min(test_price + step, max_price)
                    prod_conf["current_price"] = next_price

                    new_allocs, _ = solve_model(current_buyers, products)
                    new_alloc = new_allocs[buyer_name][prod_id]

                    if new_alloc >= target_alloc:
                        test_price = next_price
                        changes_made = True
                        break
                    test_price = next_price
                    changes_made = True

                prod_conf["current_price"] = round(test_price, 2)

        if not changes_made:
            break

    # Résolution finale
    solve_model(current_buyers, products)
    return current_buyers
