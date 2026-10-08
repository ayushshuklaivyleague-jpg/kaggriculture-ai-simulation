"""Detailed diagnostic telemetry for main.py (V2 Agent).
Collects worker action counts, idle turns, task assignments, shed accumulation,
and building-to-animal placement delays over a 720-step game.
"""
import json
from collections import Counter, defaultdict
import kaggle_environments
import main as v2_agent

def profile_game(seed=29453000, opponent="starter"):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    
    # We want to trace player 0 (v2_agent)
    worker_action_counts = defaultdict(Counter)
    pass_turns_by_day = defaultdict(lambda: defaultdict(int))
    tile_history = defaultdict(list)
    shed_history = []
    market_orders_count = []
    
    # Trace per-turn
    def traced_agent(obs):
        action = v2_agent.agent(obs)
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        me = obs["farms"][obs["player"]]
        private = obs["private"]
        
        # Farmer action
        f_act = action.get("farmer", ["PASS"])[0]
        worker_action_counts["farmer"][f_act] += 1
        if f_act == "PASS":
            pass_turns_by_day["farmer"][day] += 1
            
        # Hand actions
        hands = action.get("hands", [])
        for h_idx, h_act in enumerate(hands):
            act_name = h_act[0] if h_act else "PASS"
            worker_action_counts[f"hand_{h_idx}"][act_name] += 1
            if act_name == "PASS":
                pass_turns_by_day[f"hand_{h_idx}"][day] += 1
                
        # Shed state
        shed_total = sum(private.get("shed", {}).values())
        shed_history.append((day, hour, shed_total, dict(private.get("shed", {}))))
        
        # Market orders
        m_orders = action.get("market", [])
        market_orders_count.append((day, hour, len(m_orders)))
        
        return action

    env.run([traced_agent, opponent])
    final = env.steps[-1]
    p0_reward = final[0].reward
    p1_reward = final[1].reward
    
    print(f"Game Seed {seed} vs {opponent}: Reward P0=${p0_reward} vs P1=${p1_reward}")
    
    print("\n=== WORKER ACTION BREAKDOWN ===")
    total_actions = 0
    total_pass = 0
    for w_name, counts in sorted(worker_action_counts.items()):
        total_w = sum(counts.values())
        pass_w = counts.get("PASS", 0)
        total_actions += total_w
        total_pass += pass_w
        print(f"{w_name:10s} (total {total_w:3d}): PASS={pass_w:3d} ({pass_w/max(1,total_w)*100:4.1f}%), actions={dict(counts)}")
        
    print(f"\nTOTAL WORKER ACTIONS: {total_actions}, TOTAL PASS: {total_pass} ({total_pass/max(1,total_actions)*100:4.1f}%)")
    
    print("\n=== PASS TURNS BY DAY (FARMER & HANDS) ===")
    for day in range(30):
        farmer_pass = pass_turns_by_day["farmer"][day]
        hands_pass = sum(pass_turns_by_day[f"hand_{i}"][day] for i in range(10))
        if farmer_pass > 0 or hands_pass > 0:
            print(f"Day {day:2d}: Farmer PASS = {farmer_pass:2d}, Hands PASS = {hands_pass:2d}")
            
    # Check market orders underutilization
    empty_order_turns = sum(1 for d, h, cnt in market_orders_count if cnt == 0)
    print(f"\nTurns with 0 market orders: {empty_order_turns} / 720 ({empty_order_turns/720*100:.1f}%)")
    
    return p0_reward, p1_reward

if __name__ == "__main__":
    profile_game(29453000, "starter")
