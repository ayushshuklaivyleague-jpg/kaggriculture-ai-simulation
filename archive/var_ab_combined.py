"""Variant AB: Combined Animal Accounting Fix + Opening Tile Optimization.
Tested across the fixed 10-game evaluation suite.
"""
import main as base_module
from var_a_animal_accounting import patched_generate_market_orders
from var_b_opening_tiles import patched_generate_tasks

def agent(obs):
    orig_tasks = base_module.generate_tasks
    orig_orders = base_module.generate_market_orders
    base_module.generate_tasks = patched_generate_tasks
    base_module.generate_market_orders = patched_generate_market_orders
    try:
        return base_module.agent(obs)
    finally:
        base_module.generate_tasks = orig_tasks
        base_module.generate_market_orders = orig_orders
