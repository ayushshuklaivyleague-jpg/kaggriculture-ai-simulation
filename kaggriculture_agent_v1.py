from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Kaggriculture V1: market-aware, worker-parallel heuristic.
# Designed from the competition specification supplied in the prompt.
# No third-party dependencies.

BASE_PRICE = {
    "WHEAT": 25,
    "CARROT": 35,
    "TOMATO": 60,
    "STRAWBERRY": 120,
    "MELON": 250,
    "EGG": 50,
    "MILK": 160,
    "WOOL": 200,
    "FERTILIZER": 100,
}

I0 = 10_000
T = {
    "WHEAT": 400,
    "CARROT": 450,
    "TOMATO": 200,
    "STRAWBERRY": 100,
    "MELON": 300,
    "EGG": 332,
    "MILK": 122,
    "WOOL": 105,
    "FERTILIZER": 200,
}

CROP = {
    "WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 4, "yield_day": 0.80},
    "CARROT": {"seed": 20, "first": 2, "max_day": 3, "max_yield": 3, "yield_day": 0.75},
    "TOMATO": {"seed": 50, "first": 8, "max_day": 11, "max_yield": 4, "yield_day": 0.33},
    "STRAWBERRY": {"seed": 100, "first": 10, "max_day": 16, "max_yield": 4, "yield_day": 0.24},
    "MELON": {"seed": 80, "first": 10, "max_day": 10, "max_yield": 6, "yield_day": 0.55},
}

ANIMAL = {
    "GOOSE": {"cost": 300, "product": "EGG", "interval": 1, "structure": "COOP"},
    "COW": {"cost": 400, "product": "MILK", "interval": 2, "structure": "PASTURE"},
    "SHEEP": {"cost": 500, "product": "WOOL", "interval": 3, "structure": "PASTURE"},
}

SHOP_PRODUCTS = {
    "BAKERY": ["EGG", "WHEAT"],
    "PIZZA SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN STORE": ["WOOL"],
    "ICE CREAM SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET CAFE": ["CARROT"],
    "SMOOTHIE SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}


def price_pressure(product: str, market: Dict[str, Any]) -> float:
    """Higher = healthier market for additional production/sales."""
    inv = float(market.get("inventory", {}).get(product, I0))
    price = float(market.get("prices", {}).get(product, BASE_PRICE[product]))
    pressure = (inv - I0) / max(1, T[product])

    factor = 1.0
    if pressure > 1.0:
        factor *= 0.10
    elif pressure > 0.50:
        factor *= 0.35
    elif pressure > 0.25:
        factor *= 0.65

    if price < BASE_PRICE[product] * 0.30:
        factor *= 0.35
    elif price < BASE_PRICE[product] * 0.60:
        factor *= 0.65
    elif price > BASE_PRICE[product] * 1.05:
        factor *= 1.10

    return max(0.05, factor)


def demand_per_day(product: str, obs: Dict[str, Any]) -> int:
    # Town center consumes one/day for every non-fertilizer product.
    if product == "FERTILIZER":
        return 0
    shops = obs.get("town", {}).get("unlocked_shops", [])
    demand = 1
    for shop in shops:
        if product in SHOP_PRODUCTS.get(shop, []):
            # Default sell interval is 4 turns, i.e. six units/day.
            demand += 6
            # Single-product shops consume 2x; PET CAFE is the documented example.
            if shop == "PET CAFE" and product == "CARROT":
                demand += 6
            if shop == "YARN STORE" and product == "WOOL":
                demand += 6
    return demand


def choose_crop(obs: Dict[str, Any], me: Dict[str, Any]) -> str:
    day = int(obs.get("day", 0))
    remaining = 30 - day
    market = obs["market"]

    candidates: List[Tuple[float, str]] = []
    for name, info in CROP.items():
        if remaining < info["first"] + 1:
            continue
        price = market.get("prices", {}).get(name, BASE_PRICE[name])
        pressure_factor = price_pressure(name, market)
        # Approximate daily profit on the field, including seed amortization.
        value = info["yield_day"] * price - info["seed"] / max(1, info["max_day"])
        # Early bootstrap strongly favors fast crops; midgame favors high-value crops.
        if day <= 3:
            speed_bonus = 1.45 if name == "CARROT" else 1.0
        elif day >= 20:
            speed_bonus = 1.60 if name == "CARROT" else 0.95
        else:
            speed_bonus = 1.15 if name == "MELON" else 1.0
        # Add a small demand-aware bonus without letting demand dominate price/ROI.
        demand_bonus = 1.0 + min(0.35, demand_per_day(name, obs) / 20.0)
        score = value * pressure_factor * speed_bonus * demand_bonus
        candidates.append((score, name))

    if not candidates:
        return "CARROT"
    return max(candidates)[1]


def choose_animal(obs: Dict[str, Any]) -> str:
    market = obs["market"]
    wheat_price = market.get("prices", {}).get("WHEAT", BASE_PRICE["WHEAT"])
    scores: List[Tuple[float, str]] = []

    for name, info in ANIMAL.items():
        product = info["product"]
        interval = info["interval"]
        price = market.get("prices", {}).get(product, BASE_PRICE[product])
        fertilizer_price = market.get("prices", {}).get("FERTILIZER", BASE_PRICE["FERTILIZER"])
        # With daily feed + care, a production event has roughly 1 + interval units.
        product_per_day = (1.0 + interval) / interval
        net = product_per_day * price + fertilizer_price - wheat_price
        factor = price_pressure(product, market)
        # Late game: prefer faster payback because long-cycle animals may not yield.
        day = int(obs.get("day", 0))
        remaining = 30 - day
        if remaining < info["interval"] + 2:
            factor *= 0.25
        if remaining < info["interval"] + 1:
            factor *= 0.05
        scores.append((net * factor, name))

    return max(scores)[1]


def count_animals(me: Dict[str, Any]) -> Dict[str, int]:
    counts = {"GOOSE": 0, "COW": 0, "SHEEP": 0}
    for row in me.get("tiles", []):
        for tile in row:
            if isinstance(tile, dict) and tile.get("kind") in ("COOP", "PASTURE"):
                animal = tile.get("animal")
                if animal in counts:
                    counts[animal] += 1
    return counts


def unlocked_empty_tiles(me: Dict[str, Any]) -> List[Tuple[int, int]]:
    out = []
    for y, row in enumerate(me.get("tiles", [])):
        for x, tile in enumerate(row):
            if tile is None:
                out.append((x, y))
    return out


def next_land_cost(me: Dict[str, Any]) -> int | None:
    unlocked = len(me.get("unlocked_quadrants", []))
    if unlocked >= 4:
        return None
    return {1: 1000, 2: 2000, 3: 4000}.get(unlocked, None)


def make_market_orders(obs: Dict[str, Any], me: Dict[str, Any], private: Dict[str, Any], crop: str, animal: str) -> List[List[Any]]:
    orders: List[List[Any]] = []
    money = float(me.get("money", 0))
    day = int(obs.get("day", 0))
    market = obs["market"]
    shed = private.get("shed", {})
    seeds = private.get("seeds", {})
    counts = count_animals(me)
    total_animals = sum(counts.values())

    # Target animal count ramps after the early bootstrap. Stop buying late in the season.
    if day < 4:
        target_animals = 0
    elif day < 8:
        target_animals = 4
    elif day < 12:
        target_animals = 6
    elif day < 16:
        target_animals = 8
    elif day < 20:
        target_animals = 10
    else:
        target_animals = total_animals

    animal_needed = max(0, target_animals - total_animals)
    empty_tiles = len(unlocked_empty_tiles(me))
    animal_room = empty_tiles

    # Decide which optional market actions are needed today before hiring workers.
    want_land = False
    land_cost = next_land_cost(me)
    if land_cost is not None and money >= land_cost + 1200:
        want_land = True

    wheat_needed = 0
    if total_animals:
        current_wheat = int(shed.get("WHEAT", 0))
        # Keep roughly two days of feed in the shed without overflowing it.
        target_wheat = min(80, total_animals * 2)
        wheat_needed = max(0, target_wheat - current_wheat)

    want_wheat = wheat_needed > 0 and money >= wheat_needed * market.get("prices", {}).get("WHEAT", 25) + 200

    seed_qty = int(seeds.get(crop, 0))
    want_seed = seed_qty < 8 and empty_tiles > 0 and day < 29
    if want_seed:
        desired = min(25, max(10, empty_tiles))
        seed_cost = CROP[crop]["seed"] * desired
        if money < seed_cost + 500:
            want_seed = False

    # Sell pressure: keep the shed from filling and prefer the best-priced available product.
    sale_candidates = []
    for product, qty in shed.items():
        if qty <= 0 or product not in BASE_PRICE or product == "WHEAT":
            continue
        current_price = market.get("prices", {}).get(product, BASE_PRICE[product])
        factor = price_pressure(product, market)
        # Always clear inventory if it is getting close to the 100-item shed cap.
        urgency = 2.0 if sum(int(v) for v in shed.values()) >= 80 else 1.0
        score = current_price * factor * urgency
        if current_price >= BASE_PRICE[product] * 0.40 or urgency > 1:
            sale_candidates.append((score, product))
    sale_product = max(sale_candidates)[1] if sale_candidates else None

    extra_needed = sum(bool(x) for x in (want_land, want_wheat, animal_needed > 0 and animal_room > 0, want_seed, sale_product))
    hires = 5 if extra_needed >= 4 else 6
    hires = max(0, min(6, hires))
    for _ in range(hires):
        orders.append(["HIRE"])

    # Preserve room in the 10-order market queue for the most important actions.
    if want_land and len(orders) < 10:
        orders.append(["BUY_LAND"])
        money -= land_cost or 0

    if want_wheat and len(orders) < 10:
        orders.append(["BUY_PRODUCT", "WHEAT", wheat_needed])

    if animal_needed > 0 and animal_room > 0 and len(orders) < 10:
        species = animal
        unit_cost = ANIMAL[species]["cost"]
        reserve = 800
        affordable = max(0, int((money - reserve) // unit_cost))
        buy_n = min(animal_needed, animal_room, affordable, 4)
        if buy_n > 0:
            orders.append(["BUY_ANIMAL", species, buy_n])
            money -= buy_n * unit_cost

    if want_seed and len(orders) < 10:
        desired = min(25, max(10, empty_tiles))
        affordable_qty = max(0, int((money - 300) // CROP[crop]["seed"]))
        buy_n = min(desired, affordable_qty)
        if buy_n > 0:
            orders.append(["BUY_SEED", crop, buy_n])

    if sale_product and len(orders) < 10:
        sell_n = min(10, int(shed.get(sale_product, 0)))
        if sell_n > 0:
            orders.append(["SELL", sale_product, sell_n])

    return orders[:10]


def build_tasks(obs: Dict[str, Any], me: Dict[str, Any], private: Dict[str, Any], crop: str, animal: str) -> List[Tuple[int, Tuple[int, int], List[str]]]:
    tasks: List[Tuple[int, Tuple[int, int], List[str]]] = []
    shed = private.get("shed", {})
    animal_info = ANIMAL[animal]

    # How many new structures should we prepare for the chosen animal?
    counts = count_animals(me)
    total_animals = sum(counts.values())
    day = int(obs.get("day", 0))
    if day < 4:
        target_animals = total_animals
    elif day < 8:
        target_animals = 4
    elif day < 12:
        target_animals = 6
    elif day < 16:
        target_animals = 8
    elif day < 20:
        target_animals = 10
    else:
        target_animals = total_animals

    needed = max(0, target_animals - total_animals)
    empty = unlocked_empty_tiles(me)
    # Prefer building a small number of structures before planting the remaining empty land.
    build_slots = set(empty[: min(needed, len(empty))])

    for y, row in enumerate(me.get("tiles", [])):
        for x, tile in enumerate(row):
            pos = (x, y)
            if tile is None:
                if pos in build_slots:
                    tasks.append((115, pos, [f"BUILD_{animal_info['structure']}"]))
                elif private.get("seeds", {}).get(crop, 0) > 0:
                    tasks.append((35, pos, ["PLANT", crop]))
                continue

            if isinstance(tile, str):
                continue

            if tile.get("kind") == "PLANT":
                crop_name = tile.get("crop")
                if not crop_name:
                    continue
                age = day - int(tile.get("planted_day", day))
                if not tile.get("watered_today", False):
                    tasks.append((110, pos, ["WATER"]))
                    continue

                max_yield = CROP.get(crop_name, {}).get("max_yield", 1)
                yield_units = int(tile.get("yield_units", 0))

                # Harvest at full/near-full output. This avoids prematurely removing ongoing crops.
                if yield_units >= max_yield or age >= CROP.get(crop_name, {}).get("max_day", 0):
                    tasks.append((105, pos, ["HARVEST"]))
                    continue

                # Melon fertilizer is especially efficient: fertilizing around the bonus window
                # can hit the six-unit cap quickly. Do it only once and when fertilizer exists.
                if (
                    crop_name == "MELON"
                    and 6 <= age <= 8
                    and int(shed.get("FERTILIZER", 0)) > 0
                    and int(tile.get("fertilized_until_day", -1)) < 0
                ):
                    tasks.append((95, pos, ["FERTILIZE"]))
                    continue

            elif tile.get("kind") in ("COOP", "PASTURE"):
                occupant = tile.get("animal")
                if occupant is None:
                    # Place the best purchased animal into an empty matching structure.
                    available = int(shed.get(animal, 0))
                    if available > 0 and tile.get("kind") == animal_info["structure"]:
                        tasks.append((120, pos, ["PLACE", animal]))
                    continue

                # Animal maintenance is deliberately above planting.
                if tile.get("fertilizer_available", False):
                    tasks.append((118, pos, ["COLLECT_FERTILIZER"]))
                    continue
                if not tile.get("fed_today", False):
                    tasks.append((117, pos, ["FEED"]))
                    continue
                if not tile.get("cared_today", False):
                    tasks.append((116, pos, ["CARE"]))
                    continue
                if int(tile.get("yield_units", 0)) > 0:
                    tasks.append((106, pos, ["HARVEST"]))
                    continue

    return tasks


def move_towards(pos: Tuple[int, int], target: Tuple[int, int]) -> str:
    x, y = pos
    tx, ty = target
    if x < tx:
        return "EAST"
    if x > tx:
        return "WEST"
    if y < ty:
        return "SOUTH"
    if y > ty:
        return "NORTH"
    return "PASS"


def assign_actions(units: List[Tuple[int, int]], tasks: List[Tuple[int, Tuple[int, int], List[str]]]) -> List[List[str] | List[str]]:
    # Greedy bipartite assignment: high priority first, then nearest unit.
    assigned: List[List[str]] = [["PASS"] for _ in units]
    unused_units = set(range(len(units)))
    remaining = sorted(tasks, key=lambda t: (-t[0], t[1][1], t[1][0]))

    for priority, target, action in remaining:
        if not unused_units:
            break
        # Priority dominates distance; among same priority choose nearest.
        idx = min(unused_units, key=lambda i: abs(units[i][0] - target[0]) + abs(units[i][1] - target[1]))
        dist = abs(units[idx][0] - target[0]) + abs(units[idx][1] - target[1])
        if dist == 0:
            assigned[idx] = action
        else:
            assigned[idx] = [move_towards(units[idx], target)]
        unused_units.remove(idx)

    return assigned


def agent(obs: Dict[str, Any]) -> Dict[str, Any]:
    player = int(obs["player"])
    me = obs["farms"][player]
    private = obs["private"]

    crop = choose_crop(obs, me)
    animal = choose_animal(obs)

    market_orders = make_market_orders(obs, me, private, crop, animal)
    tasks = build_tasks(obs, me, private, crop, animal)

    units: List[Tuple[int, int]] = [tuple(me.get("farmer", [0, 0]))]
    units.extend(tuple(p) for p in me.get("hands", []))
    actions = assign_actions(units, tasks)

    return {
        "farmer": actions[0] if actions else ["PASS"],
        "hands": actions[1:],
        "market": market_orders,
    }


if __name__ == "__main__":
    # Basic import/syntax check only. Kaggriculture itself is not bundled in this environment.
    print("Kaggriculture V1 agent loaded successfully.")
