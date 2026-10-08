"""Controlled Causal Ablation Runner for Kaggriculture.

Runs paired testing across identical (seed, opponent, seat) triples.
Directly tests whether disabling speculative layers recovers OOD performance.
"""

import time
import league_eval_harness

IN_DIST_SEEDS = [29453000, 29453001, 29453002, 29453003, 29453004]
OOD_SEEDS = [42, 12345, 99999, 777777, 20260920]

def evaluate_variant(variant_path, seeds, opp_names=None):
    print("\n" + "#" * 75)
    print(f"EVALUATING: {variant_path}")
    print(f"Seeds ({len(seeds)}): {seeds}")
    print("#" * 75)
    
    cand_fn = league_eval_harness.load_agent_from_file(variant_path, "cand")
    
    all_opps = [
        ("Upstream_2945_Farm", "opponent_2945_upstream.py"),
        ("Market_Shock_Baseline", "opponent_market_shock.py"),
    ]
    if opp_names:
        all_opps = [o for o in all_opps if o[0] in opp_names]
        
    summaries = []
    total_wins = 0
    total_games = 0
    
    for name, path in all_opps:
        opp_fn = league_eval_harness.load_agent_from_file(path, name)
        s = league_eval_harness.evaluate_against_opponent(cand_fn, opp_fn, name, seeds)
        summaries.append(s)
        total_wins += (s["wins"] + 0.5 * s["ties"])
        total_games += s["games"]
        
    overall_wr = (total_wins / total_games * 100.0) if total_games > 0 else 0
    print(f"\n--> {variant_path} Overall vs Top Traders: {total_wins:.0f}/{total_games} ({overall_wr:.1f}%)")
    return summaries

def main():
    print("===========================================================================")
    print("       CAUSAL ABLATION EXPERIMENT: HUNTING THE PERF-DEGRADING LAYERS")
    print("===========================================================================")
    print("Testing on Out-of-Distribution Seeds [42, 12345, 99999, 777777, 20260920]")
    
    variants = [
        ("Variant_A_Baseline", "main.py"),
        ("Variant_B_No_CounterPlan", "archive/variant_b_no_counterplan.py"),
        ("Variant_C_Reset_OR2", "archive/variant_c_reset_or2.py"),
        ("Variant_D_Clean_Router", "archive/variant_d_clean_router.py")
    ]
    
    results = {}
    for name, path in variants:
        t0 = time.time()
        summaries = evaluate_variant(path, OOD_SEEDS)
        results[name] = summaries
        print(f"Finished {name} in {time.time()-t0:.1f}s")
        
    print("\n" + "=" * 80)
    print("                  FINAL CAUSAL ABLATION SUMMARY (OOD SEEDS)")
    print("=" * 80)
    print(f"{'Variant':<28} | {'vs Upstream 2945':<24} | {'vs Market Shock':<24}")
    print("-" * 80)
    for name, summaries in results.items():
        s_up = next(s for s in summaries if s['opponent'] == 'Upstream_2945_Farm')
        s_ms = next(s for s in summaries if s['opponent'] == 'Market_Shock_Baseline')
        
        up_str = f"{s_up['win_rate']:.0f}% ({s_up['mean_delta']:+,.0f})"
        ms_str = f"{s_ms['win_rate']:.0f}% ({s_ms['mean_delta']:+,.0f})"
        print(f"{name:<28} | {up_str:<24} | {ms_str:<24}")
    print("=" * 80)

if __name__ == "__main__":
    main()
