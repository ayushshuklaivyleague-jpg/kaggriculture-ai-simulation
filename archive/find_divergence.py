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
    
    diff_count = 0
    for s in range(len(env.steps)-1):
        a0 = env.steps[s][0].get('action', {})
        a1 = env.steps[s][1].get('action', {})
        m0 = env.steps[s+1][0]['observation']['farms'][0]['money']
        m1 = env.steps[s+1][1]['observation']['farms'][1]['money']
        if a0 != a1:
            print(f"Step {s} ACTION DIFF:")
            print(f"  P0 act: {a0}")
            print(f"  P1 act: {a1}")
            print(f"  Next money: P0=${m0} vs P1=${m1}")
            diff_count += 1
            if diff_count >= 5:
                break
    if diff_count == 0:
        print("ALL ACTIONS BETWEEN P0 AND P1 WERE COMPLETELY IDENTICAL!")
        # If all actions were identical, why did money differ at step 407?
        # Let's inspect step 405-407 market inventories and shed sales!
        for st in range(404, 408):
            obs = env.steps[st][0]['observation']
            print(f"Step {st}: P0 money=${obs['farms'][0]['money']}, P1 money=${obs['farms'][1]['money']}")
            print(f"  Market prices: {obs['market']['prices']}")
            print(f"  P0 shed: {obs['private']['shed']}")
            print(f"  Action P0: {env.steps[st][0].get('action')}")
            print(f"  Action P1: {env.steps[st][1].get('action')}")

if __name__ == "__main__":
    main()
