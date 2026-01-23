import streamlit as st
import pandas as pd
from services.state_manager import load_json

def seller_app():
    st.title("📦 Interface Vendeur")

    products = load_json("products.json")
    history = load_json("bids_history.json")

    if not history:
        st.info("Aucune enchère dans l'historique")
        return


    # -----------------------------
    # Calculer le CA global avant affichage
    # -----------------------------
    total_ca_all_products = 0
    for pid, p in products.items():
        product_history = [h for h in history if h["product"] == pid]
        if product_history:
            latest_time = max(h["timestamp"] for h in product_history)
            last_allocations = [
                h for h in product_history if h["timestamp"] == latest_time and h["qty_allocated"] > 0
            ]
            for h in last_allocations:
                total_ca_all_products += h["final_price"] * h["qty_allocated"]

    # -----------------------------
    # Afficher le CA global en haut
    # -----------------------------
    st.markdown(f"## 💵 Chiffre d'affaires total : {total_ca_all_products:.2f} €")
    st.markdown("---")  # séparateur visuel

    # -----------------------------
    # Affichage du chiffre d'affaires global
    # -----------------------------
    with st.expander("📈 Évolution du chiffre d'affaires global  (cliquer pour afficher)"):
        df = pd.DataFrame(history)
    
        # Calcul du chiffre d'affaires par ligne
        df["ca"] = df["final_price"] * df["qty_allocated"]
    
        # Grouper par timestamp pour obtenir le CA global par round
        df_ca_global = df.groupby("timestamp")["ca"].sum().reset_index()
        df_ca_global = df_ca_global.sort_values("timestamp")
    
        # Raccourcir la date pour lisibilité
        df_ca_global["short_date"] = pd.to_datetime(df_ca_global["timestamp"]).dt.strftime("%d/%m %H:%M")
    
        # Afficher le tableau
        #st.subheader("📈 Évolution du chiffre d'affaires global (tous produits)")
        st.dataframe(df_ca_global)
    
        # Option : afficher un graphique
        st.line_chart(df_ca_global.set_index("short_date")["ca"])

   # -----------------------------
    # Enchères en cours : tous produits
    # -----------------------------
    st.subheader("**📊 Enchères en cours (tous produits)**")
    rows = []
    for pid, p in products.items():
        product_history = [h for h in history if h["product"] == pid]
        if product_history:
            latest_time = max(h["timestamp"] for h in product_history)
            last_allocations = [
                h for h in product_history if h["timestamp"] == latest_time and h["qty_allocated"] > 0
            ]
            for h in last_allocations:
                rows.append({
                    "Produit": p["name"],
                    "Acheteur": h["buyer"],
                    "Qté allouée": h["qty_allocated"],
                    "Prix final (€)": h["final_price"],
                    "Qté demandée": h["qty_desired"],
                    "Prix max (€)": h["max_price"],
                    "Chiffre d'affaires (€)": h["final_price"] * h["qty_allocated"],
                    "Date": h["timestamp"]
                })
    if rows:
        st.dataframe(pd.DataFrame(rows))
    else:
        st.info("Aucun acheteur avec allocation pour le moment")

    # -----------------------------
    # Historique complet : tous produits
    # -----------------------------
    with st.expander("📜 Historique complet des enchères (tous produits)"):
        hist_rows = []
        for pid, p in products.items():
            product_history = [h for h in history if h["product"] == pid]
            for h in product_history:
                hist_rows.append({
                    "Produit": p["name"],
                    "Acheteur": h["buyer"],
                    "Qté demandée": h["qty_desired"],
                    "Qté allouée": h["qty_allocated"],
                    "Prix final (€)": h["final_price"],
                    "Prix max (€)": h["max_price"],
                    "Date": h["timestamp"],
                    "Chiffre d'affaires (€)": h["final_price"] * h["qty_allocated"]
                })
        if hist_rows:
            st.dataframe(pd.DataFrame(hist_rows))
        else:
            st.info("Aucun historique d'enchères")
