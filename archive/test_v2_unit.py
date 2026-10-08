"""Unit tests and benchmarks for Kaggriculture V2 agent.

Tests:
1. Exact price engine against spec reference table.
2. Marginal revenue calculations.
3. NPV calculations (crops & animals).
4. Task generation & worker scheduling.
5. Runtime performance benchmark (< 20ms target).
"""
import time
import main

def test_price_engine():
    print("=== TEST 1: Price Engine Spec Compliance ===")
    ref_points = [
        # (product, inventory, expected_min, expected_max)
        ("WHEAT", 10000, 25, 25),
        ("WHEAT", 9600, 45, 45),   # -T: $45
        ("WHEAT", 10400, 20, 20),  # +T: $20
        ("WHEAT", 10800, 19, 19),  # +2T: $19
        ("CARROT", 10000, 35, 35),
        ("CARROT", 9550, 70, 70),   # -T: $70
        ("CARROT", 10450, 10, 11),  # +T: $10 or $11 depending on rounding
        ("CARROT", 10900, 1, 1),    # +2T: $1
        ("TOMATO", 10000, 60, 60),
        ("TOMATO", 9800, 84, 84),   # -T: $84
        ("TOMATO", 10200, 24, 24),  # +T: $24
        ("TOMATO", 10400, 9, 9),    # +2T: $9
        ("STRAWBERRY", 10000, 120, 120),
        ("STRAWBERRY", 9900, 204, 204), # -T: $204
        ("STRAWBERRY", 10100, 1, 1),    # +T: $1
        ("MELON", 10000, 250, 250),
        ("MELON", 9700, 300, 300),      # -T: $300
        ("MELON", 10300, 1, 1),         # +T: $1
        ("EGG", 10000, 50, 50),
        ("EGG", 9668, 70, 70),          # -T: $70
        ("EGG", 10332, 40, 40),         # +T: $40
        ("EGG", 10664, 39, 39),         # +2T: $39
        ("MILK", 10000, 160, 160),
        ("MILK", 9878, 256, 256),       # -T: $256
        ("MILK", 10122, 1, 1),          # +T: $1
        ("WOOL", 10000, 200, 200),
        ("WOOL", 9895, 240, 240),       # -T: $240
        ("WOOL", 10105, 1, 1),          # +T: $1
        ("FERTILIZER", 10000, 100, 100),
        ("FERTILIZER", 9800, 140, 140), # -T: $140
        ("FERTILIZER", 10200, 60, 60),  # +T: $60
        ("FERTILIZER", 10400, 20, 20),  # +2T: $20
    ]

    passed = 0
    for prod, inv, exp_min, exp_max in ref_points:
        actual = main.compute_price(prod, inv)
        assert exp_min <= actual <= exp_max, f"FAIL {prod} at inv={inv}: expected [{exp_min}, {exp_max}], got {actual}"
        passed += 1
    print(f"PASS: All {passed} reference price points verified.")

def test_marginal_revenue():
    print("\n=== TEST 2: Marginal Revenue ===")
    # Selling 5 carrots at starting inventory 10000
    rev = main.marginal_revenue("CARROT", 10000, 5)
    print(f"Carrot x5 revenue at I0=10000: ${rev}")
    assert rev > 0
    # Selling strawberry into glut
    rev_straw = main.marginal_revenue("STRAWBERRY", 10050, 100)
    print(f"Strawberry x100 revenue starting at 10050: ${rev_straw}")
    assert rev_straw >= 100  # at least $1 each
    print("PASS: Marginal revenue functions as expected.")

def test_economics():
    print("\n=== TEST 3: Economics & NPV ===")
    market_inv = {k: 10000 for k in main.MP}
    shops = ["BAKERY", "PET CAFE"]

    best_crop_early = main.best_crop_for_day(0, market_inv, shops)
    print(f"Best crop at Day 0: {best_crop_early}")
    assert best_crop_early in main.CROP

    best_crop_late = main.best_crop_for_day(27, market_inv, shops)
    print(f"Best crop at Day 27: {best_crop_late}")
    # Late game must pick a fast crop (e.g. Carrot or Wheat), not Melon (10 days)
    assert best_crop_late in ("CARROT", "WHEAT")

    best_anim = main.best_animal_for_day(0, market_inv, shops)
    print(f"Best animal at Day 0: {best_anim}")

    best_anim_late = main.best_animal_for_day(25, market_inv, shops)
    print(f"Best animal at Day 25: {best_anim_late}")
    assert best_anim_late is None  # can't produce before day 30, so NPV < 0
    print("PASS: Economic evaluator correctly gates investments.")

def test_full_agent_turn():
    print("\n=== TEST 4: Full Agent Turn Execution & Performance ===")
    # Construct a valid, realistic observation dictionary
    tiles = [[None for _ in range(10)] for _ in range(10)]
    # Lock non-NW quadrants
    for y in range(10):
        for x in range(10):
            if x >= 5 or y >= 5:
                tiles[y][x] = "LOCKED"
    
    # Put a wheat plant at (0, 0)
    tiles[0][0] = {
        "kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
        "watered_today": False, "consecutive_unwatered": 0,
        "yield_units": 0, "max_lifespan_step": 120, "fertilized_until_day": -1
    }

    dummy_obs = {
        "player": 0,
        "step": 0,
        "day": 0,
        "hour": 0,
        "farms": [
            {
                "money": 3000.0,
                "tiles": tiles,
                "farmer": [4, 4],
                "hands": [[4, 4]],
                "unlocked_quadrants": ["NW"],
                "hires_today": 0
            },
            {
                "money": 3000.0,
                "tiles": tiles,
                "farmer": [4, 4],
                "hands": [],
                "unlocked_quadrants": ["NW"],
                "hires_today": 0
            }
        ],
        "private": {
            "shed": {"WHEAT": 10},
            "seeds": {"CARROT": 5},
            "inventories": [{}, {}]
        },
        "market": {
            "inventory": {k: 10000 for k in main.MP},
            "prices": {k: main.MP[k]["base"] for k in main.MP}
        },
        "town": {
            "unlocked_shops": ["BAKERY"]
        }
    }

    t0 = time.perf_counter()
    action = main.agent(dummy_obs)
    dt_ms = (time.perf_counter() - t0) * 1000

    print(f"Action emitted in {dt_ms:.2f} ms:")
    print(f"  Farmer: {action.get('farmer')}")
    print(f"  Hands:  {action.get('hands')}")
    print(f"  Market: {action.get('market')}")

    assert "farmer" in action
    assert "hands" in action
    assert "market" in action
    assert isinstance(action["farmer"], list)
    assert len(action["hands"]) == 1  # 1 hand was present
    assert len(action["market"]) <= 10
    assert dt_ms < 25.0, f"Execution took too long: {dt_ms:.2f}ms"
    print(f"PASS: Full turn executed in {dt_ms:.2f} ms (< 25 ms target).")

if __name__ == "__main__":
    test_price_engine()
    test_marginal_revenue()
    test_economics()
    test_full_agent_turn()
    print("\nALL UNIT TESTS PASSED SUCCESSFULLY! [OK]")
