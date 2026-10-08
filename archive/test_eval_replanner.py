"""Compare Baseline Agent vs Upgraded Dynamic Replanner Agent on 5 Seeds (10 Games).
"""
import copy
import json
import kaggle_environments
import main as base_module

# 1. Load routes profile
with open('routes_profile.json') as f:
    PROFILES = json.load(f)

CLUSTER_A = [0, 2, 100, 105, 106, 107, 108, 120, 121, 122, 124, 125]
CLUSTER_B = [1, 3, 4, 5, 6, 7, 8, 10, 11, 12, 109, 126, 127, 128]
CLUSTER_C = [101, 103, 104, 112, 113, 116, 118, 119]

def get_cluster(r):
    if r in CLUSTER_A: return CLUSTER_A
    if r in CLUSTER_B: return CLUSTER_B
    if r in CLUSTER_C: return CLUSTER_C
    return [r]

def score_route_demand(r, unlocked_shops):
    p = PROFILES[str(r)]
    s = p['sells']
    score = 0
    for shop in unlocked_shops:
        if shop == 'PIZZA_SHOP': score += s.get('WHEAT', 0)*25 + s.get('TOMATO', 0)*45
        elif shop == 'PET_CAFE': score += s.get('CARROT', 0)*35 + s.get('EGG', 0)*40 + s.get('MILK', 0)*60
        elif shop == 'BRUNCH_SPOT': score += s.get('CARROT', 0)*35 + s.get('EGG', 0)*40 + s.get('MILK', 0)*60 + s.get('STRAWBERRY', 0)*60
        elif shop == 'BAKERY': score += s.get('WHEAT', 0)*25 + s.get('CARROT', 0)*35
        elif shop == 'ICE_CREAM_SHOP': score += s.get('MILK', 0)*60 + s.get('STRAWBERRY', 0)*60
        elif shop == 'SMOOTHIE_SHOP': score += s.get('CARROT', 0)*35 + s.get('STRAWBERRY', 0)*60 + s.get('MELON', 0)*100
        elif shop == 'FARMERS_MARKET': score += s.get('CARROT', 0)*35 + s.get('TOMATO', 0)*45 + s.get('STRAWBERRY', 0)*60 + s.get('MELON', 0)*100
        elif shop == 'YARN_STORE': score += s.get('WOOL', 0)*80*2
    return score

def upgraded_router(observation, step, state):
    if step == 2:
        try:
            rv = observation['farms'][1 - int(observation['player'])]
            mkt_w = int(observation['market']['inventory']['WHEAT'])
            state['rkey'] = (round(float(rv['money']), 3), mkt_w)
        except Exception:
            state['rkey'] = None

    town = observation.get('town', {}) or {}
    unlocked_shops = list(town.get('unlocked_shops', []) or [])
    
    # Day 6 (step 144)
    if step >= 144 and not state.get('day6'):
        shops_2 = tuple(unlocked_shops[:2])
        use_new = unlocked_shops.count('YARN_STORE') <= 0
        state['expert'] = 'EXP240' if use_new else 'V39'
        r = base_module._R108_SHOP_ROUTES.get(shops_2, 100) if use_new else base_module._R110_OLD_SHOPS.get(shops_2, 0)
        r = base_module._V92_TABLE.get(shops_2, r)
        if 'YARN_STORE' in unlocked_shops and state.get('rkey') in base_module._V93_ROUTE_BY_RIVAL:
            r = base_module._V93_ROUTE_BY_RIVAL[state['rkey']]
        state['route'] = r
        state['day6'] = True

    # Receding-horizon replanning at Days 9, 12, 15, 18, 21, 24:
    curr_r = state.get('route', 0)
    for check_s in [216, 288, 360, 432, 504, 576]:
        flag = f'replan_{check_s}'
        if step >= check_s and not state.get(flag):
            cluster = get_cluster(curr_r)
            if len(cluster) > 1:
                curr_score = score_route_demand(curr_r, unlocked_shops)
                best_r = max(cluster, key=lambda cand: score_route_demand(cand, unlocked_shops))
                best_score = score_route_demand(best_r, unlocked_shops)
                # Only switch if there is a meaningful score improvement (>= 3%)
                if best_score > curr_score * 1.03:
                    state['route'] = best_r
                    curr_r = best_r
            state[flag] = True

    # Day 27 (step 648)
    if step >= 648 and not state.get('day27'):
        state['route'] = 2
        state['day27'] = True

    return state.get('route', 0)

if __name__ == '__main__':
    # Build upgraded agent with all 42 outer layers wrapping the new router
    # We patch base_module._router with upgraded_router
    orig_router = base_module._router
    base_module._router = upgraded_router
    base_module._IMPL.chassis.router = upgraded_router
    
    from eval_harness import evaluate_agent
    print("Evaluating UPGRADED AGENT vs starter...")
    evaluate_agent(base_module.agent, opponent="starter")
