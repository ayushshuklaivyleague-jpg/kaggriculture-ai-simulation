import kaggle_environments
import importlib.util

def load_agent(filepath):
    spec = importlib.util.spec_from_file_location("agent_mod", filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def main():
    cand = load_agent("main.py")
    opp = load_agent("opponent_market_shock.py")
    
    seed = 29453003
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.run([cand, opp])
    
    final = env.steps[-1]
    print(f"Seed {seed}: Cand=${final[0].reward} vs MarketShock=${final[1].reward}")
    
    # Trace the last 20 steps
    print("\n--- Last 10 turns analysis ---")
    for step_num in range(710, 720):
        step_state = env.steps[step_num]
        p0_obs = step_state[0]['observation']
        p0_reward = step_state[0]['reward']
        p1_reward = step_state[1]['reward']
        p0_action = step_state[0].get('action', {})
        p1_action = step_state[1].get('action', {})
        
        p0_private = p0_obs['private']
        p0_shed = p0_private['shed']
        p0_money = p0_obs['farms'][0]['money']
        p1_money = p0_obs['farms'][1]['money']
        
        print(f"Step {step_num}: P0=${p0_money} (shed={p0_shed}) | P1=${p1_money}")
        if p0_action.get('market'):
            print(f"  P0 market: {p0_action.get('market')}")
        if p1_action.get('market'):
            print(f"  P1 market: {p1_action.get('market')}")

if __name__ == "__main__":
    main()
