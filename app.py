import streamlit as st
from ui.buyer_app import buyer_app
from ui.seller_app import seller_app
from ui.admin_app import admin_app

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choisir l’interface",
    ["Acheteur", "Vendeur", "Admin"]
)

if page == "Acheteur":
    buyer_app()
elif page == "Vendeur":
    seller_app()
else:
    admin_app()
