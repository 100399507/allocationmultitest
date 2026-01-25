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

    with st.expander("📝 Informations sur les produits (cliquer pour afficher)", expanded=True):
       # Dictionnaire pour stocker le prix courant par produit
        current_prices = {}

        for pid, p in products.items():
            # Filtrer uniquement les enchères avec allocation > 0 pour ce produit
            product_history = [h for h in history if h["product"] == pid and h["qty_allocated"] > 0]
        
            if product_history:
                # Dernier round
                latest_ts = max(h["timestamp"] for h in product_history)
                last_round = [h for h in product_history if h["timestamp"] == latest_ts]
                current_price = min(h["final_price"] for h in last_round)
            else:
                current_price = p["starting_price"]
        
            current_prices[pid] = current_price  # stocker dans le dict
        
        # Pour ton tableau résumé
        product_summary.append({
            "Produit": p["name"],
            "Stock total": p["stock"],
            "MOQ": p["seller_moq"],
            "Volume multiple": p["volume_multiple"],
            "Prix de départ (€)": f"{current_price:.2f}"
        })
    
    st.table(pd.DataFrame(product_summary))
    st.info("Minimum de commande tout produit avant et après allocation : 80")

    # -----------------------------
    # Créer un "draft" temporaire des entrées de l'acheteur
    # -----------------------------
    draft_products = {}
    total_qty_desired = 0  # pour MOQ global
    valid_input = True     # flag global
    
    
    for pid, p in products.items():

        col1, col2, col3 = st.columns([1, 1, 1])
        
        # prix max
        with col1:
            st.markdown(f"<span style='font-size:16px; font-weight:bold'>{p['name']}</span>", unsafe_allow_html=True)
            
        with col2:
            starting_price = current_prices[pid]  #Prix min avec du stock alloué dernière enchère
            max_price = st.number_input(
                "Prix max",
                min_value=starting_price,
                step=0.5,
                key=f"max_{pid}"
            )
            st.caption(f"Prix de départ : {starting_price:.2f} €")

        # quantité désirée
        with col3:
            qty = st.number_input("Quantité désirée",min_value=p["seller_moq"],max_value=p["stock"],step=p["volume_multiple"],key=f"qty_{pid}"
                                 )
            st.caption(f"Min : {p['seller_moq']}   Max : {p['stock']}   Multiple : {p['volume_multiple']}")

        
        # Vérification du multiple
        if qty % p["volume_multiple"] != 0:
            st.warning(f"La quantité pour {p['name']} doit être un multiple de {p['volume_multiple']}.")
            valid_input = False
        
        
        draft_products[pid] = {
        "qty_desired": qty,
        "current_price": starting_price,  # prix courant max 
        "max_price": max_price,
        "moq": p["seller_moq"],               
        "volume_multiple": p["volume_multiple"],
        "stock": p["stock"]
        }
        
        total_qty_desired += qty


    # Vérification MOQ global
    GLOBAL_MOQ = 80
    if total_qty_desired < GLOBAL_MOQ:
        st.warning(f"La quantité totale demandée ({total_qty_desired}) doit être supérieure au minimum de commande global ({GLOBAL_MOQ}).")
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
                        "Produit": pid,
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
    
    
