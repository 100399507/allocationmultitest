import streamlit as st
import copy
import pandas as pd
from services.state_manager import load_json
from services.bid_service import save_final_allocations
from core.allocation_algo import run_auto_bid_aggressive, solve_model

def buyer_app():

    st.title("🛒 Espace Acheteur")

    # -----------------------------
    # Saisir un nouvel ID ou ID existant pour masquer les informations d'historique
    # -----------------------------

    buyer_id = st.text_input("Votre identifiant acheteur (confidentiel)")

    if not buyer_id:
        st.info("Veuillez saisir votre identifiant pour accéder à votre espace.")
        return
    
    st.title("🛒 Dashboard Acheteur")

    # Session state
    if "buyers" not in st.session_state:
        st.session_state.buyers = []

    # Charger les produits et historique d'enchère
    products = load_json("products.json")
    history = load_json("bids_history.json")
    
    # -----------------------------
    # Suivi de l'enchère acheteur
    # -----------------------------
    
    # Filtrer l'historique pour l'acheteur courant
    buyer_history = [
        h for h in history
        if h["buyer"] == buyer_id
    ]
    
    st.subheader("📊 Suivi de mon enchère")
    
    if not buyer_history:
        st.info(
            "Vous n'avez encore placé aucune enchère.\n\n"
            "👉 Renseignez vos prix et quantités ci-dessous pour commencer."
        )
    
    else:
        df = (
            pd.DataFrame(buyer_history)
            .assign(timestamp=lambda d: pd.to_datetime(d["timestamp"]))
            .sort_values("timestamp")
            .groupby("product", as_index=False)
            .last()
            .rename(columns={
                "product": "Produit",
                "qty_desired": "Qté demandée",
                "qty_allocated": "Qté allouée",
                "max_price": "Prix max (€)",
                "final_price": "Prix final (€)",
                "timestamp": "Dernière mise à jour"
            })
        )
    
        st.dataframe(
            df[[
                "Produit",
                "Qté demandée",
                "Qté allouée",
                "Prix max (€)",
                "Prix final (€)",
                "Dernière mise à jour"
            ]],
            use_container_width=True
        )
    
        total_desired = df["Qté demandée"].sum()
        total_allocated = df["Qté allouée"].sum()
    
        st.warning(
            f"⚠️ Allocation partielle : {total_allocated} / {total_desired} unités allouées.\n\n"
            "💡 Vous pouvez modifier votre prix max ou vos quantités et relancer une simulation."
        ) if total_allocated < total_desired else st.success(
            "✅ Vous êtes actuellement alloué à 100 % sur vos produits."
        )
    

    # -----------------------------
    # Cadre récapitulatif des produits
    # -----------------------------
    st.subheader("🛒 Vos produits et enchères")
    
    # --- Calculer le prix courant par produit (min final_price dernière enchère avec allocation >0) ---
    current_prices = {}
    for pid, p in products.items():
        # Filtrer uniquement les enchères avec allocation > 0
        product_history = [h for h in history if h["product"] == pid and h["qty_allocated"] > 0]
        if product_history:
            latest_ts = max(h["timestamp"] for h in product_history)
            last_round = [h for h in product_history if h["timestamp"] == latest_ts]
            current_prices[pid] = min(h["final_price"] for h in last_round)
        else:
            current_prices[pid] = p["starting_price"]
    
    # --- Récupérer les dernières valeurs de l'acheteur si existantes ---
    last_qty = {}
    if buyer_history:
        df_buyer = (
            pd.DataFrame(buyer_history)
            .assign(timestamp=lambda d: pd.to_datetime(d["timestamp"]))
            .sort_values("timestamp")
            .groupby("product", as_index=False)
            .last()
        )
        for _, row in df_buyer.iterrows():
            last_qty[row["product"]] = row["qty_desired"]
    
    # --- Boucle affichage produits avec inputs sur la même ligne ---
    draft_products = {}
    total_qty_desired = 0
    valid_input = True

        # ---- En-tête du tableau ----
    col_name_h, col_info_h, col_price_h, col_qty_h = st.columns([2, 2, 1.5, 1.5])
    
    with col_name_h:
        st.markdown("**Produit**")
    
    with col_info_h:
        st.markdown("**Informations**")
    
    with col_price_h:
        st.markdown("**Prix max (€)**")
    
    with col_qty_h:
        st.markdown("**Quantité désirée**")
    
    st.divider()  # optionnel, pour séparer visuellement
    
    for pid, p in products.items():
        col_name, col_info, col_price, col_qty = st.columns([2, 2, 1.5, 1.5])
    
        # Nom produit
        with col_name:
            st.markdown(f"**{p['name']}**")
    
        # Infos produit
        with col_info:
            st.markdown(f"Stock: {p['stock']}")
            st.markdown(f"Exp :  {p['shelf_life']}")
            
    
        # Prix max
        with col_price:
            starting_price = current_prices[pid]
            max_price = st.number_input(
                "",
                min_value=starting_price,
                step=0.5,
                key=f"max_{pid}"
            )
            st.caption(f"Prix min: {starting_price:.2f} €")
    
        # Quantité désirée
        with col_qty:
            default_qty = last_qty.get(pid, p["seller_moq"])
            qty = st.number_input(
                "",
                min_value=p["seller_moq"],
                max_value=p["stock"],
                step=p["volume_multiple"],
                value=default_qty,
                key=f"qty_{pid}"
            )
            st.caption(f"Min: {p['seller_moq']} | Multiple: {p['volume_multiple']}")
    
        # Vérification du multiple
        if qty % p["volume_multiple"] != 0:
            st.warning(f"La quantité pour {p['name']} doit être un multiple de {p['volume_multiple']}.")
            valid_input = False
    
        draft_products[pid] = {
            "qty_desired": qty,
            "current_price": starting_price,
            "max_price": max_price,
            "moq": p["seller_moq"],
            "volume_multiple": p["volume_multiple"],
            "stock": p["stock"]
        }
    
        total_qty_desired += qty
    
    # Vérification MOQ global
    GLOBAL_MOQ = 80
    if total_qty_desired < GLOBAL_MOQ:
        st.warning(f"La quantité totale demandée ({total_qty_desired}) doit être ≥ au MOQ global ({GLOBAL_MOQ}).")
        valid_input = False



    # -----------------------------
    # Bouton simulation + recommandation
    # -----------------------------
    
    #Passage par un state, sinon rerun et le bouton disparait
    if "sim_alloc" not in st.session_state:
        st.session_state.sim_alloc = {}  # dictionnaire vide au départ

    if st.button("🧪 Simuler mon allocation et recommandation", disabled=not valid_input):
        if not buyer_id:
            st.warning("Renseigne d'abord ton identifiant acheteur")
        else:
            # Copier les acheteurs existants pour ne pas toucher aux originaux
            buyers_copy = copy.deepcopy(st.session_state.buyers)
    
            # Créer un buyer temporaire pour simulation uniquement
            temp_buyer = {
                "name": "__SIMULATION__",
                "auto_bid": True,
                "products": copy.deepcopy(draft_products)
            }
            buyers_copy.append(temp_buyer)
    
            # Lancer auto-bid sur copie
            buyers_simulated = run_auto_bid_aggressive(buyers_copy, list(products.values()), max_rounds=30)

            # Récupérer allocations simulées
            allocations, _ = solve_model(buyers_simulated, list(products.values()))
            sim_alloc = allocations["__SIMULATION__"]
            
            # Stocker dans le session_state
            st.session_state.sim_alloc = sim_alloc

    
            # Affichage allocations simulées
            if st.session_state.sim_alloc:
                sim_rows = []
                for pid, prod in draft_products.items():
                    sim_rows.append({
                        "Produit": products[pid]["name"],
                        "Qté désirée": prod["qty_desired"],
                        "Qté allouée": st.session_state.sim_alloc.get(pid, 0),
                        "Prix courant simulé (€)": buyers_simulated[-1]["products"][pid]["current_price"],
                        "Prix max (€)": prod["max_price"]
                    })
            
            st.subheader("🧪 Résultat simulation allocation")
            st.dataframe(sim_rows)
    
            # -----------------------------
            # Recommandations prix pour obtenir 100% du stock
            # -----------------------------
            from core.recommendation import simulate_optimal_bid
    
            user_qtys = {pid: prod["qty_desired"] for pid, prod in draft_products.items()}
            user_prices = {pid: prod["current_price"] for pid, prod in draft_products.items()}
    
            recs = simulate_optimal_bid(
                st.session_state.buyers,  # on simule l'impact sur les autres acheteurs réels
                list(products.values()),
                user_qtys=user_qtys,
                user_prices=user_prices,
                new_buyer_name="__SIMULATION__"
            )
    
            rec_rows = []
            for pid, rec in recs.items():
                rec_rows.append({
                    "Produit": products[pid]["name"],
                    "Prix recommandé pour 100% allocation (€)": rec["recommended_price"]
                })
    
            st.subheader("💡 Recommandation prix pour obtenir 100% du stock")
            st.dataframe(rec_rows)
            
    # -----------------------------
    # Bouton pour valider l'enchère
    # -----------------------------
    if st.button("💰 Placer l’enchère pour tous les produits", disabled=not valid_input):
    
        # 1️⃣ Ajouter / mettre à jour le buyer
        if not any(b["name"] == buyer_id for b in st.session_state.buyers):
            st.session_state.buyers.append({
                "name": buyer_id,
                "products": copy.deepcopy(draft_products),
                "auto_bid": True
            })
        else:
            for b in st.session_state.buyers:
                if b["name"] == buyer_id:
                    b["products"] = copy.deepcopy(draft_products)
                    b["auto_bid"] = True
    
        # 2️⃣ AUTO-BID (formation des prix)
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers,list(products.values()))
    
        # 3️⃣ SOLVEUR (allocation finale)
        allocations, _ = solve_model(
            st.session_state.buyers,
            list(products.values())
        )
    
        # 4️⃣ SAUVEGARDE HISTORIQUE FINAL dans le tableau JSON
        save_final_allocations(st.session_state.buyers, allocations)
    
        # 5️⃣ AFFICHAGE POUR L’ACHETEUR COURANT
        buyer_alloc = allocations.get(buyer_id, {})
    
        result_rows = []
        for pid, prod in draft_products.items():
            result_rows.append({
                "Produit": products[pid]["name"],
                "Qté demandée": prod["qty_desired"],
                "Qté allouée": buyer_alloc.get(pid, 0),
                "Prix final (€)": next(
                    b for b in st.session_state.buyers if b["name"] == buyer_id
                )["products"][pid]["current_price"]
            })
    
        st.subheader("✅ Allocation finale du stock")
        st.dataframe(result_rows)
        st.success("Marché clôturé : allocation finale calculée et enregistrée")
    
    
