# core/allocation_algo.py
import pulp
import copy

# -----------------------------
# Fonctions principales
# -----------------------------
def round_to_multiple(value, multiple):
    if multiple <= 0:
        return int(value)
    return int(round(value / multiple) * multiple)

def solve_model(buyers, products, seller_global_moq=80):
    """Résout le modèle multi-produits avec MOQ Global"""
    if not buyers:
        return {}, 0.0

    model = pulp.LpProblem("Sequential_Auction", pulp.LpMaximize)

    x = {}
    y = {}
    z = {}
    n_mult = {}

    # Variables
    for buyer in buyers:
        buyer_name = buyer["name"]
        z[buyer_name] = pulp.LpVariable(f"z_{buyer_name}", lowBound=0, upBound=1, cat="Binary")

        for product in products:
            prod_id = product["id"]
            x[(buyer_name, prod_id)] = pulp.LpVariable(f"x_{buyer_name}_{prod_id}", lowBound=0)
            y[(buyer_name, prod_id)] = pulp.LpVariable(f"y_{buyer_name}_{prod_id}", lowBound=0, upBound=1, cat="Binary")
            n_mult[(buyer_name, prod_id)] = pulp.LpVariable(f"n_{buyer_name}_{prod_id}", lowBound=0, cat="Integer")

    # Fonction objectif
    revenue_terms = []
    for buyer in buyers:
        for prod_id in buyer["products"]:
            buyer_name = buyer["name"]
            price = buyer["products"][prod_id]["current_price"]
            revenue_terms.append(price * x[(buyer_name, prod_id)])
    model += pulp.lpSum(revenue_terms)

    # Contraintes par produit
    for product in products:
        prod_id = product["id"]
        volume_multiple = product["volume_multiple"]
        stock_terms = [x[(b["name"], prod_id)] for b in buyers]
        if stock_terms:
            model += pulp.lpSum(stock_terms) <= product["stock"]
        for buyer in buyers:
            model += x[(buyer["name"], prod_id)] == volume_multiple * n_mult[(buyer["name"], prod_id)]

    # Contraintes par acheteur
    for buyer in buyers:
        buyer_name = buyer["name"]
        total_alloc_terms = [x[(buyer_name, prod_id)] for prod_id in buyer["products"]]
        model += pulp.lpSum(total_alloc_terms) >= seller_global_moq * z[buyer_name]

        for prod_id, prod_conf in buyer["products"].items():
            big_m = 10000
            model += x[(buyer_name, prod_id)] <= big_m * z[buyer_name]
            model += x[(buyer_name, prod_id)] >= prod_conf["moq"] * y[(buyer_name, prod_id)]
            model += x[(buyer_name, prod_id)] <= prod_conf["qty_desired"] * y[(buyer_name, prod_id)]
            model += y[(buyer_name, prod_id)] <= z[buyer_name]

    # Résolution
    model.solve(pulp.PULP_CBC_CMD(msg=False))

    allocations = {}
    total_ca = 0.0

    for buyer in buyers:
        allocations[buyer["name"]] = {}
        buyer_total = 0

        for prod_id in buyer["products"]:
            alloc_value = x[(buyer["name"], prod_id)].value() or 0
            volume_multiple = next(p["volume_multiple"] for p in products if p["id"] == prod_id)
            alloc_value = round_to_multiple(alloc_value, volume_multiple)
            buyer_total += alloc_value

        if buyer_total < seller_global_moq:
            for prod_id in buyer["products"]:
                allocations[buyer["name"]][prod_id] = 0
        else:
            for prod_id in buyer["products"]:
                alloc_value = x[(buyer["name"], prod_id)].value() or 0
                volume_multiple = next(p["volume_multiple"] for p in products if p["id"] == prod_id)
                alloc_value = round_to_multiple(alloc_value, volume_multiple)
                allocations[buyer["name"]][prod_id] = alloc_value
                total_ca += alloc_value * buyer["products"][prod_id]["current_price"]

    return allocations, total_ca

# -----------------------------
# Auto-bid agressif
# -----------------------------
def run_auto_bid_aggressive(buyers, products, max_rounds=30):
    """
    Applique l'auto-bid sur tous les acheteurs.
    Incrémente les prix progressivement jusqu'à atteindre la quantité désirée.
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

            for prod_id, prod_conf in buyer["products"].items():
                current_price = prod_conf["current_price"]
                max_price = prod_conf["max_price"]
                qty_desired = prod_conf["qty_desired"]

                allocations, _ = solve_model(current_buyers, products)
                current_alloc = allocations[buyer["name"]][prod_id]

                if current_alloc >= qty_desired:
                    continue

                # Test prix max
                prod_conf["current_price"] = max_price
                max_allocs, _ = solve_model(current_buyers, products)
                target_alloc = min(max_allocs[buyer["name"]][prod_id], qty_desired)

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
                    new_alloc = new_allocs[buyer["name"]][prod_id]

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
