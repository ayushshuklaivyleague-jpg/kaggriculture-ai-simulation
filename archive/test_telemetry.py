"""Test script to verify telemetry logging at 3-day boundaries on main.py.
"""
import kaggle_environments
import main as current_agent

def count_tile_contents(tiles):
    animals = {"GOOSE": 0, "COW": 0, "SHEEP": 0}
    crops = {}
    structures = {"COOP": 0, "PASTURE": 0}
    weeds = 0
    if not tiles:
        return animals, crops, structures, weeds
    for row in tiles:
        for t in row:
            if isinstance(t, dict):
                k = t.get("kind")
                if k == "WEED":
                    weeds += 1
                elif k == "PLANT":
                    c = t.get("crop", "UNKNOWN")
                    crops[c] = crops.get(c, 0) + 1
                elif k in ("COOP", "PASTURE"):
                    structures[k] = structures.get(k, 0) + 1
                    a = t.get("animal")
                    if a in animals:
                        animals[a] += 1
    return animals, crops, structures, weeds

def inspect_game():
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 29453000})
    
    # We will wrap current_agent to observe every 72 steps (3-day boundary)
    log_records = []
    
    original_agent = current_agent.agent
    
    def wrapped_agent(obs, config=None):
        step = int(obs["step"])
        if step % 72 == 0 or step == 718:
            seat = int(obs["player"])
            opp_seat = 1 - seat
            my_farm = obs["farms"][seat]
            opp_farm = obs["farms"][opp_seat]
            my_priv = obs.get("private", {})
            mkt = obs.get("market", {})
            town = obs.get("town", {})
            
            my_animals, my_crops, my_structs, my_weeds = count_tile_contents(my_farm.get("tiles", []))
            opp_animals, opp_crops, opp_structs, opp_weeds = count_tile_contents(opp_farm.get("tiles", []))
            
            unlocked_shops = list(town.get("unlocked_shops", []))
            # count shop frequencies
            shop_counts = {}
            for s in unlocked_shops:
                shop_counts[s] = shop_counts.get(s, 0) + 1
                
            record = {
                "day": step // 24,
                "step": step,
                "my_cash": round(my_farm.get("money", 0), 1),
                "opp_cash": round(opp_farm.get("money", 0), 1),
                "margin": round(my_farm.get("money", 0) - opp_farm.get("money", 0), 1),
                "my_hands": len(my_farm.get("hands", [])),
                "opp_hands": len(opp_farm.get("hands", [])),
                "my_quads": len(my_farm.get("unlocked_quadrants", [])),
                "opp_quads": len(opp_farm.get("unlocked_quadrants", [])),
                "my_animals": my_animals,
                "opp_animals": opp_animals,
                "my_crops": my_crops,
                "opp_crops": opp_crops,
                "my_shed": dict(my_priv.get("shed", {})),
                "my_seeds": dict(my_priv.get("seeds", {})),
                "shops": unlocked_shops,
                "shop_counts": shop_counts,
                "mkt_wheat_inv": mkt.get("inventory", {}).get("WHEAT", 0),
                "mkt_wheat_px": mkt.get("prices", {}).get("WHEAT", 1),
            }
            log_records.append(record)
            
        return original_agent(obs, config)
        
    env.run([wrapped_agent, "starter"])
    final = env.steps[-1]
    
    import json
    with open("telemetry_dump.json", "w") as f:
        json.dump(log_records, f, indent=2)
    print(f"Dumped {len(log_records)} records to telemetry_dump.json! Final: My=${final[0].reward:,.0f} vs Opp=${final[1].reward:,.0f}")

if __name__ == "__main__":
    inspect_game()
