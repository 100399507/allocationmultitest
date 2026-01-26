import streamlit as st
import pandas as pd
from services.state_manager import load_json

def seller_app():
    st.title("Dashboard Vendeur")

    products = load_json("products.json")
    history = load_json("bids_history.json")
    lots = load_json("lots.json")

    # -----------------------------
    # Saisir buyer_name
    # -----------------------------
    buyer_name = st.text_input("Votre identifiant vendeur/acheteur (confidentiel)")
    if not buyer_name:
        st.info("Veuillez saisir votre identifiant pour accéder à votre espace.")
        return

    # -----------------------------
    # Identifier les lots où ce buyer a des enchères
    # -----------------------------
    buyer_lots = {h["lot_id"] for h in history if h["buyer"] == buyer_name}
    if not buyer_lots:
        st.info("Vous n'avez aucune enchère enregistrée pour le moment.")
        return

    # Sélection du lot
    lot_id = st.selectbox(
        "📦 Sélectionnez un lot",
        options=list(buyer_lots),
        format_func=lambda k: lots[k]["lot_name"]
    )

    # Produits du lot sélectionné
    lot_products = {pid: p for pid, p in products.items() if p["lot_id"] == lot_id}

    # -----------------------------
    # Cadre récapitulatif des produits
    # -----------------------------
    with st.expander("📝 Informations sur les produits (cliquer pour afficher)"):
        product_summary = []
        for pid, p in lot_products.items():
            product_summary.append({
                "Produit": p["name"],
                "Stock total": p["stock"],
                "MOQ": p["seller_moq"],
                "Volume multiple": p["volume_multiple"],
                "Prix de départ (€)": round(p["starting_price"])
            })
        st.table(pd.DataFrame(product_summary))

    # -----------------------------
    # Chiffre d'affaires total pour ce lot
    # -----------------------------
    total_ca = 0
    for pid, p in lot_products.items():
        product_history = [h for h in history if h["product"] == pid]
        if product_history:
            latest_time = max(h["timestamp"] for h in product_history)
            last_allocations = [h for h in product_history if h["timestamp"] == latest_time and h["qty_allocated"] > 0]
            for h in last_allocations:
                total_ca += h["final_price"] * h["qty_allocated"]

    st.markdown(f"## 💵 Chiffre d'affaires total pour ce lot : {total_ca:.2f} €")
    st.markdown("---")

    # -----------------------------
    # Évolution du chiffre d'affaires
    # -----------------------------
    with st.expander("📈 Évolution du chiffre d'affaires (lot sélectionné)"):
        df = pd.DataFrame([h for h in history if h["lot_id"] == lot_id])
        if not df.empty:
            df["ca"] = df["final_price"] * df["qty_allocated"]
            df_ca_global = df.groupby("timestamp")["ca"].sum().reset_index()
            df_ca_global = df_ca_global.sort_values("timestamp")
            df_ca_global["short_date"] = pd.to_datetime(df_ca_global["timestamp"]).dt.strftime("%d/%m %H:%M")
            st.dataframe(df_ca_global)
            st.line_chart(df_ca_global.set_index("short_date")["ca"])
        else:
            st.info("Aucune enchère pour ce lot pour le moment.")

    # -----------------------------
    # Enchères en cours pour le lot
    # -----------------------------
    st.subheader("**📊 Enchères en cours (lot sélectionné)**")
    rows = []
    for pid, p in lot_products.items():
        product_history = [h for h in history if h["product"] == pid]
        if product_history:
            latest_time = max(h["timestamp"] for h in product_history)
            last_allocations = [h for h in product_history if h["timestamp"] == latest_time and h["qty_allocated"] > 0]
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
        st.info("Aucune enchère allouée pour ce lot pour le moment.")

    # -----------------------------
    # Historique complet pour le lot
    # -----------------------------
    with st.expander("📜 Historique complet des enchères (lot sélectionné)"):
        hist_rows = []
        for pid, p in lot_products.items():
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
            st.info("Aucun historique d'enchères pour ce lot.")
