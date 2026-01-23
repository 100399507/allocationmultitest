import streamlit as st
import pandas as pd
from services.state_manager import load_json

def seller_app():
    st.title("📦 Interface Vendeur")

    products = load_json("products.json")
    history = load_json("bids_history.json")
    
    #Pour calcul du CA global
    total_ca_all_products = 0

    # -----------------------------
    # Chiffre d'affaires total global
    # -----------------------------
    st.markdown(f"## 💵 Chiffre d'affaires total tous produits : {total_ca_all_products:.2f} €")


    for pid, p in products.items():
        st.subheader(p["name"])

        # -----------------------------
        # Enchères en cours : derniers allocataires
        # -----------------------------
        st.markdown("**📊 Enchères en cours (acheteurs avec allocation)**")

        # Filtrer l'historique pour ce produit
        product_history = [h for h in history if h["product"] == pid]

        if product_history:
            # Trouver la dernière timestamp pour ce produit
            latest_time = max(h["timestamp"] for h in product_history)

            # Sélectionner uniquement les allocations de ce round
            last_allocations = [
                h for h in product_history 
                if h["timestamp"] == latest_time and h["qty_allocated"] > 0
            ]

            if last_allocations:
                rows = []
                total_ca = 0
                for h in last_allocations:
                    ca = h["final_price"] * h["qty_allocated"]
                    total_ca += ca
                    rows.append({
                        "Acheteur": h["buyer"],
                        "Qté allouée": h["qty_allocated"],
                        "Prix final (€)": h["final_price"],
                        "Qté demandée": h["qty_desired"],
                        "Prix max (€)": h["max_price"],
                        "Chiffre d'affaires (€)": ca,
                        "Date": h["timestamp"]
                    })

                total_ca_all_products += total_ca

                st.dataframe(pd.DataFrame(rows))
                
                # Afficher le CA total du produit
                st.markdown(f"**💰 Chiffre d'affaires total pour ce produit : {total_ca:.2f} €**")
            else:
                st.info("Aucun acheteur avec allocation pour ce produit")
        else:
            st.info("Aucune allocation pour ce produit")


        # -----------------------------
        # Historique des résultats finaux
        # -----------------------------
        with st.expander("📜 Historique des enchères (cliquer pour afficher)"):

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
    
    

