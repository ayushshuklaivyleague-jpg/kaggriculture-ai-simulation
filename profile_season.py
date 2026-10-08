"""Inspect game state summary for each day 0..29."""
import kaggle_environments
import main as v2_agent

def profile_season(seed=29453000):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    
    daily_summaries = []
    
    def traced_agent(obs):
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        
        if hour == 23:
            me = obs["farms"][obs["player"]]
            private = obs["private"]
            tiles = me["tiles"]
            empty = sum(1 for row in tiles for t in row if t is None)
            plants = [(t.get("crop"), t.get("yield_units", 0), t.get("planted_day"))
                      for row in tiles for t in row if isinstance(t, dict) and t.get("kind") == "PLANT"]
            pastures = [(t.get("kind"), t.get("animal"))
                        for row in tiles for t in row if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE")]
            weeds = sum(1 for row in tiles for t in row if isinstance(t, dict) and t.get("kind") == "WEED")
            
            crop_counts = {}
            for c, y, pd in plants:
                crop_counts[c] = crop_counts.get(c, 0) + 1
                
            animal_counts = {}
            for k, a in pastures:
                key = f"{k}:{a}"
                animal_counts[key] = animal_counts.get(key, 0) + 1
                
            daily_summaries.append({
                "day": day,
                "money": me["money"],
                "empty": empty,
                "crops": crop_counts,
                "animals": animal_counts,
                "weeds": weeds,
                "shed": {k: v for k, v in private.get("shed", {}).items() if v > 0},
                "quadrants": len(me.get("unlocked_quadrants", [])),
            })
            
        return v2_agent.agent(obs)

    env.run([traced_agent, "starter"])
    final = env.steps[-1]
    
    print("DAY |  MONEY | EMP | CROPS          | ANIMALS/STRUCTS   | SHED")
    print("-" * 75)
    for s in daily_summaries:
        crops_str = ", ".join(f"{k}:{v}" for k, v in s["crops"].items()) or "None"
        anim_str = ", ".join(f"{k}:{v}" for k, v in s["animals"].items()) or "None"
        shed_str = ", ".join(f"{k}:{v}" for k, v in s["shed"].items()) or "Empty"
        print(f"{s['day']:3d} | {s['money']:6.0f} | {s['empty']:3d} | {crops_str:14s} | {anim_str:17s} | {shed_str}")
    print(f"\nFinal Reward: P0=${final[0].reward} vs P1=${final[1].reward}")

if __name__ == "__main__":
    profile_season()
