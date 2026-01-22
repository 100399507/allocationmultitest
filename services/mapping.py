def json_to_buyers(products):
    buyers = {}

    for pid, product in products.items():
        for buyer_id, bid in product["bids"].items():
            buyers.setdefault(buyer_id, {
                "name": buyer_id,
                "auto_bid": bid["auto_bid"],
                "products": {}
            })

            buyers[buyer_id]["products"][pid] = {
                "qty_desired": bid["qty_desired"],
                "current_price": bid["current_price"],
                "max_price": bid["max_price"],
                "moq": product["seller_moq"]
            }

    return list(buyers.values())
