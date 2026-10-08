"""Kaggriculture V2 — Strategic Planner Agent.

Architecture: GameState → MarketModel → EconomicEvaluator → TaskPlanner
             → WorkerScheduler → MarketOrderGenerator → ActionEmitter

No external dependencies. Single-file submission.
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

BOARD = 10
HALF = BOARD // 2  # 5
SHED_TILES = [(HALF - 1, HALF - 1), (HALF, HALF - 1),
              (HALF - 1, HALF), (HALF, HALF)]  # (4,4),(5,4),(4,5),(5,5)
SEASON_DAYS = 30
TURNS_PER_DAY = 24
TOTAL_TURNS = SEASON_DAYS * TURNS_PER_DAY  # 720
SHED_CAP = 100
MAX_MARKET_ORDERS = 10

MP = {  # Market parameters — exact from spec
    "WHEAT":       {"base": 25,  "I0": 10000, "T": 400, "bf": "sqrt",  "bt": 0.80, "af": "log",    "at": 0.20},
    "CARROT":      {"base": 35,  "I0": 10000, "T": 450, "bf": "hinge", "bt": 1.00, "af": "sqrt",   "at": 0.70},
    "TOMATO":      {"base": 60,  "I0": 10000, "T": 200, "bf": "hinge", "bt": 0.40, "af": "sqrt",   "at": 0.60},
    "STRAWBERRY":  {"base": 120, "I0": 10000, "T": 100, "bf": "sqrt",  "bt": 0.70, "af": "linear", "at": 1.60},
    "MELON":       {"base": 250, "I0": 10000, "T": 300, "bf": "log",   "bt": 0.20, "af": "sq",     "at": 3.60},
    "EGG":         {"base": 50,  "I0": 10000, "T": 332, "bf": "hinge", "bt": 0.40, "af": "log",    "at": 0.20},
    "MILK":        {"base": 160, "I0": 10000, "T": 122, "bf": "sqrt",  "bt": 0.60, "af": "linear", "at": 1.60},
    "WOOL":        {"base": 200, "I0": 10000, "T": 105, "bf": "log",   "bt": 0.20, "af": "sq",     "at": 3.20},
    "FERTILIZER":  {"base": 100, "I0": 10000, "T": 200, "bf": "linear","bt": 0.40, "af": "linear", "at": 0.40},
}

CROP = {
    "WHEAT":      {"seed": 10,  "first": 2, "max_day": 4,  "type": "onetime",  "max_yield": 6, "unfert_yield": 4, "bonus_start": 2},
    "CARROT":     {"seed": 20,  "first": 2, "max_day": 3,  "type": "onetime",  "max_yield": 4, "unfert_yield": 3, "bonus_start": 2},
    "TOMATO":     {"seed": 50,  "first": 8, "max_day": 11, "type": "ongoing",  "max_yield": 4, "unfert_yield": 4, "bonus_start": -1,
                   "prod_ages": [8, 9, 10, 11]},
    "STRAWBERRY": {"seed": 100, "first": 10,"max_day": 16, "type": "ongoing",  "max_yield": 4, "unfert_yield": 4, "bonus_start": -1,
                   "prod_ages": [10, 12, 14, 16]},
    "MELON":      {"seed": 80,  "first": 10,"max_day": 10, "type": "onetime",  "max_yield": 6, "unfert_yield": 6, "bonus_start": 6},
}
CROP_PRODUCT = {c: c for c in CROP}

ANIMAL = {
    "GOOSE": {"cost": 300, "product": "EGG",  "interval": 1, "structure": "COOP",    "first_yield": 4, "max_held": 4},
    "COW":   {"cost": 400, "product": "MILK", "interval": 2, "structure": "PASTURE", "first_yield": 8, "max_held": 6},
    "SHEEP": {"cost": 500, "product": "WOOL", "interval": 3, "structure": "PASTURE", "first_yield": 6, "max_held": 6},
}

SHOP_DEMANDS = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN STORE":     ["WOOL"],
    "ICE CREAM SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET CAFE":       ["CARROT"],
    "SMOOTHIE SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
SINGLE_PRODUCT_SHOPS = {"YARN STORE", "PET CAFE"}

_FIB_CACHE = [1, 1]
def fib(n: int) -> int:
    while len(_FIB_CACHE) <= n:
        _FIB_CACHE.append(_FIB_CACHE[-1] + _FIB_CACHE[-2])
    return _FIB_CACHE[n]

def hire_cost_total(already_hired: int, n: int) -> int:
    return sum(fib(already_hired + i) for i in range(n))

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PRICE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _shape(name: str, x: float, T: float) -> float:
    """Evaluate shape function f(x). All satisfy f(0) = 0."""
    if name == "linear":
        return x
    if name == "sq":
        return x * x
    if name == "sqrt":
        return math.sqrt(max(0.0, x))
    if name == "log":
        return math.log(1.0 + x)
    if name == "log10":
        return math.log10(1.0 + x)
    if name == "hinge":
        u = x / T if T > 0 else 0.0
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x

def compute_price(product: str, inv: int) -> int:
    """Exact market price per spec. Returns integer ≥ 1."""
    p = MP[product]
    base, I0, T_ = p["base"], p["I0"], p["T"]
    delta = inv - I0
    if delta == 0:
        return base
    if delta < 0:  # scarcity → price up
        func, target = p["bf"], p["bt"]
        x = float(-delta)
        fT = _shape(func, float(T_), float(T_))
        if fT == 0:
            return base
        amp = target * base / fT
        price = base + amp * _shape(func, x, float(T_))
    else:  # glut → price down
        func, target = p["af"], p["at"]
        x = float(delta)
        fT = _shape(func, float(T_), float(T_))
        if fT == 0:
            return base
        amp = target * base / fT
        price = base - amp * _shape(func, x, float(T_))
    return max(1, round(price))

def marginal_revenue(product: str, current_inv: int, quantity: int) -> int:
    """Total revenue from selling `quantity` units one at a time."""
    total = 0
    inv = current_inv
    for _ in range(quantity):
        p = compute_price(product, inv)
        total += p
        if p > 1:
            inv += 1
    return total

def town_daily_consumption(product: str, shops: List[str]) -> int:
    """Units of `product` consumed per day by town center + shops."""
    if product == "FERTILIZER":
        return 0
    demand = 1
    for shop in shops:
        prods = SHOP_DEMANDS.get(shop, [])
        if product in prods:
            is_single = shop in SINGLE_PRODUCT_SHOPS
            ticks_per_day = TURNS_PER_DAY // 4  # 6
            per_tick = 2 if is_single else 1
            demand += ticks_per_day * per_tick
    return demand

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — ECONOMICS
# ═══════════════════════════════════════════════════════════════════════════════

def crop_yield_unfert(crop: str) -> int:
    """Expected yield when watered every day, no fertilizer."""
    c = CROP[crop]
    if c["type"] == "onetime":
        bonus_days = c["max_day"] - c["bonus_start"] + 1
        return min(c["max_yield"], 1 + bonus_days)
    else:
        return c["max_yield"]

def crop_harvest_age(crop: str) -> int:
    """Age (in days) at which a one-time crop should be harvested for max yield."""
    c = CROP[crop]
    return c["max_day"]

def crop_npv(crop: str, plant_day: int, market_inv: Dict[str, int],
             shops: List[str]) -> float:
    """NPV of one tile-rotation of this crop planted on plant_day."""
    c = CROP[crop]
    harvest_day = plant_day + c["max_day"]
    if harvest_day > 29:
        if c["type"] == "onetime":
            earliest_harvest = plant_day + c["first"]
            if earliest_harvest > 29:
                return -999.0
            available_bonus = max(0, min(29 - plant_day, c["max_day"]) - c["bonus_start"] + 1)
            y = min(c["unfert_yield"], 1 + available_bonus)
            harvest_day = min(29, plant_day + c["max_day"])
        else:
            prods = [a for a in c.get("prod_ages", []) if plant_day + a <= 29]
            if not prods:
                return -999.0
            y = len(prods)
            harvest_day = plant_day + max(prods)
    else:
        y = crop_yield_unfert(crop)

    drain = town_daily_consumption(crop, shops)
    days_until_harvest = max(1, harvest_day - plant_day)
    future_inv = max(0, market_inv.get(crop, 10000) - drain * days_until_harvest)
    sell_price = compute_price(crop, future_inv)
    revenue = y * sell_price
    return float(revenue - c["seed"])

def multi_rotation_npv(crop: str, start_day: int, market_inv: Dict[str, int],
                       shops: List[str]) -> Tuple[float, int]:
    """Total NPV and rotation count for repeated planting from start_day."""
    c = CROP[crop]
    total = 0.0
    rotations = 0
    d = start_day
    cycle = c["max_day"]
    while d + c["first"] <= 29:
        npv = crop_npv(crop, d, market_inv, shops)
        if npv < 0:
            break
        total += npv
        rotations += 1
        d += cycle
    return total, rotations

def animal_npv(animal: str, place_day: int, market_inv: Dict[str, int],
               shops: List[str], wheat_buy_price: int) -> float:
    """NPV of placing this animal on place_day, accounting for feed cost."""
    a = ANIMAL[animal]
    first_prod_day = place_day + a["first_yield"]
    if first_prod_day > 29:
        return -999.0
    prod_days = []
    d = first_prod_day
    while d <= 29:
        prod_days.append(d)
        d += a["interval"]
    if not prod_days:
        return -999.0

    yield_per_prod = 1 + a["interval"]
    total_yield = len(prod_days) * yield_per_prod
    product = a["product"]
    drain = town_daily_consumption(product, shops)
    avg_harvest_day = sum(prod_days) / len(prod_days)
    days_to_avg = max(1, int(avg_harvest_day - place_day))
    future_inv = max(0, market_inv.get(product, 10000) - drain * days_to_avg)
    sell_price = compute_price(product, future_inv)
    revenue = total_yield * sell_price

    remaining_days = 30 - place_day
    feed_cost = remaining_days * wheat_buy_price
    fert_price = compute_price("FERTILIZER", market_inv.get("FERTILIZER", 10000))
    fert_revenue = remaining_days * fert_price * 0.5
    purchase = a["cost"]
    return float(revenue + fert_revenue - feed_cost - purchase)

def best_crop_for_day(day: int, market_inv: Dict[str, int],
                      shops: List[str]) -> str:
    """Pick crop with highest NPV/day for remaining season."""
    best_name = "CARROT"
    best_score = -1e9
    for name in CROP:
        total, rots = multi_rotation_npv(name, day, market_inv, shops)
        if rots == 0:
            continue
        remaining = max(1, 30 - day)
        score = total / remaining
        if score > best_score:
            best_score = score
            best_name = name
    return best_name

def best_animal_for_day(day: int, market_inv: Dict[str, int],
                        shops: List[str]) -> Optional[str]:
    """Pick animal with highest NPV, or None if all negative."""
    wheat_price = compute_price("WHEAT", market_inv.get("WHEAT", 10000))
    best_name = None
    best_npv = 0.0
    for name in ANIMAL:
        npv = animal_npv(name, day, market_inv, shops, wheat_price)
        if npv > best_npv:
            best_npv = npv
            best_name = name
    return best_name

def should_buy_land(money: float, n_unlocked: int, day: int,
                    best_tile_npv_per_day: float) -> bool:
    """Is land expansion NPV-positive?"""
    if n_unlocked >= 4:
        return False
    cost = {1: 1000, 2: 2000, 3: 4000}.get(n_unlocked)
    if cost is None or money < cost + 500:
        return False
    remaining = max(1, 30 - day)
    new_tiles = 25
    expected_value = new_tiles * 0.6 * best_tile_npv_per_day * remaining
    return expected_value > cost

def optimal_hire_count(task_count: int, hires_today: int, money: float) -> int:
    """How many additional workers to hire."""
    max_hires = min(6, task_count)
    affordable = 0
    budget = min(money * 0.05, 50.0)
    total_cost = 0
    for i in range(max_hires):
        c = fib(hires_today + i)
        if total_cost + c > budget and i >= 4:
            break
        total_cost += c
        affordable = i + 1
    return affordable

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def nearest_shed_tile(pos: Tuple[int, int]) -> Tuple[int, int]:
    return min(SHED_TILES, key=lambda s: manhattan(pos, s))

def is_shed_adjacent(pos: Tuple[int, int]) -> bool:
    return pos in SHED_TILES

def move_towards(pos: Tuple[int, int], target: Tuple[int, int]) -> str:
    x, y = pos
    tx, ty = target
    if x < tx: return "EAST"
    if x > tx: return "WEST"
    if y < ty: return "SOUTH"
    if y > ty: return "NORTH"
    return "PASS"

def scan_tiles(tiles):
    """Parse tile grid into categorized lists."""
    empty, plants, animals, structs_empty, weeds = [], [], [], [], []
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            pos = (x, y)
            if t is None:
                empty.append(pos)
            elif isinstance(t, str):
                continue  # "LOCKED"
            elif t.get("kind") == "WEED":
                weeds.append(pos)
            elif t.get("kind") == "PLANT":
                plants.append((pos, t))
            elif t.get("kind") in ("COOP", "PASTURE"):
                if t.get("animal"):
                    animals.append((pos, t))
                else:
                    structs_empty.append((pos, t))
    return empty, plants, animals, structs_empty, weeds

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — TASK GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_tasks(day: int, hour: int, tiles, shed: Dict, seeds: Dict,
                   market_inv: Dict, shops: List[str],
                   chosen_crop: str, chosen_animal: Optional[str],
                   target_animal_count: int) -> List[Tuple]:
    """Produce a priority-sorted task list from current tile state."""
    empty, plants, animals, structs_empty, weeds = scan_tiles(tiles)
    tasks = []

    plant_priority = max(10, int(50 - day * 1.2))
    current_animal_count = len(animals)
    structures_needed = max(0, target_animal_count - current_animal_count - len(structs_empty))
    build_slots = 0

    for pos in empty:
        if build_slots < structures_needed and chosen_animal:
            struct_type = ANIMAL[chosen_animal]["structure"]
            tasks.append((plant_priority + 10, pos, "BUILD", {"structure": struct_type}))
            build_slots += 1
        else:
            tasks.append((plant_priority, pos, "PLANT", {"crop": chosen_crop}))

    for pos, tile in plants:
        crop_name = tile.get("crop", "")
        if not crop_name or crop_name not in CROP:
            continue
        c = CROP[crop_name]
        age = day - tile.get("planted_day", day)
        watered = tile.get("watered_today", False)
        consec_unwatered = tile.get("consecutive_unwatered", 0)
        yield_units = tile.get("yield_units", 0)

        if not watered:
            urgency = 200 if consec_unwatered >= 1 else 100
            tasks.append((urgency, pos, "WATER", {}))

        if c["type"] == "onetime":
            if yield_units > 0 and age >= c["first"]:
                at_max = yield_units >= c["unfert_yield"]
                near_decay = age >= c["max_day"]
                endgame = day >= 27
                if at_max or near_decay or endgame:
                    tasks.append((90, pos, "HARVEST", {}))
        else:
            if yield_units > 0:
                max_h = c["max_yield"]
                urgency = 95 if yield_units >= max_h - 1 else 70
                tasks.append((urgency, pos, "HARVEST", {}))

        if c["type"] == "onetime" and c["bonus_start"] > 0:
            fert_until = tile.get("fertilized_until_day", -1)
            in_window = c["bonus_start"] <= age <= c["max_day"]
            not_already_fert = fert_until < day
            if in_window and not_already_fert:
                extra_yield = min(3, c["max_yield"] - c["unfert_yield"])
                if extra_yield > 0:
                    sell_price = compute_price(crop_name, market_inv.get(crop_name, 10000))
                    fert_cost = compute_price("FERTILIZER", market_inv.get("FERTILIZER", 10000))
                    if extra_yield * sell_price > fert_cost * 1.5:
                        tasks.append((60, pos, "FERTILIZE", {}))

    for pos, tile in animals:
        animal_name = tile.get("animal", "")
        if not animal_name:
            continue
        fed = tile.get("fed_today", False)
        consec_unfed = tile.get("consecutive_unfed", 0)
        cared = tile.get("cared_today", False)
        fert_avail = tile.get("fertilizer_available", False)
        yield_units = tile.get("yield_units", 0)

        if not fed:
            urgency = 210 if consec_unfed >= 1 else 105
            tasks.append((urgency, pos, "FEED", {}))

        if not cared and fed:
            tasks.append((80, pos, "CARE", {}))

        if fert_avail:
            tasks.append((55, pos, "COLLECT_FERT", {}))

        if yield_units > 0:
            a_info = ANIMAL.get(animal_name, {})
            max_h = a_info.get("max_held", 4)
            urgency = 92 if yield_units >= max_h - 1 else 75
            tasks.append((urgency, pos, "HARVEST", {}))

    for pos, tile in structs_empty:
        if chosen_animal:
            expected_struct = ANIMAL[chosen_animal]["structure"]
            if tile.get("kind") == expected_struct:
                tasks.append((85, pos, "PLACE", {"animal": chosen_animal}))

    for pos in weeds:
        tasks.append((20, pos, "DIG", {}))

    tasks.sort(key=lambda t: -t[0])
    return tasks

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — WORKER SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

def _needs_item(task_type: str, extra: Dict) -> Tuple[bool, str, int]:
    if task_type == "FEED":
        return True, "WHEAT", 1
    if task_type == "FERTILIZE":
        return True, "FERTILIZER", 1
    if task_type == "PLACE":
        return True, extra.get("animal", ""), 1
    return False, "", 0

def _task_action(task_type: str, extra: Dict) -> List:
    if task_type == "WATER":    return ["WATER"]
    if task_type == "HARVEST":  return ["HARVEST"]
    if task_type == "FEED":     return ["FEED"]
    if task_type == "CARE":     return ["CARE"]
    if task_type == "COLLECT_FERT": return ["COLLECT_FERTILIZER"]
    if task_type == "FERTILIZE": return ["FERTILIZE"]
    if task_type == "DIG":      return ["DIG"]
    if task_type == "PLANT":    return ["PLANT", extra.get("crop", "CARROT")]
    if task_type == "BUILD":
        s = extra.get("structure", "PASTURE")
        return [f"BUILD_{s}"]
    if task_type == "PLACE":
        return ["PLACE", extra.get("animal", "")]
    return ["PASS"]

def compute_worker_action(w_pos: Tuple[int, int], w_inv: Dict,
                          target: Tuple[int, int], task_type: str,
                          extra: Dict) -> List:
    needs, item, qty = _needs_item(task_type, extra)

    if needs and w_inv.get(item, 0) < qty:
        if is_shed_adjacent(w_pos):
            return ["PICKUP", item, qty]
        else:
            shed_pos = nearest_shed_tile(w_pos)
            return [move_towards(w_pos, shed_pos)]

    if w_pos == target:
        return _task_action(task_type, extra)
    return [move_towards(w_pos, target)]

def estimate_task_turns(w_pos: Tuple[int, int], w_inv: Dict,
                        target: Tuple[int, int], task_type: str,
                        extra: Dict) -> int:
    needs, item, qty = _needs_item(task_type, extra)
    turns = 0
    if needs and w_inv.get(item, 0) < qty:
        shed = nearest_shed_tile(w_pos)
        turns += manhattan(w_pos, shed) + 1
        turns += manhattan(shed, target) + 1
    else:
        turns += manhattan(w_pos, target) + 1
    return max(1, turns)

def schedule_workers(workers: List[Tuple[int, int]],
                     inventories: List[Dict],
                     tasks: List[Tuple],
                     shed: Dict,
                     seeds: Dict) -> List[List]:
    n = len(workers)
    actions = [["PASS"]] * n
    assigned_workers = set()
    assigned_task_keys = set()

    avail_shed = {k: int(v) for k, v in shed.items()}
    avail_seeds = {k: int(v) for k, v in seeds.items()}

    for priority, pos, task_type, extra in tasks:
        if len(assigned_workers) >= n:
            break

        task_key = (pos, task_type)
        if task_key in assigned_task_keys:
            continue

        if task_type == "PLANT":
            crop = extra.get("crop", "")
            if avail_seeds.get(crop, 0) <= 0:
                continue

        needs, item, qty = _needs_item(task_type, extra)

        best_w = -1
        best_cost = 999999
        for w in range(n):
            if w in assigned_workers:
                continue
            cost = estimate_task_turns(workers[w], inventories[w], pos, task_type, extra)
            if cost < best_cost:
                best_cost = cost
                best_w = w

        if best_w < 0:
            continue

        if needs and inventories[best_w].get(item, 0) < qty:
            if avail_shed.get(item, 0) < qty:
                continue
            avail_shed[item] -= qty

        if task_type == "PLANT":
            avail_seeds[extra.get("crop", "")] -= 1

        remaining_turns_today = TURNS_PER_DAY - 1
        if best_cost > remaining_turns_today and priority < 100:
            continue

        action = compute_worker_action(workers[best_w], inventories[best_w],
                                       pos, task_type, extra)
        actions[best_w] = action
        assigned_workers.add(best_w)
        assigned_task_keys.add(task_key)

    return actions

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MARKET ORDER GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_market_orders(day: int, hour: int, money: float,
                           shed: Dict, seeds: Dict, market_inv: Dict,
                           market_prices: Dict, shops: List[str],
                           me: Dict, chosen_crop: str,
                           chosen_animal: Optional[str],
                           target_animal_count: int,
                           total_tasks: int) -> List[List]:
    orders: List[List] = []
    remaining_money = money

    tiles_data = me.get("tiles", [])
    _, _, animal_tiles, structs_empty, _ = scan_tiles(tiles_data)
    current_animals = len(animal_tiles)
    hires_today = me.get("hires_today", 0)
    n_unlocked = len(me.get("unlocked_quadrants", ["NW"]))

    shed_total = sum(int(v) for v in shed.values())
    remaining_days = max(1, 30 - day)

    feed_reserve = current_animals * remaining_days + current_animals
    sellable_wheat = max(0, int(shed.get("WHEAT", 0)) - feed_reserve)

    sell_candidates = []
    for product, qty_raw in shed.items():
        qty = int(qty_raw)
        if qty <= 0 or product not in MP:
            continue
        if product == "WHEAT":
            qty = sellable_wheat
            if qty <= 0:
                continue
        price = compute_price(product, market_inv.get(product, 10000))
        base = MP[product]["base"]

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
        if len(orders) >= MAX_MARKET_ORDERS - 2:
            break
        orders.append(["SELL", product, sell_qty])

    if hour == 0 or (hour <= 2 and hires_today == 0):
        n_hires = optimal_hire_count(total_tasks, hires_today, remaining_money)
        for _ in range(n_hires):
            if len(orders) >= MAX_MARKET_ORDERS:
                break
            cost = fib(hires_today)
            if remaining_money >= cost:
                orders.append(["HIRE"])
                remaining_money -= cost
                hires_today += 1

    current_seeds = int(seeds.get(chosen_crop, 0))
    empty_count = len([1 for row in tiles_data for t in row if t is None])
    if current_seeds < max(3, empty_count) and day < 29 and len(orders) < MAX_MARKET_ORDERS:
        want = min(20, max(5, empty_count - current_seeds))
        cost = want * CROP[chosen_crop]["seed"]
        if remaining_money >= cost + 300:
            orders.append(["BUY_SEED", chosen_crop, want])
            remaining_money -= cost

    if current_animals > 0 and len(orders) < MAX_MARKET_ORDERS:
        current_wheat = int(shed.get("WHEAT", 0))
        target_wheat = min(80, current_animals * max(2, min(5, remaining_days)))
        wheat_deficit = max(0, target_wheat - current_wheat)
        if wheat_deficit > 0:
            wheat_buy_price = compute_price("WHEAT", market_inv.get("WHEAT", 10000))
            cost = wheat_deficit * wheat_buy_price
            if remaining_money >= cost + 200:
                orders.append(["BUY_PRODUCT", "WHEAT", wheat_deficit])
                remaining_money -= cost

    # 5. BUY_ANIMAL (AFFORDABILITY-SCALED, NO OVERBUYING)
    if chosen_animal and len(orders) < MAX_MARKET_ORDERS:
        a_info = ANIMAL[chosen_animal]
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

    if len(orders) < MAX_MARKET_ORDERS:
        best_npv_day = crop_npv(chosen_crop, day, market_inv, shops) / max(1, CROP[chosen_crop]["max_day"])
        if should_buy_land(remaining_money, n_unlocked, day, best_npv_day):
            orders.append(["BUY_LAND"])
            land_cost = {1: 1000, 2: 2000, 3: 4000}.get(n_unlocked, 0)
            remaining_money -= land_cost

    return orders[:MAX_MARKET_ORDERS]

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — OPPONENT MODEL (lightweight)
# ═══════════════════════════════════════════════════════════════════════════════

def estimate_opponent_pressure(opp_tiles, day: int) -> Dict[str, int]:
    production = {}
    for y, row in enumerate(opp_tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT":
                crop = t.get("crop", "")
                if crop in CROP:
                    c = CROP[crop]
                    age = day - t.get("planted_day", day)
                    harvest_age = c["max_day"]
                    if age + (harvest_age - age) <= 30:
                        y_est = crop_yield_unfert(crop)
                        production[crop] = production.get(crop, 0) + y_est
            elif t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                animal = t["animal"]
                if animal in ANIMAL:
                    product = ANIMAL[animal]["product"]
                    remaining = max(1, 30 - day)
                    est = remaining // ANIMAL[animal]["interval"]
                    production[product] = production.get(product, 0) + est
    return production

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — STRATEGIC DECISIONS
# ═══════════════════════════════════════════════════════════════════════════════

def strategic_evaluate(day: int, money: float, market_inv: Dict, shops: List[str],
                       tiles, n_unlocked: int,
                       opp_tiles) -> Dict:
    crop = best_crop_for_day(day, market_inv, shops)
    animal = best_animal_for_day(day, market_inv, shops)

    _, _, existing_animals, _, _ = scan_tiles(tiles)
    current_n = len(existing_animals)
    target_n = current_n

    if animal:
        wheat_price = compute_price("WHEAT", market_inv.get("WHEAT", 10000))
        a_npv = animal_npv(animal, day, market_inv, shops, wheat_price)
        c_npv = crop_npv(crop, day, market_inv, shops)
        if a_npv > c_npv and a_npv > 0:
            empty_count = len([1 for row in tiles for t in row if t is None])
            max_new = min(empty_count // 2, 4)
            target_n = current_n + max_new
        elif a_npv > 0:
            target_n = max(current_n, min(current_n + 2, 6))

    opp_pressure = estimate_opponent_pressure(opp_tiles, day)

    return {
        "crop": crop,
        "animal": animal,
        "target_animals": target_n,
        "opp_pressure": opp_pressure,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — AGENT ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

_P: Dict[str, Any] = {}

def agent(obs: Dict[str, Any]) -> Dict[str, Any]:
    global _P

    player = int(obs["player"])
    me = obs["farms"][player]
    opp = obs["farms"][1 - player]
    private = obs["private"]
    market = obs["market"]
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    money = float(me.get("money", 0))
    shed = {k: int(v) for k, v in private.get("shed", {}).items()}
    seeds = {k: int(v) for k, v in private.get("seeds", {}).items()}
    inventories_raw = private.get("inventories", [{}])
    market_inv = {k: int(v) for k, v in market.get("inventory", {}).items()}
    market_prices = {k: int(v) for k, v in market.get("prices", {}).items()}
    shops = obs.get("town", {}).get("unlocked_shops", [])
    tiles = me.get("tiles", [])
    opp_tiles = opp.get("tiles", [])
    n_unlocked = len(me.get("unlocked_quadrants", ["NW"]))

    farmer_pos = tuple(me.get("farmer", [4, 4]))
    hand_positions = [tuple(h) for h in me.get("hands", [])]
    workers = [farmer_pos] + hand_positions

    inventories = []
    for i in range(len(workers)):
        if i < len(inventories_raw) and isinstance(inventories_raw[i], dict):
            inventories.append({k: int(v) for k, v in inventories_raw[i].items()})
        else:
            inventories.append({})

    if hour == 0 or "plan" not in _P or _P.get("plan_day", -1) != day:
        plan = strategic_evaluate(day, money, market_inv, shops, tiles,
                                   n_unlocked, opp_tiles)
        _P["plan"] = plan
        _P["plan_day"] = day
    plan = _P["plan"]

    chosen_crop = plan["crop"]
    chosen_animal = plan.get("animal")
    target_animals = plan.get("target_animals", 0)

    tasks = generate_tasks(day, hour, tiles, shed, seeds, market_inv, shops,
                           chosen_crop, chosen_animal, target_animals)

    worker_actions = schedule_workers(workers, inventories, tasks, shed, seeds)

    market_orders = generate_market_orders(
        day, hour, money, shed, seeds, market_inv, market_prices, shops,
        me, chosen_crop, chosen_animal, target_animals, len(tasks)
    )

    farmer_action = worker_actions[0] if worker_actions else ["PASS"]
    hand_actions = worker_actions[1:] if len(worker_actions) > 1 else []

    return {
        "farmer": farmer_action,
        "hands": hand_actions,
        "market": market_orders,
    }
