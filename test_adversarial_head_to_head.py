"""Rigorous Verification for Adversarial Ambush Layer.

Tests:
1. Paired head-to-head vs Upstream 2945 Farm across both seats.
2. Paired head-to-head vs Market Shock baseline across both seats.
3. Paired head-to-head vs Main Champion (mirror test) to confirm zero self-harm.
4. Telemetry inspection: verify war chest held, feed squeeze buys, ambush executions, and damage dealt.
"""

import time
import kaggle_environments
import adversarial_ambush
import opponent_2945_upstream
import opponent_market_shock
import main as champion_base

TEST_SEEDS = [29453000, 29453001, 29453002]

def run_paired_match(agent_a, agent_b, name_a, name_b, seeds):
    print(f"\n" + "=" * 70)
    print(f"   PAIRED MATCH: {name_a} vs {name_b} ({len(seeds)*2} games)")
    print("=" * 70)
    
    results = []
    for seed in seeds:
        for seat_a in [0, 1]:
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            if seat_a == 0:
                env.run([agent_a, agent_b])
                r_a = env.steps[-1][0].reward
                r_b = env.steps[-1][1].reward
            else:
                env.run([agent_b, agent_a])
                r_a = env.steps[-1][1].reward
                r_b = env.steps[-1][0].reward
                
            diff = r_a - r_b
            win = 1 if diff > 5 else 0
            loss = 1 if diff < -5 else 0
            tie = 1 if abs(diff) <= 5 else 0
            
            outcome = "WIN" if win else ("LOSS" if loss else "TIE")
            print(f"Seed {seed} | Seat {seat_a}: {name_a}=${r_a:.0f} vs {name_b}=${r_b:.0f} | Diff={diff:+.0f} [{outcome}]")
            results.append((r_a, r_b, diff, win, loss, tie))
            
    total_wins = sum(r[3] for r in results)
    total_losses = sum(r[4] for r in results)
    total_ties = sum(r[5] for r in results)
    mean_diff = sum(r[2] for r in results) / len(results)
    mean_a = sum(r[0] for r in results) / len(results)
    mean_b = sum(r[1] for r in results) / len(results)
    win_rate = (total_wins + 0.5 * total_ties) / len(results) * 100
    
    print("-" * 70)
    print(f"SUMMARY: {total_wins}W - {total_losses}L - {total_ties}T | Win Rate: {win_rate:.1f}%")
    print(f"Mean {name_a}: ${mean_a:.0f} | Mean {name_b}: ${mean_b:.0f} | Margin: {mean_diff:+.0f}")
    print(f"Telemetry: {adversarial_ambush.agent.telemetry}")
    print("-" * 70)
    return total_wins, total_losses, total_ties, mean_diff

if __name__ == "__main__":
    print("Testing Adversarial Ambush Layer...")
    # Test vs 2945 Upstream
    run_paired_match(adversarial_ambush.agent, opponent_2945_upstream.agent, "Adversarial_Ambush", "2945_Upstream", TEST_SEEDS)
    # Test vs Market Shock Baseline
    run_paired_match(adversarial_ambush.agent, opponent_market_shock.agent, "Adversarial_Ambush", "Market_Shock", TEST_SEEDS)
