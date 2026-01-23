import streamlit as st
import pandas as pd
from services.state_manager import load_json, save_json

def admin_app():
    st.title("🛠️ Interface Admin")

    from services.bid_service import reset_bid_history

    # Bouton pour réinitialiser l'historique
    if st.button("⚠️ Réinitialiser l'historique des enchères"):
        reset_bid_history()
        st.success("Le fichier bid_history.json a été remis à zéro ✅")

    products = load_json("products.json")
    buyers = load_json("buyers.json")

    st.subheader("👥 Acheteurs")
    st.json(buyers)

    st.subheader("📦 Produits & Enchères")
    st.json(products)

    if st.button("🧹 Reset toutes les enchères"):
        for p in products.values():
            p["bids"] = {}
        save_json("products.json", products)
        st.success("Toutes les enchères ont été supprimées")
