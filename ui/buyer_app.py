import streamlit as st
from services.state_manager import load_json
from services.bid_service import place_bid

def buyer_app():
    st.title("🛒 Interface Acheteur")

    products = load_json("products.json")
    buyer_id = st.text_input("Votre identifiant acheteur", "buyer_A")

    for pid, p in products.items():
        st.subheader(p["name"])
        st.metric("Prix de départ", f"{p['starting_price']} €")

        qty = st.number_input("Quantité désirée", min_value=p["seller_moq"], step=p["volume_multiple"])
        max_price = st.number_input("Prix max", min_value=p["starting_price"], step=0.5)

        if st.button(f"Placer enchère – {pid}"):
            place_bid(buyer_id, pid, qty, max_price)
            st.success("Enchère enregistrée")
