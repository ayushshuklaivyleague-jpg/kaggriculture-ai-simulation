"""Variant B: Opening Tile Optimization — Defer empty structure construction until animals are affordable.
Tested against CURRENT BASELINE directly.
"""
import main as base_module

def patched_generate_tasks(day: int, hour: int, tiles, shed, seeds,
                           market_inv, shops, chosen_crop, chosen_animal,
                           target_animal_count):
    empty, plants, animals, structs_empty, weeds = base_module.scan_tiles(tiles)
    tasks = []

    plant_priority = max(10, int(50 - day * 1.2))
    current_animal_count = len(animals)
    
    # Check if we can afford animals before dedicating valuable land to empty structures
    # On day 0-10, if we cannot afford animals, do not build structures that sit empty!
    can_afford_animal = True
    if chosen_animal and current_animal_count == 0:
        a_cost = base_module.ANIMAL[chosen_animal]["cost"]
        # If early in the game (day < 10) and no animals owned yet, don't waste tiles on empty pastures
        # if money cannot even afford 1 animal + buffer
        # In fact, if day < 10, melons are growing, so don't leave 4 tiles empty for 10 days!
        if day < 10:
            can_afford_animal = False
            
    if can_afford_animal:
        structures_needed = max(0, target_animal_count - current_animal_count - len(structs_empty))
    else:
        structures_needed = 0
        
    build_slots = 0

    for pos in empty:
        if build_slots < structures_needed and chosen_animal:
            struct_type = base_module.ANIMAL[chosen_animal]["structure"]
            tasks.append((plant_priority + 10, pos, "BUILD", {"structure": struct_type}))
            build_slots += 1
        else:
            tasks.append((plant_priority, pos, "PLANT", {"crop": chosen_crop}))

    for pos, tile in plants:
        crop_name = tile.get("crop", "")
        if not crop_name or crop_name not in base_module.CROP:
            continue
        c = base_module.CROP[crop_name]
        age = day - tile.get("planted_day", day)
        watered = tile.get("watered_today", False)
        consec_unwatered = tile.get("consecutive_unwatered", 0)
        yield_units = tile.get("yield_units", 0)

        if not watered:
            urgency = 200 if consec_unwatered >= 1 else 100
            tasks.append((urgency, pos, "WATER", {}))

        if c["type"] == "onetime":
            if yield_units > 0 and age >= c["first"]:
                at_max = yield_units >= c["unfert_yield"]
                near_decay = age >= c["max_day"]
                endgame = day >= 27
                if at_max or near_decay or endgame:
                    tasks.append((90, pos, "HARVEST", {}))
        else:
            if yield_units > 0:
                max_h = c["max_yield"]
                urgency = 95 if yield_units >= max_h - 1 else 70
                tasks.append((urgency, pos, "HARVEST", {}))

        if c["type"] == "onetime" and c["bonus_start"] > 0:
            fert_until = tile.get("fertilized_until_day", -1)
            in_window = c["bonus_start"] <= age <= c["max_day"]
            not_already_fert = fert_until < day
            if in_window and not_already_fert:
                extra_yield = min(3, c["max_yield"] - c["unfert_yield"])
                if extra_yield > 0:
                    sell_price = base_module.compute_price(crop_name, market_inv.get(crop_name, 10000))
                    fert_cost = base_module.compute_price("FERTILIZER", market_inv.get("FERTILIZER", 10000))
                    if extra_yield * sell_price > fert_cost * 1.5:
                        tasks.append((60, pos, "FERTILIZE", {}))

    for pos, tile in animals:
        animal_name = tile.get("animal", "")
        if not animal_name:
            continue
        fed = tile.get("fed_today", False)
        consec_unfed = tile.get("consecutive_unfed", 0)
        cared = tile.get("cared_today", False)
        fert_avail = tile.get("fertilizer_available", False)
        yield_units = tile.get("yield_units", 0)

        if not fed:
            urgency = 210 if consec_unfed >= 1 else 105
            tasks.append((urgency, pos, "FEED", {}))

        if not cared and fed:
            tasks.append((80, pos, "CARE", {}))

        if fert_avail:
            tasks.append((55, pos, "COLLECT_FERT", {}))

        if yield_units > 0:
            a_info = base_module.ANIMAL.get(animal_name, {})
            max_h = a_info.get("max_held", 4)
            urgency = 92 if yield_units >= max_h - 1 else 75
            tasks.append((urgency, pos, "HARVEST", {}))

    for pos, tile in structs_empty:
        if chosen_animal:
            expected_struct = base_module.ANIMAL[chosen_animal]["structure"]
            if tile.get("kind") == expected_struct:
                tasks.append((85, pos, "PLACE", {"animal": chosen_animal}))

    for pos in weeds:
        tasks.append((20, pos, "DIG", {}))

    tasks.sort(key=lambda t: -t[0])
    return tasks

def agent(obs):
    orig_fn = base_module.generate_tasks
    base_module.generate_tasks = patched_generate_tasks
    try:
        return base_module.agent(obs)
    finally:
        base_module.generate_tasks = orig_fn
