"""Variant D: Affordability-scaled animal purchasing.
Instead of requiring cash for 3 animals at once, buy whatever animals are affordable
(1, 2, or 3) into available structures, allowing immediate livestock on Day 0.
Tested against CURRENT BASELINE directly.
"""
import main as base_module

def patched_generate_market_orders(day, hour, money, shed, seeds, market_inv,
                                    market_prices, shops, me, chosen_crop,
                                    chosen_animal, target_animal_count, total_tasks):
    tiles_data = me.get("tiles", [])
    _, _, animal_tiles, structs_empty, _ = base_module.scan_tiles(tiles_data)
    current_animals = len(animal_tiles)
    hires_today = me.get("hires_today", 0)
    n_unlocked = len(me.get("unlocked_quadrants", ["NW"]))

    shed_total = sum(int(v) for v in shed.values())
    remaining_days = max(1, 30 - day)

    feed_reserve = current_animals * remaining_days + current_animals
    sellable_wheat = max(0, int(shed.get("WHEAT", 0)) - feed_reserve)

    orders = []
    remaining_money = money

    # 1. SELL candidates
    sell_candidates = []
    for product, qty_raw in shed.items():
        qty = int(qty_raw)
        if qty <= 0 or product not in base_module.MP:
            continue
        if product == "WHEAT":
            qty = sellable_wheat
            if qty <= 0:
                continue
        price = base_module.compute_price(product, market_inv.get(product, 10000))
        base = base_module.MP[product]["base"]

        if day >= 28:
            sell_qty = qty
        elif shed_total >= 85:
            sell_qty = qty
        elif price >= base * 0.50:
            sell_qty = qty
        elif price >= base * 0.30:
            sell_qty = min(qty, max(1, qty // 2))
        else:
            if day >= 25:
                sell_qty = qty
            else:
                continue

        if sell_qty > 0:
            score = price * sell_qty
            sell_candidates.append((score, product, sell_qty))

    sell_candidates.sort(reverse=True)
    for _, product, sell_qty in sell_candidates:
        if len(orders) >= base_module.MAX_MARKET_ORDERS - 2:
            break
        orders.append(["SELL", product, sell_qty])

    # 2. HIRE
    if hour == 0 or (hour <= 2 and hires_today == 0):
        n_hires = base_module.optimal_hire_count(total_tasks, hires_today, remaining_money)
        for _ in range(n_hires):
            if len(orders) >= base_module.MAX_MARKET_ORDERS:
                break
            cost = base_module.fib(hires_today)
            if remaining_money >= cost:
                orders.append(["HIRE"])
                remaining_money -= cost
                hires_today += 1

    # 3. BUY_SEED
    current_seeds = int(seeds.get(chosen_crop, 0))
    empty_count = len([1 for row in tiles_data for t in row if t is None])
    if current_seeds < max(3, empty_count) and day < 29 and len(orders) < base_module.MAX_MARKET_ORDERS:
        want_seeds = min(20, max(5, empty_count - current_seeds))
        cost = want_seeds * base_module.CROP[chosen_crop]["seed"]
        if remaining_money >= cost + 300:
            orders.append(["BUY_SEED", chosen_crop, want_seeds])
            remaining_money -= cost

    # 4. BUY_PRODUCT WHEAT (Buffer replenishment)
    if current_animals > 0 and len(orders) < base_module.MAX_MARKET_ORDERS:
        current_wheat = int(shed.get("WHEAT", 0))
        target_wheat = min(80, current_animals * max(2, min(5, remaining_days)))
        wheat_deficit = max(0, target_wheat - current_wheat)
        if wheat_deficit > 0:
            wheat_buy_price = base_module.compute_price("WHEAT", market_inv.get("WHEAT", 10000))
            cost = wheat_deficit * wheat_buy_price
            if remaining_money >= cost + 200:
                orders.append(["BUY_PRODUCT", "WHEAT", wheat_deficit])
                remaining_money -= cost

    # 5. BUY_ANIMAL (AFFORDABILITY-SCALED, NO OVERBUYING)
    if chosen_animal and len(orders) < base_module.MAX_MARKET_ORDERS:
        a_info = base_module.ANIMAL[chosen_animal]
        animals_in_shed = int(shed.get(chosen_animal, 0))
        total_owned = current_animals + animals_in_shed
        deficit = max(0, target_animal_count - total_owned)
        
        expected_kind = a_info["structure"]
        matching_empty = sum(1 for pos, t in structs_empty if t.get("kind") == expected_kind)
        can_place = max(0, matching_empty - animals_in_shed)
        
        needed = min(deficit, can_place)
        if needed > 0:
            # Check how many we can actually afford with safety reserve of 300
            max_affordable = max(0, int((remaining_money - 300) // a_info["cost"]))
            want = min(3, needed, max_affordable)
            if want > 0:
                cost = want * a_info["cost"]
                orders.append(["BUY_ANIMAL", chosen_animal, want])
                remaining_money -= cost

    # 6. BUY_LAND
    if len(orders) < base_module.MAX_MARKET_ORDERS:
        best_npv_day = base_module.crop_npv(chosen_crop, day, market_inv, shops) / max(1, base_module.CROP[chosen_crop]["max_day"])
        if base_module.should_buy_land(remaining_money, n_unlocked, day, best_npv_day):
            orders.append(["BUY_LAND"])
            land_cost = {1: 1000, 2: 2000, 3: 4000}.get(n_unlocked, 0)
            remaining_money -= land_cost

    return orders[:base_module.MAX_MARKET_ORDERS]

def agent(obs):
    orig_fn = base_module.generate_market_orders
    base_module.generate_market_orders = patched_generate_market_orders
    try:
        return base_module.agent(obs)
    finally:
        base_module.generate_market_orders = orig_fn
