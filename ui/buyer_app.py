import streamlit as st
import copy
from services.state_manager import load_json
from services.bid_service import place_bid
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
    # Bouton unique pour tous les produits
    # -----------------------------
    if st.button("💰 Placer l’enchère pour tous les produits"):
        # Ajouter le buyer courant s'il n'existe pas encore
        if not any(b["name"] == buyer_id for b in st.session_state.buyers):
            st.session_state.buyers.append({
                "name": buyer_id,
                "products": copy.deepcopy(draft_products),
                "auto_bid": True
            })
        else:
            # Mettre à jour les valeurs si déjà présent
            for b in st.session_state.buyers:
                if b["name"] == buyer_id:
                    b["products"] = copy.deepcopy(draft_products)
                    b["auto_bid"] = True

        # Placer les enchères (optionnel si tu as une fonction place_bid par produit)
        for pid, prod in draft_products.items():
            place_bid(buyer_id, pid, prod["qty_desired"], prod["max_price"])

        # Lancer l'auto-bid pour tous les buyers
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, list(products.values()))

        st.success("Enchères placées et auto-bid lancé pour tous les produits")


        # -----------------------------
        # Bouton simulation + recommandation
        # -----------------------------
        if st.button("🧪 Simuler mon allocation et recommandation"):
            if not buyer_id:
                st.warning("Renseigne d'abord ton identifiant acheteur")
            else:
                # Copier les acheteurs existants pour ne pas toucher aux originaux
                buyers_copy = copy.deepcopy(st.session_state.buyers)
        
                # Créer un buyer temporaire pour simulation
                temp_buyer = {
                    "name": "__SIMULATION__",
                    "auto_bid": True,
                    "products": copy.deepcopy(draft_products)
                }
                buyers_copy.append(temp_buyer)
        
                # Lancer auto-bid sur copie uniquement
                from core.allocation_algo import run_auto_bid_aggressive, solve_model
                buyers_simulated = run_auto_bid_aggressive(buyers_copy, list(products.values()), max_rounds=30)
        
                # Récupérer allocations
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
        
                # Recommandations prix pour 100% allocation
                from allocation_recommendation import simulate_optimal_bid
        
                user_qtys = {pid: prod["qty_desired"] for pid, prod in draft_products.items()}
                user_prices = {pid: prod["current_price"] for pid, prod in draft_products.items()}
        
                recs = simulate_optimal_bid(
                    st.session_state.buyers,  # On utilise les acheteurs réels pour simuler l'impact
                    list(products.values()),
                    user_qtys=user_qtys,
                    user_prices=user_prices,
                    new_buyer_name="__SIMULATION__"
                )
        
                rec_rows = []
                for pid, rec in recs.items():
                    rec_rows.append({
                        "Produit": pid,
                        "Prix recommandé pour 100% allocation (€)": rec["recommended_price"]
                    })
        
                st.subheader("💡 Recommandation prix pour obtenir 100% du stock")
                st.dataframe(rec_rows)

        # -----------------------------
        # Bouton simulation + recommandation
        # -----------------------------
        # Affichage des résultats après auto-bid

        result_rows = []
        
        # Récupérer l'index et l'objet acheteur final
        buyer_index = next(i for i, b in enumerate(st.session_state.buyers) if b["name"] == buyer_id)
        buyer_final = st.session_state.buyers[buyer_index]
        
        # ⚡ Récupérer les allocations finales
        allocations, _ = solve_model(st.session_state.buyers, list(products.values()))
        
        for pid, prod in draft_products.items():
            current_price = buyer_final["products"][pid]["current_price"]
            qty_allocated = allocations[buyer_id][pid]  # <-- récupérer la quantité allouée ici
            result_rows.append({
                "Produit": pid,
                "Qté désirée": prod["qty_desired"],
                "Qté allouée": qty_allocated, 
                "Prix courant (€)": current_price,
                "Prix max (€)": prod["max_price"]
            })
        
        st.subheader("Résultat enchères après Auto-bid")
        st.dataframe(result_rows)

