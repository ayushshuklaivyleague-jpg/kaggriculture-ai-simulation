"""Test implementation of Phase B: State-Compatibility Guarded 3-Day Replanner.
"""
import copy
import json
import kaggle_environments
import main as base_module

# 1. Load routes profile
with open('routes_profile.json') as f:
    PROFILES = json.load(f)

# Shop demand definitions
SHOP_DEMANDS = {
    'BAKERY': {'WHEAT': 1, 'CARROT': 1},
    'BRUNCH_SPOT': {'CARROT': 1, 'EGG': 1, 'MILK': 1, 'STRAWBERRY': 1},
    'FARMERS_MARKET': {'CARROT': 1, 'TOMATO': 1, 'STRAWBERRY': 1, 'MELON': 1},
    'ICE_CREAM_SHOP': {'MILK': 1, 'STRAWBERRY': 1},
    'PET_CAFE': {'CARROT': 1, 'EGG': 1, 'MILK': 1},
    'PIZZA_SHOP': {'WHEAT': 1, 'TOMATO': 1},
    'SMOOTHIE_SHOP': {'CARROT': 1, 'STRAWBERRY': 1, 'MELON': 1},
    'YARN_STORE': {'WOOL': 2},
}

BASE_PRICES = {
    'WHEAT': 25, 'CARROT': 35, 'TOMATO': 45, 'STRAWBERRY': 60,
    'MELON': 100, 'EGG': 40, 'MILK': 60, 'WOOL': 80, 'FERTILIZER': 20
}

# Physical clusters: precomputed map of (land, sorted_animals) at steps 144, 216, 288
STEP_CLUSTERS = {}
for step in [144, 216, 288, 360, 432, 504, 576]:
    clusters = {}
    for r_id, tape in base_module._ROUTES.items():
        animals = {}
        land = 1
        for s in range(min(step, len(tape))):
            for o in tape[s].get('market', []):
                if not o: continue
                if o[0] == 'BUY_ANIMAL':
                    animals[o[1]] = animals.get(o[1], 0) + 1
                elif o[0] == 'BUY_LAND':
                    land += 1
        key = (land, tuple(sorted(animals.items())))
        clusters.setdefault(key, []).append(r_id)
    STEP_CLUSTERS[step] = clusters

def get_compatible_routes(current_route, step):
    """Returns candidate routes that have identical physical assets at step."""
    # Find cluster that contains current_route
    for step_boundary in sorted(STEP_CLUSTERS.keys(), reverse=True):
        if step >= step_boundary:
            for key, r_list in STEP_CLUSTERS[step_boundary].items():
                if current_route in r_list:
                    return r_list
            break
    return [current_route]

def score_route_against_shops(r_id, unlocked_shops, market_prices=None):
    """Computes shop demand alignment score for route r_id."""
    p = PROFILES[str(r_id)]
    sells = p['sells']
    prices = market_prices or BASE_PRICES
    
    score = sum(sells[item] * prices.get(item, 1) for item in sells)
    
    # Add shop demand bonus
    for shop in unlocked_shops:
        demands = SHOP_DEMANDS.get(shop, {})
        for item, mult in demands.items():
            sold = sells.get(item, 0)
            # 20% price preservation bonus per shop demand unit
            score += sold * prices.get(item, 1) * 0.20 * mult
            
    return score

def dynamic_router(observation, step, state):
    # Step 2: Record continuous rival state
    if step == 2:
        try:
            rv = observation['farms'][1 - int(observation['player'])]
            mkt_wheat = int(observation['market']['inventory']['WHEAT'])
            state['rival_cash'] = float(rv['money'])
            state['rival_wheat_draw'] = 10000 - mkt_wheat
            state['rkey'] = (round(float(rv['money']), 3), mkt_wheat)
        except Exception:
            state['rkey'] = None

    town = observation.get('town', {}) or {}
    unlocked_shops = list(town.get('unlocked_shops', []) or [])
    current_route = state.get('route', 0)
    
    # Day 6 (step 144): Initial major route selection
    if step >= 144 and not state.get('day6'):
        shops_2 = tuple(unlocked_shops[:2])
        has_yarn = 'YARN_STORE' in unlocked_shops
        
        if has_yarn:
            # Check rival trick first, else use standard yarn specialist route 9
            if state.get('rkey') in base_module._V93_ROUTE_BY_RIVAL:
                best_route = base_module._V93_ROUTE_BY_RIVAL[state['rkey']]
            else:
                best_route = base_module._V92_TABLE.get(shops_2, 9)
        else:
            # Score all compatible routes against unlocked shops
            compat = get_compatible_routes(current_route, 144)
            best_route = max(compat, key=lambda r: score_route_against_shops(r, unlocked_shops))
            
        state['route'] = best_route
        state['day6'] = True
        state['replan_history'] = [(144, 6, best_route, list(unlocked_shops))]

    # Days 9, 12, 15, 18, 21, 24: Receding-horizon replanning within physical compatibility cluster!
    for check_step in [216, 288, 360, 432, 504, 576]:
        flag = f'replan_{check_step}'
        if step >= check_step and not state.get(flag):
            compat = get_compatible_routes(current_route, check_step)
            if len(compat) > 1:
                # Rank compatible routes by current shop demand
                mkt_px = observation.get('market', {}).get('prices', {})
                best_route = max(compat, key=lambda r: score_route_against_shops(r, unlocked_shops, mkt_px))
                if best_route != current_route:
                    # Switch route smoothly
                    current_route = best_route
                    state['route'] = best_route
                    state.setdefault('replan_history', []).append((check_step, check_step // 24, best_route, list(unlocked_shops)))
            state[flag] = True

    # Day 27 (step 648): Terminal liquidation switch
    if step >= 648 and not state.get('day27'):
        state['route'] = 2
        state['day27'] = True
        state.setdefault('replan_history', []).append((648, 27, 2, list(unlocked_shops)))

    return state.get('route', 0)

if __name__ == '__main__':
    # Build agent with dynamic_router and test locally on the 5 evaluation seeds
    test_agent = base_module.make_agent(base_module._ROUTES, router=dynamic_router, **base_module._SETTINGS)
    
    print("Testing dynamic_router on Seed 29453000...")
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 29453000})
    env.run([test_agent, "starter"])
    final = env.steps[-1]
    print(f"Result: My=${final[0].reward:,.0f} vs Starter=${final[1].reward:,.0f}")
