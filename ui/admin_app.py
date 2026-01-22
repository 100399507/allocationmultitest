import streamlit as st
import pandas as pd
from services.state_manager import load_json, save_json

def admin_app():
    st.title("🛠️ Interface Admin")

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
