"""Script to generate controlled ablation variants B, C, and D from main.py."""

def build():
    with open("main.py", "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    # -------------------------------------------------------------
    # VARIANT B: Disable speculative continuous archetype counter-plan
    # Revert _ct_apply to exact CT_TABLE.get(...) only
    # -------------------------------------------------------------
    src_b = src.replace(
        'st["plan"] = _get_counter_plan(rival["money"], mkt_w)',
        'st["plan"] = CT_TABLE.get((round(float(rival["money"]), 3), mkt_w))'
    )
    with open("variant_b_no_counterplan.py", "w", encoding="utf-8") as f:
        f.write(src_b)
    print("Created variant_b_no_counterplan.py")

    # -------------------------------------------------------------
    # VARIANT C: Variant B + Reset _OR2_SN_K from 10 to 0
    # -------------------------------------------------------------
    src_c = src_b.replace(
        '_OR2_SN_K = 10',
        '_OR2_SN_K = 0'
    )
    with open("variant_c_reset_or2.py", "w", encoding="utf-8") as f:
        f.write(src_c)
    print("Created variant_c_reset_or2.py")

    # -------------------------------------------------------------
    # VARIANT D: Variant C + Revert router to clean baseline (no cluster replanning)
    # -------------------------------------------------------------
    # In opponent_market_shock.py, router was:
    clean_router = """def _router(observation,step,state):
    if step==2:
        try:
            _rv=observation['farms'][1-int(observation['player'])]
            state['rkey']=(round(float(_rv['money']),3), int(observation['market']['inventory']['WHEAT']))
        except Exception:
            state['rkey']=None
    if step>=144 and not state.get('day6'):
        shops=tuple((_get(_get(observation,'town',{}),'unlocked_shops',[]) or [])[:2])
        use_new=shops.count('YARN_STORE')<=0
        state['expert']='EXP240' if use_new else 'V39'
        state['route']=_R108_SHOP_ROUTES.get(shops,100) if use_new else _R110_OLD_SHOPS.get(shops,0)
        state['route']=_V92_TABLE.get(shops,state['route'])
        if 'YARN_STORE' in shops and state.get('rkey') in _V93_ROUTE_BY_RIVAL:
            state['route']=_V93_ROUTE_BY_RIVAL[state['rkey']]
        state['day6']=True
    if step>=648 and not state.get('day27'):
        state['route']=2
        state['day27']=True
    return state.get('route',0)"""

    # Find the start of _CLUSTER_A and end of _router in src_c
    start_pos = src_c.find("_CLUSTER_A = [")
    end_marker = "return state.get('route',0)"
    end_pos = src_c.find(end_marker, start_pos) + len(end_marker)

    if start_pos != -1 and end_pos != -1:
        src_d = src_c[:start_pos] + clean_router + src_c[end_pos:]
        with open("variant_d_clean_router.py", "w", encoding="utf-8") as f:
            f.write(src_d)
        print("Created variant_d_clean_router.py")
    else:
        print(f"Warning: could not locate cluster router markers ({start_pos}, {end_pos})")

if __name__ == "__main__":
    build()
