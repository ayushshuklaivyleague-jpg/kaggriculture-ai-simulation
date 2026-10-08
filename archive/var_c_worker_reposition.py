"""Variant C: Worker End-of-Day Idle Repositioning and Immediate Shed DROP.
Tested against CURRENT BASELINE directly.
"""
import main as base_module

_ORIG_SCHEDULE_WORKERS = base_module.schedule_workers

def patched_schedule_workers(workers, inventories, tasks, shed, seeds):
    # Call the original base scheduler
    actions = _ORIG_SCHEDULE_WORKERS(workers, inventories, tasks, shed, seeds)
    
    # Now inspect any worker that was assigned ["PASS"]
    for w_i, act in enumerate(actions):
        if act == ["PASS"]:
            w_pos = workers[w_i]
            w_inv = inventories[w_i] if w_i < len(inventories) else {}
            
            # Check if carrying any harvested produce
            has_produce = any(qty > 0 for item, qty in w_inv.items()
                              if item in base_module.MP or item in ("GOOSE", "COW", "SHEEP"))
            
            if has_produce:
                if base_module.is_shed_adjacent(w_pos):
                    actions[w_i] = ["DROP"]
                else:
                    shed_pos = base_module.nearest_shed_tile(w_pos)
                    actions[w_i] = [base_module.move_towards(w_pos, shed_pos)]
            elif w_i == 0:  # Main farmer repositioning towards central hub (4,4)
                if not base_module.is_shed_adjacent(w_pos):
                    actions[w_i] = [base_module.move_towards(w_pos, (4, 4))]
                    
    return actions

def agent(obs):
    base_module.schedule_workers = patched_schedule_workers
    try:
        return base_module.agent(obs)
    finally:
        base_module.schedule_workers = _ORIG_SCHEDULE_WORKERS
