"""Extensive multi-seed tournament evaluation for Kaggriculture agent.
Tests 20+ matches across varied seeds and opponents (starter, random, v2_backup).
Verifies that score is consistently well above $3,000 in every match.
"""
import time
import math
import kaggle_environments
import main as current_agent
import v2_planner_backup as previous_agent

TEST_SEEDS = [
    29453000, 29453001, 29453002, 29453003, 29453004, # Classic 2945 suite
    42, 12345, 99999, 777777, 20260920                # Out-of-distribution seeds
]

def run_match(agent0, agent1, seed, name0="P0", name1="P1"):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    t0 = time.time()
    env.run([agent0, agent1])
    elapsed = time.time() - t0
    final = env.steps[-1]
    
    r0 = final[0].reward
    r1 = final[1].reward
    s0 = final[0].status
    s1 = final[1].status
    return {
        "seed": seed,
        "name0": name0,
        "name1": name1,
        "r0": r0,
        "r1": r1,
        "s0": s0,
        "s1": s1,
        "elapsed": elapsed
    }

def main():
    print("=" * 70)
    print("      EXTENSIVE TOURNAMENT EVALUATION (24 MATCHES)")
    print("=" * 70)
    
    results_vs_starter = []
    
    # 1. Test vs Starter on 10 seeds (both seats = 20 games)
    print("\n[PART 1] Testing vs Starter across 10 distinct seeds (both seats)...")
    for seed in TEST_SEEDS:
        # Seat 0
        res0 = run_match(current_agent.agent, "starter", seed, "MarketShock", "Starter")
        win0 = "W" if res0["r0"] > res0["r1"] else "L" if res0["r0"] < res0["r1"] else "T"
        print(f"Seed {seed:8d} (Seat 0): Score=${res0['r0']:,.0f} vs Starter=${res0['r1']:,.0f} | Margin={res0['r0']-res0['r1']:+,.0f} [{win0}] in {res0['elapsed']:.1f}s")
        results_vs_starter.append((res0["r0"], res0["r1"], res0["r0"] > res0["r1"]))
        
        # Seat 1
        res1 = run_match("starter", current_agent.agent, seed, "Starter", "MarketShock")
        win1 = "W" if res1["r1"] > res1["r0"] else "L" if res1["r1"] < res1["r0"] else "T"
        print(f"Seed {seed:8d} (Seat 1): Score=${res1['r1']:,.0f} vs Starter=${res1['r0']:,.0f} | Margin={res1['r1']-res1['r0']:+,.0f} [{win1}] in {res1['elapsed']:.1f}s")
        results_vs_starter.append((res1["r1"], res1["r0"], res1["r1"] > res1["r0"]))

    # 2. Test vs Previous V2 Planner (Head-to-head)
    print("\n[PART 2] Head-to-head vs Previous V2 Planner...")
    h2h_results = []
    for seed in [29453000, 42]:
        res_h2h_0 = run_match(current_agent.agent, previous_agent.agent, seed, "MarketShock", "V2_Planner")
        win_h0 = "W" if res_h2h_0["r0"] > res_h2h_0["r1"] else "L"
        print(f"H2H Seed {seed} (Seat 0): MarketShock=${res_h2h_0['r0']:,.0f} vs V2_Planner=${res_h2h_0['r1']:,.0f} [{win_h0}]")
        h2h_results.append(res_h2h_0["r0"] > res_h2h_0["r1"])
        
        res_h2h_1 = run_match(previous_agent.agent, current_agent.agent, seed, "V2_Planner", "MarketShock")
        win_h1 = "W" if res_h2h_1["r1"] > res_h2h_1["r0"] else "L"
        print(f"H2H Seed {seed} (Seat 1): MarketShock=${res_h2h_1['r1']:,.0f} vs V2_Planner=${res_h2h_1['r0']:,.0f} [{win_h1}]")
        h2h_results.append(res_h2h_1["r1"] > res_h2h_1["r0"])

    # Summary
    my_scores = [r[0] for r in results_vs_starter]
    wins = sum(1 for r in results_vs_starter if r[2])
    total = len(results_vs_starter)
    
    print("\n" + "=" * 70)
    print("FINAL TOURNAMENT SUMMARY:")
    print(f"Games Tested vs Starter: {total}")
    print(f"Record:                  {wins}W - {total - wins}L - 0T ({wins/total*100:.1f}%)")
    print(f"Average Final Cash:      ${sum(my_scores)/total:,.0f}")
    print(f"Lowest Final Cash:       ${min(my_scores):,.0f} (Target threshold: >$3,000)")
    print(f"Highest Final Cash:      ${max(my_scores):,.0f}")
    print(f"All Scores > $3,000?:    {all(s > 3000 for s in my_scores)}")
    print(f"H2H vs Old V2:           {sum(h2h_results)}/{len(h2h_results)} Wins")
    print("=" * 70)

if __name__ == "__main__":
    main()
