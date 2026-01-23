import streamlit as st
import pandas as pd
from services.state_manager import load_json

def seller_app():
    st.title("📦 Interface Vendeur")

    products = load_json("products.json")
    history = load_json("bids_history.json")

    # -----------------------------
    # Transformer en DataFrame
    # -----------------------------
    df = pd.DataFrame(history)

    # Calcul du chiffre d'affaires par ligne
    df["ca"] = df["final_price"] * df["qty_allocated"]

    # Grouper par timestamp pour obtenir le CA global par round
    df_ca_global = df.groupby("timestamp")["ca"].sum().reset_index()
    df_ca_global = df_ca_global.sort_values("timestamp")

    # Afficher le tableau
    st.subheader("📈 Évolution du chiffre d'affaires global (tous produits)")
    st.dataframe(df_ca_global)

    # Option : afficher un graphique
    st.line_chart(df_ca_global.set_index("timestamp")["ca"])

    
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
    # Affichage détaillé produit par produit
    # -----------------------------
    for pid, p in products.items():
        st.subheader(p["name"])

        # Enchères en cours : derniers allocataires
        st.markdown("**📊 Enchères en cours (acheteurs avec allocation)**")
        product_history = [h for h in history if h["product"] == pid]

        if product_history:
            latest_time = max(h["timestamp"] for h in product_history)
            last_allocations = [
                h for h in product_history if h["timestamp"] == latest_time and h["qty_allocated"] > 0
            ]

            if last_allocations:
                rows = []
                total_ca_product = 0
                for h in last_allocations:
                    ca = h["final_price"] * h["qty_allocated"]
                    total_ca_product += ca
                    rows.append({
                        "Acheteur": h["buyer"],
                        "Qté allouée": h["qty_allocated"],
                        "Prix final (€)": h["final_price"],
                        "Qté demandée": h["qty_desired"],
                        "Prix max (€)": h["max_price"],
                        "Chiffre d'affaires (€)": ca,
                        "Date": h["timestamp"]
                    })

                st.dataframe(pd.DataFrame(rows))
                st.markdown(f"**💰 Chiffre d'affaires total pour ce produit : {total_ca_product:.2f} €**")
            else:
                st.info("Aucun acheteur avec allocation pour ce produit")
        else:
            st.info("Aucune allocation pour ce produit")

        # Historique détaillé dans un expander
        with st.expander("📜 Historique des enchères (cliquer pour afficher)"):
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
