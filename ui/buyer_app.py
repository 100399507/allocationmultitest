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
    st.subheader("📦 Suivi global de mes lots")

    history = load_json("bids_history.json")
    lots = load_json("lots.json")
    products = load_json("products.json")

    # Historique de l'acheteur
    buyer_history = [h for h in history if h["buyer"] == buyer_id]

    # --- Cas 1 : aucune enchère ---
    if not buyer_history:
        st.info(
            "Vous n’avez encore placé aucune enchère.\n\n"
            "👉 Sélectionnez un lot ci-dessous pour commencer à enchérir."
        )
    else:
        rows = []

        # Lots sur lesquels l'acheteur a au moins une enchère
        buyer_lots = set(h["lot_id"] for h in buyer_history)

        for lot_id in buyer_lots:
            lot_name = lots.get(lot_id, {}).get("lot_name", lot_id)

            lot_hist = [h for h in buyer_history if h["lot_id"] == lot_id]

            # Dernière enchère du lot
            latest_ts = max(h["timestamp"] for h in lot_hist)
            last_round = [h for h in lot_hist if h["timestamp"] == latest_ts]

            qty_desired = sum(h["qty_desired"] for h in last_round)
            qty_allocated = sum(h["qty_allocated"] for h in last_round)

            allocation_rate = (
                round(qty_allocated / qty_desired * 100, 1)
                if qty_desired > 0 else 0
            )

            if qty_allocated == 0:
                status = "❌ Aucune allocation"
            elif qty_allocated < qty_desired:
                status = "⚠️ Allocation partielle"
            else:
                status = "✅ Allocation complète"

            rows.append({
                "Lot": lot_name,
                "Qté demandée": qty_desired,
                "Qté allouée": qty_allocated,
                "% allocation": allocation_rate,
                "Statut": status,
                "Dernière mise à jour": latest_ts
            })

        df = pd.DataFrame(rows).sort_values(
            "Dernière mise à jour", ascending=False
        )

        st.dataframe(df, use_container_width=True)

    lots = load_json("lots.json")
    lot_options = [""] + list(lots.keys())

    lot_id = st.selectbox(
        "📦 Sélectionnez un lot",
        options=lot_options,
        format_func=lambda k: "— Sélectionner un lot —"
        if k == "" else lots[k]["lot_name"]
    )

    if not lot_id:
        st.info("👆 Sélectionnez un lot pour afficher les produits et enchères.")
        st.stop()

    # Récupérer le seller pour ce lot
    seller_id = lots[lot_id].get("seller_id", None)
    if not seller_id:
        st.warning("Ce lot n'a pas de seller_id défini !")

    # Session state
    if "buyers" not in st.session_state:
        st.session_state.buyers = []

    # Charger les produits et historique d'enchère
    products = load_json("products.json")
    history = load_json("bids_history.json")

    # -----------------------------
    # Suivi de l'enchère acheteur
    # -----------------------------
    buyer_history = [
        h for h in history
        if h["buyer"] == buyer_id and h["lot_id"] == lot_id
    ]

    st.subheader("📊 Suivi de mon enchère")

    fully_allocated = False

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
        fully_allocated = (
            total_allocated >= total_desired and total_desired > 0
        )

        if fully_allocated:
            st.success("✅ Vous êtes actuellement alloué à 100 % sur vos produits.")
        else:
            st.warning(
                f"⚠️ Allocation partielle : {total_allocated} / {total_desired} unités allouées.\n\n"
                "💡 Vous pouvez modifier votre prix max ou vos quantités et relancer une simulation."
            )

    # -----------------------------
    # Cadre récapitulatif des produits
    # -----------------------------
    if not fully_allocated:

        st.subheader("🛒 Vos produits et enchères")

        # --- Calculer le prix courant par produit ---
        current_prices = {}

        lot_products = {
            pid: p for pid, p in products.items()
            if p["lot_id"] == lot_id
        }

        for pid, p in lot_products.items():
            product_history = [
                h for h in history
                if h["product"] == pid
                and h["qty_allocated"] > 0
                and h["lot_id"] == lot_id
            ]

            if product_history:
                latest_ts = max(h["timestamp"] for h in product_history)
                last_round = [
                    h for h in product_history
                    if h["timestamp"] == latest_ts
                ]
                current_prices[pid] = min(
                    h["final_price"] for h in last_round
                )
            else:
                current_prices[pid] = p["starting_price"]

        # --- Récupérer les dernières valeurs de l'acheteur ---
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

        draft_products = {}
        total_qty_desired = 0
        valid_input = True

        # En-tête
        col_name_h, col_info_h, col_price_h, col_qty_h = st.columns([2, 2, 1.5, 1.5])
        col_name_h.markdown("**Produit**")
        col_info_h.markdown("**Informations**")
        col_price_h.markdown("**Prix max (€)**")
        col_qty_h.markdown("**Quantité désirée**")

        st.divider()

        for pid, p in lot_products.items():

            col_name, col_info, col_price, col_qty = st.columns([2, 2, 1.5, 1.5])

            col_name.markdown(f"**{p['name']}**")
            col_info.markdown(f"Stock: {p['stock']}")
            col_info.markdown(f"Exp :  {p['shelf_life']}")

            starting_price = current_prices[pid]
            max_price = col_price.number_input(
                "",
                min_value=starting_price,
                step=0.5,
                key=f"max_{pid}"
            )
            col_price.caption(f"Prix min: {starting_price:.2f} €")

            default_qty = last_qty.get(pid, p["seller_moq"])
            qty = col_qty.number_input(
                "",
                min_value=p["seller_moq"],
                max_value=p["stock"],
                step=p["volume_multiple"],
                value=default_qty,
                key=f"qty_{pid}"
            )
            col_qty.caption(
                f"Min: {p['seller_moq']} | Multiple: {p['volume_multiple']}"
            )

            if qty % p["volume_multiple"] != 0:
                st.warning(
                    f"La quantité pour {p['name']} doit être un multiple de {p['volume_multiple']}."
                )
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

        GLOBAL_MOQ = lots[lot_id]["global_moq"]
        if total_qty_desired < GLOBAL_MOQ:
            st.warning(
                f"La quantité totale demandée ({total_qty_desired}) doit être ≥ au MOQ global ({GLOBAL_MOQ})."
            )
            valid_input = False

        # -----------------------------
        # Bouton simulation + recommandation
        # -----------------------------
        if st.button(
            "🧪 Simuler mon allocation et recommandation",
            disabled=not valid_input
        ):
            if not buyer_id:
                st.warning("Renseigne d'abord ton identifiant acheteur")
            else:
                buyers_copy = copy.deepcopy(st.session_state.buyers)

                for buyer in buyers_copy:
                    buyer["products"] = {
                        pid: prod for pid, prod in buyer["products"].items()
                        if pid in lot_products
                    }

                temp_buyer = {
                    "name": "__SIMULATION__",
                    "auto_bid": True,
                    "products": copy.deepcopy(draft_products)
                }
                buyers_copy.append(temp_buyer)

                buyers_copy_lot = []
                for b in buyers_copy:
                    filtered_products = {
                        pid: p for pid, p in b["products"].items()
                        if pid in lot_products
                    }
                    if filtered_products:
                        buyers_copy_lot.append({
                            "name": b["name"],
                            "auto_bid": b.get("auto_bid", False),
                            "products": filtered_products
                        })

                buyers_simulated = run_auto_bid_aggressive(
                    buyers_copy_lot,
                    list(lot_products.values()),
                    max_rounds=30
                )

                allocations, _ = solve_model(
                    buyers_simulated,
                    list(lot_products.values())
                )

                sim_alloc = allocations["__SIMULATION__"]

                sim_rows = []
                total_desired_sim = 0
                total_allocated_sim = 0

                for pid, prod in draft_products.items():
                    qty_desired = prod["qty_desired"]
                    qty_allocated = sim_alloc.get(pid, 0)

                    total_desired_sim += qty_desired
                    total_allocated_sim += qty_allocated

                    sim_rows.append({
                        "Produit": products[pid]["name"],
                        "Qté désirée": prod["qty_desired"],
                        "Qté allouée": qty_allocated,
                        "Prix courant simulé (€)": buyers_simulated[-1]["products"][pid]["current_price"],
                        "Prix max (€)": prod["max_price"]
                    })

                if total_allocated_sim >= total_desired_sim and total_desired_sim > 0:
                    st.success(
                        f"✅ Simulation : Allocation complète ({total_allocated_sim}/{total_desired_sim})"
                    )
                else:
                    st.warning(
                        f"⚠️ Simulation : Allocation partielle ({total_allocated_sim}/{total_desired_sim})"
                    )

                st.subheader("🧪 Résultat simulation allocation")
                st.dataframe(sim_rows)

                from core.recommendation import simulate_optimal_bid

                buyers_copy_lot = []
                for b in st.session_state.buyers:
                    filtered_products = {
                        pid: p for pid, p in b["products"].items()
                        if pid in lot_products
                    }
                    if filtered_products:
                        buyers_copy_lot.append({
                            "name": b["name"],
                            "auto_bid": b.get("auto_bid", False),
                            "products": filtered_products
                        })

                buyers_copy_lot.append({
                    "name": "__SIMULATION__",
                    "auto_bid": True,
                    "products": copy.deepcopy(draft_products)
                })

                recs = simulate_optimal_bid(
                    buyers_copy_lot,
                    list(lot_products.values()),
                    user_qtys={pid: prod["qty_desired"] for pid, prod in draft_products.items()},
                    user_prices={pid: prod["current_price"] for pid, prod in draft_products.items()},
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
        if st.button(
            "💰 Placer l’enchère pour tous les produits",
            disabled=not valid_input
        ):

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

            buyers_for_lot = []
            for b in st.session_state.buyers:
                filtered_products = {
                    pid: p for pid, p in b["products"].items()
                    if pid in lot_products
                }
                if filtered_products:
                    buyers_for_lot.append({
                        "name": b["name"],
                        "auto_bid": b.get("auto_bid", False),
                        "products": filtered_products
                    })

            st.session_state.buyers = run_auto_bid_aggressive(
                buyers_for_lot,
                list(lot_products.values())
            )

            allocations, _ = solve_model(
                st.session_state.buyers,
                list(lot_products.values())
            )

            save_final_allocations(
                st.session_state.buyers,
                allocations,
                lot_id,
                seller_id
            )

            buyer_alloc = allocations.get(buyer_id, {})

            result_rows = []
            for pid, prod in draft_products.items():
                result_rows.append({
                    "Produit": products[pid]["name"],
                    "Qté demandée": prod["qty_desired"],
                    "Qté allouée": buyer_alloc.get(pid, 0),
                    "Prix final (€)": next(
                        b for b in st.session_state.buyers
                        if b["name"] == buyer_id
                    )["products"][pid]["current_price"]
                })

            st.subheader("✅ Allocation finale du stock")
            st.dataframe(result_rows)
            st.success("Marché clôturé : allocation finale calculée et enregistrée")
