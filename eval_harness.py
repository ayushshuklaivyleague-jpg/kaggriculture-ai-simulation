"""Deterministic Local Evaluation Harness for Kaggriculture Agents.

Runs a fixed seed suite (both seats 0 and 1) against a chosen opponent.
Records exact rewards, wins, losses, ties, margins, and statistics.
"""
import math
import sys
import kaggle_environments

EVAL_SEEDS = [29453000, 29453001, 29453002, 29453003, 29453004]

def evaluate_agent(agent_func, opponent="starter", seeds=None, verbose=True):
    if seeds is None:
        seeds = EVAL_SEEDS
        
    results = []
    
    for seed in seeds:
        for seat in [0, 1]:
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            
            if seat == 0:
                env.run([agent_func, opponent])
                my_reward = env.steps[-1][0].reward
                opp_reward = env.steps[-1][1].reward
                my_status = env.steps[-1][0].status
                opp_status = env.steps[-1][1].status
            else:
                env.run([opponent, agent_func])
                my_reward = env.steps[-1][1].reward
                opp_reward = env.steps[-1][0].reward
                my_status = env.steps[-1][1].status
                opp_status = env.steps[-1][0].status
                
            margin = my_reward - opp_reward
            win = 1 if my_reward > opp_reward else 0
            loss = 1 if my_reward < opp_reward else 0
            tie = 1 if my_reward == opp_reward else 0
            
            results.append({
                "seed": seed,
                "seat": seat,
                "my_reward": my_reward,
                "opp_reward": opp_reward,
                "margin": margin,
                "win": win,
                "loss": loss,
                "tie": tie,
                "my_status": my_status,
                "opp_status": opp_status,
            })
            if verbose:
                print(f"Seed {seed} Seat {seat}: My=${my_reward:.0f}, Opp=${opp_reward:.0f}, Margin={margin:+.0f} ({'W' if win else 'L' if loss else 'T'})")

    total_games = len(results)
    wins = sum(r["win"] for r in results)
    losses = sum(r["loss"] for r in results)
    ties = sum(r["tie"] for r in results)
    win_rate = (wins + 0.5 * ties) / total_games * 100.0
    
    margins = [r["margin"] for r in results]
    mean_margin = sum(margins) / total_games
    worst_margin = min(margins)
    
    my_rewards = [r["my_reward"] for r in results]
    mean_my_reward = sum(my_rewards) / total_games
    
    opp_rewards = [r["opp_reward"] for r in results]
    mean_opp_reward = sum(opp_rewards) / total_games
    
    variance = sum((m - mean_margin) ** 2 for m in margins) / max(1, total_games - 1)
    std_margin = math.sqrt(variance)
    
    summary = {
        "games": total_games,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": win_rate,
        "mean_my_reward": mean_my_reward,
        "mean_opp_reward": mean_opp_reward,
        "mean_margin": mean_margin,
        "worst_margin": worst_margin,
        "std_margin": std_margin,
        "results": results,
    }
    
    print("\n" + "=" * 55)
    print(f"SUMMARY vs {opponent} ({total_games} games, {len(seeds)} seeds, 2 seats):")
    print(f"Record: {wins}W - {losses}L - {ties}T (Win Rate: {win_rate:.1f}%)")
    print(f"Mean Final Cash: ${mean_my_reward:.0f} (Opp: ${mean_opp_reward:.0f})")
    print(f"Mean Margin:     {mean_margin:+.0f} (Worst: {worst_margin:+.0f}, Std: {std_margin:.0f})")
    print("=" * 55 + "\n")
    
    return summary

if __name__ == "__main__":
    import main as base_agent
    print("Evaluating BASELINE agent (main.py)...")
    evaluate_agent(base_agent.agent, opponent="starter")
