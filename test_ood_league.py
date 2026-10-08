import league_eval_harness

OOD_SEEDS = [42, 12345, 99999, 777777, 20260920]

if __name__ == "__main__":
    print("Testing on Out-of-Distribution Seeds...")
    league_eval_harness.run_league_tournament("main.py", seeds=OOD_SEEDS)
