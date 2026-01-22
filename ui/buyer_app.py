import streamlit as st
import copy
from services.state_manager import load_json
from services.bid_service import place_bid
from core.allocation_algo import run_auto_bid_aggressive, solve_model

def buyer_app():
    st.title("🛒 Interface Acheteur")

    # Session state
    if "buyers" not in st.session_state:
        st.session_state.buyers = []

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
            "current_price": p["starting_price"],  # valeur initiale
            "max_price": max_price,
            "moq": p["seller_moq"],               # nécessaire pour solve_model
            "volume_multiple": p["volume_multiple"],
            "stock": p["stock"]
        }

    # -----------------------------
    # Bouton unique pour tous les produits
    # -----------------------------
    if st.button("💰 Placer l’enchère pour tous les produits"):
        # Ajouter le buyer courant s'il n'existe pas encore
        if not any(b["name"] == buyer_id for b in st.session_state.buyers):
            st.session_state.buyers.append({
                "name": buyer_id,
                "products": copy.deepcopy(draft_products),
                "auto_bid": True
            })
        else:
            # Mettre à jour les valeurs si déjà présent
            for b in st.session_state.buyers:
                if b["name"] == buyer_id:
                    b["products"] = copy.deepcopy(draft_products)
                    b["auto_bid"] = True

        # Placer les enchères (optionnel si tu as une fonction place_bid par produit)
        for pid, prod in draft_products.items():
            place_bid(buyer_id, pid, prod["qty_desired"], prod["max_price"])

        # Lancer l'auto-bid pour tous les buyers
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, list(products.values()))

        st.success("Enchères placées et auto-bid lancé pour tous les produits")

        # Affichage des résultats après auto-bid
        result_rows = []
        buyer_index = next(i for i, b in enumerate(st.session_state.buyers) if b["name"] == buyer_id)
        buyer_final = st.session_state.buyers[buyer_index]

        for pid, prod in draft_products.items():
            current_price = buyer_final["products"][pid]["current_price"]
            result_rows.append({
                "Produit": pid,
                "Qté désirée": prod["qty_desired"],
                "Qté allouée": qty_allocated, 
                "Prix courant (€)": current_price,
                "Prix max (€)": prod["max_price"]
            })

        st.subheader("Résultat enchères après Auto-bid")
        st.dataframe(result_rows)
