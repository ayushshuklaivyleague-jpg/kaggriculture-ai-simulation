"""Trace Days 9, 10, 11 turn by turn."""
import kaggle_environments
import main as v2_agent

def trace_harvest(seed=29453000):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    
    with open("harvest_log.txt", "w", encoding="utf-8") as out:
        def traced_agent(obs):
            day = obs.get("day", 0)
            hour = obs.get("hour", 0)
            action = v2_agent.agent(obs)
            
            if day in [9, 10, 11]:
                me = obs["farms"][obs["player"]]
                private = obs["private"]
                out.write(f"Day {day:2d} Hour {hour:2d}: Money=${me['money']:.0f}, Shed={dict(private.get('shed', {}))}\n")
                # check workers inventories
                invs = [inv for inv in private.get("inventories", []) if inv]
                if invs:
                    out.write(f"  Worker inventories: {invs}\n")
                if action.get("market"):
                    out.write(f"  Market: {action.get('market')}\n")
                # count harvest actions
                acts = [action.get("farmer")] + action.get("hands", [])
                h_acts = [a for a in acts if a and a[0] == "HARVEST"]
                if h_acts:
                    out.write(f"  HARVEST actions: {len(h_acts)}\n")
            return action

        env.run([traced_agent, "starter"])
    print("Done writing harvest_log.txt")

if __name__ == "__main__":
    trace_harvest()
