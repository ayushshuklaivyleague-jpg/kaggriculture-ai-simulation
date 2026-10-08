"""Simulation harness to benchmark V2 vs V1, Starter, and Random agents."""
import sys
import os
import json
import time

try:
    from kaggle_environments import make
except ImportError:
    print("kaggle_environments not installed yet. Please wait for pip installation to finish.")
    sys.exit(1)

import main as champion_agent
import opponent_2945_upstream as upstream_agent

def run_match(agent1, agent2, name1="Agent1", name2="Agent2", steps=720):
    print(f"\n--- MATCH: {name1} vs {name2} ({steps} steps) ---")
    env = make("kaggriculture", configuration={"episodeSteps": steps}, debug=True)
    
    t0 = time.time()
    env.run([agent1, agent2])
    elapsed = time.time() - t0
    
    final = env.steps[-1]
    p0_reward = final[0].reward
    p1_reward = final[1].reward
    p0_status = final[0].status
    p1_status = final[1].status
    
    print(f"Time: {elapsed:.1f}s")
    print(f"Result: {name1}: ${p0_reward} ({p0_status}) | {name2}: ${p1_reward} ({p1_status})")
    
    if p0_reward > p1_reward:
        winner = name1
    elif p1_reward > p0_reward:
        winner = name2
    else:
        winner = "TIE"
    print(f"Winner: {winner}")
    return p0_reward, p1_reward, winner

def main_suite():
    print("==================================================")
    print("       KAGGRICULTURE CHAMPION BENCHMARK HARNESS   ")
    print("==================================================")
    
    # 1. Champion vs Starter baseline
    run_match(champion_agent.agent, "starter", name1="Champion", name2="Starter_Baseline")
    
    # 2. Champion vs Upstream 2945
    run_match(champion_agent.agent, upstream_agent.agent, name1="Champion", name2="Upstream_2945")

if __name__ == "__main__":
    main_suite()
