"""Inspect why workers are idling (PASS) hour-by-hour on Days 0, 1, 2, and 5.
Writes output directly to hourly_log.txt.
"""
import kaggle_environments
import main as v2_agent

def inspect_hours(seed=29453000):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    
    with open("hourly_log.txt", "w", encoding="utf-8") as out:
        def traced_agent(obs):
            day = obs.get("day", 0)
            hour = obs.get("hour", 0)
            action = v2_agent.agent(obs)
            
            if day in [0, 1, 2, 3, 4, 5]:
                me = obs["farms"][obs["player"]]
                private = obs["private"]
                workers = [me["farmer"]] + me.get("hands", [])
                acts = [action.get("farmer")] + action.get("hands", [])
                
                tiles = me["tiles"]
                empty = [(x,y) for y in range(10) for x in range(10) if tiles[y][x] is None]
                plants = [(x,y) for y in range(10) for x in range(10) if isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") == "PLANT"]
                animals = [(x,y) for y in range(10) for x in range(10) if isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") in ("COOP", "PASTURE")]
                
                # Check if all workers are passing
                all_pass = all(a == ["PASS"] or a == "PASS" for a in acts)
                if all_pass or hour in [0, 6, 12, 18, 23]:
                    out.write(f"--- Day {day} Hour {hour:2d} --- (All PASS: {all_pass})\n")
                    out.write(f"Money: ${me['money']:.0f}, Shed: {private.get('shed', {})}, Seeds: {private.get('seeds', {})}\n")
                    out.write(f"Tiles: {len(empty)} empty, {len(plants)} plants, {len(animals)} animals\n")
                    out.write(f"Workers ({len(workers)}):\n")
                    for w_i, (w_pos, w_act) in enumerate(zip(workers, acts)):
                        inv = private["inventories"][w_i] if w_i < len(private["inventories"]) else {}
                        out.write(f"  w{w_i} at {w_pos}, inv={inv}: action={w_act}\n")
                    if action.get("market"):
                        out.write(f"  Market orders: {action.get('market')}\n")
                    out.write("\n")
                    
            return action

        env.run([traced_agent, "starter"])
    print("Done writing hourly_log.txt")

if __name__ == "__main__":
    inspect_hours()
