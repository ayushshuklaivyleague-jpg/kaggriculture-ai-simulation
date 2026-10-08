"""Head-to-head match: Upgraded agent (main.py) vs Previous Champion (main_backup.py).

Tests head-to-head win rate, cash margin, and market resilience.
"""
import kaggle_environments
import importlib.util

def load_agent(filepath):
    spec = importlib.util.spec_from_file_location("agent_mod", filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def main():
    print("Loading agents...")
    new_agent = load_agent("main.py")
    old_agent = load_agent("main_backup.py")
    
    seeds = [29453000, 29453001, 29453002, 29453003, 29453004]
    results = []
    
    for seed in seeds:
        for new_seat in [0, 1]:
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            
            if new_seat == 0:
                env.run([new_agent, old_agent])
                new_reward = env.steps[-1][0].reward
                old_reward = env.steps[-1][1].reward
            else:
                env.run([old_agent, new_agent])
                new_reward = env.steps[-1][1].reward
                old_reward = env.steps[-1][0].reward
                
            margin = new_reward - old_reward
            win = 1 if new_reward > old_reward else 0
            loss = 1 if new_reward < old_reward else 0
            tie = 1 if new_reward == old_reward else 0
            
            results.append({
                "seed": seed,
                "seat": new_seat,
                "new": new_reward,
                "old": old_reward,
                "margin": margin,
                "win": win,
                "loss": loss,
                "tie": tie
            })
            outcome = 'WIN' if win else ('LOSS' if loss else 'TIE')
            print(f"Seed {seed} Seat {new_seat}: New=${new_reward:.0f} vs Old=${old_reward:.0f} | Margin={margin:+.0f} [{outcome}]")

    wins = sum(r["win"] for r in results)
    losses = sum(r["loss"] for r in results)
    ties = sum(r["tie"] for r in results)
    win_rate = (wins + 0.5 * ties) / len(results) * 100
    mean_margin = sum(r["margin"] for r in results) / len(results)
    mean_new = sum(r["new"] for r in results) / len(results)
    mean_old = sum(r["old"] for r in results) / len(results)
    
    print("\n" + "="*60)
    print(f"HEAD-TO-HEAD SUMMARY: New vs Old Champion (10 games)")
    print(f"Record: {wins}W - {losses}L - {ties}T (Win Rate: {win_rate:.1f}%)")
    print(f"New Agent Mean Cash: ${mean_new:.0f}")
    print(f"Old Agent Mean Cash: ${mean_old:.0f}")
    print(f"Mean Margin:         {mean_margin:+.0f}")
    print("="*60)

if __name__ == "__main__":
    main()
