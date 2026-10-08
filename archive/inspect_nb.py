import json

with open('kaggriculture-a-smaller-market-shock.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i in [3, 4, 5, 6]:
    src = "".join(nb['cells'][i]['source'])
    print(f"=== CELL {i} (len {len(src)}) ===")
    print(src[:300])
    print("...\n")
