import league_eval_harness

IN_DIST_SEEDS = [29453000, 29453001, 29453002, 29453003, 29453004]

if __name__ == "__main__":
    print("Testing Variant D on IN-DISTRIBUTION Seeds...")
    league_eval_harness.run_league_tournament("variant_d_clean_router.py", seeds=IN_DIST_SEEDS)
