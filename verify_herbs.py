import json

# Load items
with open('config/items.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

# Required herb IDs from requirements document
required_herbs = {
    "凡品": [2002, 2020, 2021, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2122, 2123, 2124, 2126, 2127, 2128, 2129],
    "珍品": [2022, 2023, 2024, 2025, 2026, 2027, 2006, 2004, 2014, 2200, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 2220, 2221, 2222, 2223, 2224, 2225, 2226],
    "圣品": [2028, 2029, 2030, 2300, 2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311, 2312, 2313, 2314, 2315, 2316, 2317, 2318, 2319, 2320, 2321, 2322],
    "帝品": [2400, 2401, 2402, 2403, 2404, 2405, 2406, 2407, 2408, 2409, 2410, 2411, 2412, 2413, 2414, 2415, 2416, 2417],
    "道品": [2500, 2501, 2502, 2503, 2504, 2505, 2506, 2507, 2508, 2509, 2510, 2511],
    "仙品": [2600, 2601, 2602, 2603, 2604, 2605, 2606, 2607],
    "神品": [2700, 2701, 2702, 2703, 2704]
}

print("=== Verifying Required Herbs ===\n")

total_required = 0
total_found = 0
all_missing = []

for rank, herb_ids in required_herbs.items():
    print(f"{rank} ({len(herb_ids)} required):")
    missing = []
    for herb_id in herb_ids:
        herb_id_str = str(herb_id)
        total_required += 1
        if herb_id_str in items:
            item = items[herb_id_str]
            if item.get('type') == '材料' and item.get('rank') == rank:
                total_found += 1
                print(f"  ✓ {herb_id}: {item['name']}")
            else:
                missing.append(f"{herb_id} (wrong type/rank: {item.get('type')}/{item.get('rank')})")
        else:
            missing.append(f"{herb_id} (not found)")
            all_missing.append((rank, herb_id))
    
    if missing:
        print(f"  ✗ Missing/Wrong:")
        for m in missing:
            print(f"    - {m}")
    print()

print(f"\n=== Summary ===")
print(f"Total required: {total_required}")
print(f"Total found: {total_found}")
print(f"Missing: {len(all_missing)}")

if all_missing:
    print(f"\n=== All Missing Herbs ===")
    for rank, herb_id in all_missing:
        print(f"  {rank}: {herb_id}")
else:
    print("\n✓ All required herbs are present!")
