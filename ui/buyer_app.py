import streamlit as st
import copy
from core.auto_bid import run_auto_bid_aggressive
from core.allocation_algo import solve_model
from core.recommendation_algo import simulate_optimal_bid
from services.state_manager import load_products

# -----------------------------
# Charger les produits
# -----------------------------
products = load_products()  # Retourne une liste de dict {id, name, stock, starting_price, volume_multiple, seller_moq}

# -----------------------------
# Initialisation session state
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

# -----------------------------
# Formulaire acheteur
# -----------------------------
st.title("🏷️ Interface Acheteur")

with st.form("buyer_form"):
    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Activer Auto-bid", value=True)

    draft_products = {}
    for idx_p, p in enumerate(products):
        st.markdown(f"**{p['name']} ({p['id']})**")

        multiple = p["volume_multiple"]
        min_qty = max(p["seller_moq"], multiple)

        # Quantité désirée
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=min_qty,
            max_value=p["stock"],
            value=min_qty,
            step=multiple,
            key=f"qty_{p['id']}_{idx_p}"
        )

        # Prix courant actuel (max des autres acheteurs)
        prices = [
            b["products"][p["id"]]["current_price"]
            for b in st.session_state.buyers
            if p["id"] in b["products"]
        ]
        current_price = max(prices) if prices else p["starting_price"]

        st.metric(
            f"Prix courant – {p['id']}",
            f"{current_price:.2f} €"
        )

        # Prix max à proposer
        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=current_price,
            value=current_price,
            step=0.5,
            key=f"max_{p['id']}_{idx_p}"
        )

        draft_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": current_price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    # 🔹 Bouton unique pour tous les produits
    submit_all = st.form_submit_button("💰 Placer l’enchère pour tous les produits")

# -----------------------------
# Action du bouton unique
# -----------------------------
if submit_all and buyer_name:
    # Ajouter l’acheteur
    st.session_state.buyers.append({
        "name": buyer_name,
        "products": copy.deepcopy(draft_products),
        "auto_bid": auto_bid
    })

    # Lancer auto-bid simultanément sur tous les produits
    st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)

    st.success(f"Enchère placée pour tous les produits par {buyer_name}")

    # Affichage des résultats
    rows = []
    for pid, prod in draft_products.items():
        current_price = st.session_state.buyers[-1]["products"][pid]["current_price"]
        max_price = st.session_state.buyers[-1]["products"][pid]["max_price"]
        rows.append({
            "Produit": pid,
            "Qté désirée": prod["qty_desired"],
            "Prix courant (€)": current_price,
            "Prix max (€)": max_price
        })

    st.subheader(f"Résultat enchère pour {buyer_name}")
    st.dataframe(rows)

# -----------------------------
# Modifier prix max déjà saisis
# -----------------------------
st.subheader("✏️ Modifier les prix max")
for idx_b, buyer in enumerate(st.session_state.buyers):
    st.markdown(f"**{buyer['name']}**")
    cols = st.columns(len(products))
    for idx_p, (col, (pid, prod)) in enumerate(zip(cols, buyer["products"].items())):
        widget_key = f"edit_max_{buyer['name']}_{pid}_{idx_b}_{idx_p}"
        new_max = col.number_input(
            f"{pid}",
            min_value=prod["current_price"],
            value=prod["max_price"],
            step=0.5,
            key=widget_key
        )
        st.session_state.buyers[idx_b]["products"][pid]["max_price"] = new_max
        if st.session_state.buyers[idx_b]["products"][pid]["current_price"] > new_max:
            st.session_state.buyers[idx_b]["products"][pid]["current_price"] = new_max

# -----------------------------
# Simulation recommandation
# -----------------------------
st.subheader("💡 Simulation prix recommandé pour 100% du stock")
for buyer in st.session_state.buyers:
    user_qtys = {pid: p["qty_desired"] for pid, p in buyer["products"].items()}
    user_prices = {pid: p["current_price"] for pid, p in buyer["products"].items()}
    recs = simulate_optimal_bid(
        st.session_state.buyers,
        products,
        user_qtys=user_qtys,
        user_prices=user_prices,
        new_buyer_name=buyer["name"] + "_SIMULATION"
    )

    rec_rows = []
    for pid, rec in recs.items():
        rec_rows.append({
            "Produit": pid,
            "Prix recommandé (€)": rec["recommended_price"]
        })

    st.markdown(f"**Recommandation pour {buyer['name']}**")
    st.dataframe(rec_rows)
