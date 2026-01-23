import streamlit as st
import copy
from services.state_manager import load_json
from services.bid_service import save_final_allocations
from core.allocation_algo import run_auto_bid_aggressive, solve_model

def buyer_app():
    st.title("🛒 Interface Acheteur")

    # Session state
    if "buyers" not in st.session_state:
        st.session_state.buyers = []

    # Charger les produits
    products = load_json("products.json")
    buyer_id = st.text_input("Votre identifiant acheteur", "buyer_A")

    # -----------------------------
    # Créer un "draft" temporaire des entrées de l'acheteur
    # -----------------------------
    draft_products = {}
    for pid, p in products.items():
        st.subheader(p["name"])
        st.metric("Prix de départ", f"{p['starting_price']} €")

        qty = st.number_input(
            "Quantité désirée",
            min_value=p["seller_moq"],
            step=p["volume_multiple"],
            key=f"qty_{pid}"
        )
        max_price = st.number_input(
            "Prix max",
            min_value=p["starting_price"],
            step=0.5,
            key=f"max_{pid}"
        )

        draft_products[pid] = {
            "qty_desired": qty,
            "current_price": p["starting_price"],  # valeur initiale
            "max_price": max_price,
            "moq": p["seller_moq"],               # nécessaire pour solve_model
            "volume_multiple": p["volume_multiple"],
            "stock": p["stock"]
        }

    # -----------------------------
    # Bouton simulation + recommandation
    # -----------------------------
    if st.button("🧪 Simuler mon allocation et recommandation"):
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
    
            # ⚡ Récupérer allocations simulées
            allocations, _ = solve_model(buyers_simulated, list(products.values()))
            sim_alloc = allocations["__SIMULATION__"]
    
            # Affichage allocations simulées
            sim_rows = []
            for pid, prod in draft_products.items():
                sim_rows.append({
                    "Produit": pid,
                    "Qté désirée": prod["qty_desired"],
                    "Qté allouée": sim_alloc.get(pid, 0),
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
    # Bouton unique pour tous les produits
    # -----------------------------

    if st.button("💰 Placer l’enchère pour tous les produits"):
    
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
    
        # 4️⃣ SAUVEGARDE HISTORIQUE FINAL
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
    
        
