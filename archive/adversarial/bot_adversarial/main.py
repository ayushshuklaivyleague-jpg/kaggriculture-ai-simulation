"""Adversarial Market Predator: RIVAL_SHADOW_TAPE + WAR_CHEST + TERMINAL_AMBUSH + SLOT_SNIPER + FEED_SQUEEZE.

Key Enhancements:
1. War Chest accumulation starts on Day 26 (step 624), preserving 100% of early-game and mid-game capital for farm expansion.
2. Live Market Weapon Evaluator: chooses the target asset dynamically based on real-time market price (P >= 40) and glut drop delta.
3. Surgical Slot Sniper: at terminal liquidation (steps 710 and 713), injects the ambush order into Slot 0 to pre-crater the market depth before the opponent's order in Slot 3..7 quotes its first unit.
4. Asymmetric Safety Gate: aborts and falls back to optimal liquidation if enemy quantity is not significantly greater than our sacrifice.
"""

import math
import copy
import core_engine

# Target candidate products with steep glut curves
PREMIUM_WEAPONS = ("WOOL", "MELON", "STRAWBERRY", "MILK")

MARKET_DEFAULTS = {
    "WHEAT":      {"base": 25,  "I0": 10000, "T": 400, "below_func": "linear", "below_target": 0.8, "above_func": "log",    "above_target": 0.2},
    "CARROT":     {"base": 35,  "I0": 10000, "T": 450, "below_func": "linear", "below_target": 1.0, "above_func": "sqrt",   "above_target": 0.7},
    "TOMATO":     {"base": 60,  "I0": 10000, "T": 200, "below_func": "sqrt",   "below_target": 0.4, "above_func": "sqrt",   "above_target": 0.6},
    "STRAWBERRY": {"base": 120, "I0": 10000, "T": 100, "below_func": "sqrt",   "below_target": 0.7, "above_func": "linear", "above_target": 1.0},
    "MELON":      {"base": 250, "I0": 10000, "T": 300, "below_func": "log",    "below_target": 0.2, "above_func": "sq",     "above_target": 3.6},
    "EGG":        {"base": 50,  "I0": 10000, "T": 332, "below_func": "sq",     "below_target": 0.4, "above_func": "log",    "above_target": 0.2},
    "MILK":       {"base": 160, "I0": 10000, "T": 122, "below_func": "sq",     "below_target": 0.6, "above_func": "linear", "above_target": 1.0},
    "WOOL":       {"base": 200, "I0": 10000, "T": 105, "below_func": "log",    "below_target": 0.2, "above_func": "sq",     "above_target": 2.2},
    "FERTILIZER": {"base": 100, "I0": 10000, "T": 200, "below_func": "linear", "below_target": 0.4, "above_func": "linear", "above_target": 0.4},
}

SHOPS_CONSUMPTION = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA_SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE":     ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE":       ["CARROT"],
    "SMOOTHIE_SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

def _shape_val(func, x, T):
    if func == "linear":
        return x
    if func == "sq":
        return x * x / T if T else x * x
    if func == "sqrt":
        return math.sqrt(x * T) if T and x >= 0 else math.sqrt(max(0, x))
    if func == "log":
        return T * math.log(1.0 + x / T) if T else math.log(1.0 + x)
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x

def calc_market_price(item, inventory, params=None):
    p = (params or MARKET_DEFAULTS).get(item, MARKET_DEFAULTS.get(item))
    if not p:
        return 1
    base = p["base"]
    I0 = p["I0"]
    T = p["T"]
    if inventory < I0:
        f = p["below_func"]
        amp = p["below_target"] * base / _shape_val(f, T, T)
        price = base + amp * _shape_val(f, I0 - inventory, T)
    else:
        f = p["above_func"]
        amp = p["above_target"] * base / _shape_val(f, T, T)
        price = base - amp * _shape_val(f, inventory - I0, T)
    return max(1, int(round(price)))


class RivalShadowTape:
    """Continuous behavioral signature and telemetry tracker."""
    def __init__(self, seat):
        self.seat = seat
        self.rival_seat = 1 - seat
        self.inferred_shed = {k: 0 for k in MARKET_DEFAULTS}
        self.harvest_counts = {k: 0 for k in MARKET_DEFAULTS}
        self.observed_sales = {k: 0 for k in MARKET_DEFAULTS}
        self.last_tiles = {}
        self.last_market_inv = {}
        self.archetype = "UNKNOWN"
        self.is_2945_lineage = False
        self.confidence = 0.0

    def update(self, obs, own_committed_sales):
        step = obs["step"]
        rival_farm = obs["farms"][self.rival_seat]
        market = obs["market"]
        market_inv = market["inventory"]
        shops = (obs.get("town") or {}).get("unlocked_shops", [])

        # 1. Scan rival tiles
        cows = 0
        sheep = 0
        geese = 0
        melons = 0
        strawberries = 0
        tomatoes = 0
        carrots = 0
        wheat = 0
        current_tiles = {}

        for y, row in enumerate(rival_farm["tiles"]):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict):
                    continue
                pos = (x, y)
                animal = tile.get("animal")
                crop = tile.get("crop")
                yield_u = int(tile.get("yield_units", 0))

                if animal == "COW": cows += 1
                elif animal == "SHEEP": sheep += 1
                elif animal == "GOOSE": geese += 1

                if crop == "MELON": melons += 1
                elif crop == "STRAWBERRY": strawberries += 1
                elif crop == "TOMATO": tomatoes += 1
                elif crop == "CARROT": carrots += 1
                elif crop == "WHEAT": wheat += 1

                current_tiles[pos] = {
                    "animal": animal,
                    "crop": crop,
                    "yield": yield_u,
                    "day": tile.get("placed_day", tile.get("planted_day", 0))
                }

        # 2. Track harvests since last step
        if self.last_tiles:
            for pos, old_info in self.last_tiles.items():
                new_info = current_tiles.get(pos)
                old_y = old_info["yield"]
                if old_y <= 0:
                    continue
                product = None
                if old_info["animal"] == "COW": product = "MILK"
                elif old_info["animal"] == "SHEEP": product = "WOOL"
                elif old_info["animal"] == "GOOSE": product = "EGG"
                elif old_info["crop"] in PREMIUM_WEAPONS: product = old_info["crop"]
                
                if product:
                    got = 0
                    if new_info is None or new_info.get("day") != old_info.get("day"):
                        got = old_y
                    elif new_info["yield"] < old_y:
                        got = old_y - new_info["yield"]
                    if got > 0:
                        self.harvest_counts[product] += got
                        self.inferred_shed[product] += got

        # 3. Track market sales
        if self.last_market_inv:
            town_draw = {}
            if step % 4 == 0:
                for shop in shops:
                    prods = SHOPS_CONSUMPTION.get(shop, [])
                    for p in prods:
                        town_draw[p] = town_draw.get(p, 0) + (2 if len(prods) == 1 else 1)
            if step % 24 == 0:
                for p in MARKET_DEFAULTS:
                    if p != "FERTILIZER":
                        town_draw[p] = town_draw.get(p, 0) + 1

            for p, cur_inv in market_inv.items():
                prev_inv = self.last_market_inv.get(p, cur_inv)
                draw = town_draw.get(p, 0)
                own_sold = own_committed_sales.get(p, 0)
                delta_inv = cur_inv - prev_inv
                rival_sold = max(0, delta_inv + draw - own_sold)
                if rival_sold > 0:
                    self.observed_sales[p] += rival_sold
                    self.inferred_shed[p] = max(0, self.inferred_shed.get(p, 0) - rival_sold)

        self.last_tiles = current_tiles
        self.last_market_inv = dict(market_inv)

        # 4. Fingerprint Classification
        if step >= 96:
            tile_24 = rival_farm["tiles"][4][2] if len(rival_farm["tiles"]) > 4 else None
            is_2945 = isinstance(tile_24, dict) and (tile_24.get("kind") == "PASTURE" or tile_24.get("crop") == "WHEAT")
            self.is_2945_lineage = is_2945

            if cows + sheep >= 5:
                self.archetype = "HERD_META"
                self.confidence = 0.90
            elif melons >= 6:
                self.archetype = "MELON_META"
                self.confidence = 0.90
            elif strawberries >= 8:
                self.archetype = "STRAWBERRY_META"
                self.confidence = 0.85
            elif is_2945:
                self.archetype = "2945_CHASSIS"
                self.confidence = 0.95
            else:
                self.archetype = "BALANCED"
                self.confidence = 0.60

    def evaluate_attack_targets(self, obs, our_shed):
        """Evaluates every weapon candidate based on live price and enemy exposure."""
        market_prices = obs["market"]["prices"]
        market_inv = obs["market"]["inventory"]
        rival_farm = obs["farms"][self.rival_seat]

        cows = sum(1 for row in rival_farm["tiles"] for t in row if isinstance(t, dict) and t.get("animal") == "COW")
        sheep = sum(1 for row in rival_farm["tiles"] for t in row if isinstance(t, dict) and t.get("animal") == "SHEEP")
        melons = sum(1 for row in rival_farm["tiles"] for t in row if isinstance(t, dict) and t.get("crop") == "MELON")
        strawberries = sum(1 for row in rival_farm["tiles"] for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")

        candidates = {}
        for p in PREMIUM_WEAPONS:
            price = market_prices.get(p, 0)
            if price < 40:
                continue
            
            if p == "WOOL":
                q_enemy = sheep * 6 + self.inferred_shed.get("WOOL", 0)
            elif p == "MELON":
                q_enemy = melons * 25 + self.inferred_shed.get("MELON", 0)
            elif p == "STRAWBERRY":
                q_enemy = strawberries * 8 + self.inferred_shed.get("STRAWBERRY", 0)
            elif p == "MILK":
                q_enemy = cows * 8 + self.inferred_shed.get("MILK", 0)
            else:
                q_enemy = 0

            our_stock = our_shed.get(p, 0)
            cur_inv = market_inv.get(p, 10000)
            p_b = calc_market_price(p, cur_inv)
            p_a = calc_market_price(p, cur_inv + max(our_stock, 5))
            delta_p = p_b - p_a

            net_adv = (q_enemy - our_stock) * delta_p
            candidates[p] = {
                "product": p,
                "price": price,
                "q_enemy": q_enemy,
                "our_stock": our_stock,
                "delta_p": delta_p,
                "net_adv": net_adv,
            }

        if not candidates:
            return None
        # Best weapon has highest net advantage with high delta_p
        best_p = max(candidates, key=lambda k: (candidates[k]["net_adv"], candidates[k]["price"]))
        return candidates[best_p]


_AMBUSH_STATE = {}
_AMBUSH_REPORT = {
    "war_chest_held": 0,
    "feed_squeeze_buys": 0,
    "ambush_fired": 0,
    "ambush_aborted": 0,
    "predicted_damage": 0,
}

_BASE_AGENT = core_engine.agent

def agent(observation, configuration=None):
    seat = int(observation["player"])
    step = int(observation["step"])

    st = _AMBUSH_STATE.get(seat)
    if st is None or step <= st.get("step", -1):
        st = _AMBUSH_STATE[seat] = {
            "step": -1,
            "shadow_tape": RivalShadowTape(seat),
            "war_chest_item": None,
            "ambush_executed": False,
            "own_committed_sales": {},
        }
        if step == 0:
            for k in _AMBUSH_REPORT:
                _AMBUSH_REPORT[k] = 0

    st["step"] = step
    tape = st["shadow_tape"]
    tape.update(observation, st["own_committed_sales"])
    st["own_committed_sales"] = {}

    action = _BASE_AGENT(observation, configuration)
    if not isinstance(action, dict):
        return action

    market_orders = [list(o) for o in (action.get("market") or [])]
    private = observation["private"]
    shed = private["shed"]
    my_money = observation["farms"][seat]["money"]

    # 1. FEED SQUEEZE: If opponent is HERD_META and we have surplus capital
    if tape.archetype == "HERD_META" and 150 <= step < 580:
        wheat_price = observation["market"]["prices"].get("WHEAT", 25)
        if wheat_price <= 24 and my_money > 2200 and len(market_orders) < 10:
            if not any(o[0] == "BUY_PRODUCT" and o[1] == "WHEAT" for o in market_orders):
                market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
                _AMBUSH_REPORT["feed_squeeze_buys"] += 4

    # 2. LATE-SEASON WAR CHEST ACCUMULATION (Days 26 to 28, steps 624 to 708)
    # Only withhold inventory late in the season to prevent early capital starvation
    best_target = tape.evaluate_attack_targets(observation, shed)
    if 624 <= step < 708 and best_target is not None:
        target_product = best_target["product"]
        st["war_chest_item"] = target_product
        current_held = shed.get(target_product, 0)
        _AMBUSH_REPORT["war_chest_held"] = current_held

        # Withhold a moderate batch (up to 15-20 units)
        war_quota = 18
        new_orders = []
        for o in market_orders:
            if len(o) >= 3 and o[0] == "SELL" and o[1] == target_product:
                sell_amt = int(o[2])
                allow_sell = max(0, current_held - war_quota)
                if allow_sell > 0:
                    new_orders.append(["SELL", target_product, min(sell_amt, allow_sell)])
            else:
                new_orders.append(o)
        market_orders = new_orders

    # 3. TERMINAL AMBUSH & SLOT SNIPER (Steps 710 to 714)
    if 710 <= step <= 714 and not st["ambush_executed"] and best_target is not None:
        target_product = best_target["product"]
        our_stock = shed.get(target_product, 0)
        enemy_q = best_target["q_enemy"]
        delta_p = best_target["delta_p"]
        net_adv = best_target["net_adv"]

        # Mathematical Trigger Gate:
        # Require genuine asymmetric advantage and meaningful damage
        gate_passed = (
            enemy_q >= 1.2 * our_stock and
            net_adv >= 1000 and
            delta_p >= 20 and
            our_stock >= 5
        )

        if gate_passed and step in (710, 713):
            # FIRE AMBUSH IN SLOT 0!
            # Front-runs the enemy's slot in the same turn or pre-craters prior to step 714
            st["ambush_executed"] = True
            _AMBUSH_REPORT["ambush_fired"] += 1
            _AMBUSH_REPORT["predicted_damage"] = int(net_adv)

            ambush_order = ["SELL", target_product, our_stock]
            market_orders = [o for o in market_orders if not (len(o) >= 3 and o[0] == "SELL" and o[1] == target_product)]
            market_orders.insert(0, ambush_order)
            market_orders = market_orders[:10]

    # 4. SAFETY ABORT: At step 715+, if ambush was not fired or any residual stock remains, liquidate cleanly!
    if step >= 715:
        if not st["ambush_executed"]:
            _AMBUSH_REPORT["ambush_aborted"] = 1
        for p in PREMIUM_WEAPONS:
            rem = shed.get(p, 0)
            if rem > 0 and len(market_orders) < 10:
                if not any(o[0] == "SELL" and o[1] == p for o in market_orders):
                    market_orders.append(["SELL", p, rem])

    # Record committed sales for next step's deduction
    for o in market_orders:
        if len(o) >= 3 and o[0] == "SELL":
            st["own_committed_sales"][o[1]] = st["own_committed_sales"].get(o[1], 0) + int(o[2])

    action = dict(action)
    action["market"] = market_orders
    return action

agent.telemetry = _AMBUSH_REPORT
