import streamlit as st
from services.state_manager import load_json
from services.bid_service import place_bid
from core.allocation_algo import run_auto_bid_aggressive

# Session state
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

def buyer_app():
    st.title("🛒 Interface Acheteur")

    # Charger les produits
    products = load_json("products.json")
    buyer_id = st.text_input("Votre identifiant acheteur", "buyer_A")

    # -----------------------------
    # Créer un "draft" temporaire des entrées de l'acheteur
    # -----------------------------
    draft_products = {}
    for pid, p in products.items():
        st.subheader(p["name"])
        st.metric("Prix de départ", f"{p['starting_price']} €")

        qty = st.number_input(
            "Quantité désirée",
            min_value=p["seller_moq"],
            step=p["volume_multiple"],
            key=f"qty_{pid}"
        )
        max_price = st.number_input(
            "Prix max",
            min_value=p["starting_price"],
            step=0.5,
            key=f"max_{pid}"
        )

        draft_products[pid] = {
        "qty_desired": qty,
        "current_price": p["starting_price"],  # valeur de départ
        "max_price": max_price,
        "moq": p["seller_moq"]  # nécessaire pour solve_model

        }


    # -----------------------------
    # Bouton unique pour tous les produits
    # -----------------------------
    if st.button("💰 Placer l’enchère pour tous les produits"):
        # Placer l'enchère pour chaque produit
        for pid, prod in draft_products.items():
            place_bid(buyer_id, pid, prod["qty_desired"], prod["max_price"])

        # Lancer l'auto-bid pour tous les produits
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, list(products.values()))


        st.success("Enchères placées pour tous les produits")

        # Ajouter le buyer courant s'il n'existe pas encore
        if not any(b["name"] == buyer_id for b in st.session_state.buyers):
            st.session_state.buyers.append({
                "name": buyer_id,
                "products": copy.deepcopy(draft_products),
                "auto_bid": True
            })


        # Affichage des résultats après auto-bid
        result_rows = []
        for pid, prod in draft_products.items():
            current_price = st.session_state.buyers[-1]["products"][pid]["current_price"]
            result_rows.append({
                "Produit": pid,
                "Qté désirée": prod["qty_desired"],
                "Prix courant (€)": current_price,
                "Prix max (€)": prod["max_price"]
            })

        st.subheader("Résultat enchères après Auto-bid")
        st.dataframe(result_rows)
