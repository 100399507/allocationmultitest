import streamlit as st
import pandas as pd
from services.state_manager import load_json

def seller_app():
    st.title("📦 Interface Vendeur")

    from services.bid_service import reset_bid_history

    # Bouton pour réinitialiser l'historique
    if st.button("⚠️ Réinitialiser l'historique des enchères"):
        reset_bid_history()
        st.success("Le fichier bid_history.json a été remis à zéro ✅")

    products = load_json("products.json")
    history = load_json("bids_history.json")

    for pid, p in products.items():
        st.subheader(p["name"])

        # -----------------------------
        # État courant des enchères
        # -----------------------------
        st.markdown("**📊 Enchères en cours**")

        rows = []
        for buyer, bid in p.get("bids", {}).items():
            rows.append({
                "Acheteur": buyer,
                "Quantité demandée": bid["qty_desired"],
                "Prix courant (€)": bid["current_price"],
                "Prix max (€)": bid["max_price"],
                "Auto-bid": bid["auto_bid"]
            })

        if rows:
            st.dataframe(pd.DataFrame(rows))
        else:
            st.info("Aucune enchère en cours")

        # -----------------------------
        # Historique des résultats finaux
        # -----------------------------
        st.markdown("**📜 Historique des allocations finales**")

        product_history = [
            h for h in history if h["product"] == pid
        ]

        if product_history:
            hist_rows = []
            for h in product_history:
                hist_rows.append({
                    "Acheteur": h["buyer"],
                    "Qté demandée": h["qty_desired"],
                    "Qté allouée": h["qty_allocated"],
                    "Prix final (€)": h["final_price"],
                    "Prix max (€)": h["max_price"],
                    "Date": h["timestamp"]
                })

            st.dataframe(pd.DataFrame(hist_rows))
        else:
            st.info("Aucun historique pour ce produit")



