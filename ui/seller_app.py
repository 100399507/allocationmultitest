import streamlit as st
import pandas as pd
from services.state_manager import load_json

def seller_app():
    st.title("📦 Interface Vendeur")

    products = load_json("products.json")

    for pid, p in products.items():
        st.subheader(p["name"])

        rows = []
        for buyer, bid in p["bids"].items():
            rows.append({
                "Acheteur": buyer,
                "Quantité": bid["qty_desired"],
                "Prix courant": bid["current_price"],
                "Prix max": bid["max_price"],
                "Auto-bid": bid["auto_bid"]
            })

        if rows:
            st.dataframe(pd.DataFrame(rows))
        else:
            st.info("Aucune enchère")
