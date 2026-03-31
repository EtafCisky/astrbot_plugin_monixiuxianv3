import json

# Load files
with open('config/alchemy_recipes.json', 'r', encoding='utf-8') as f:
    recipes = json.load(f)

with open('config/items.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

# Get all herb names from recipes
herbs_in_recipes = set()
for recipe in recipes:
    if 'materials' in recipe:
        for herb_name in recipe['materials'].keys():
            herbs_in_recipes.add(herb_name)

# Get all material names from items
herbs_in_items = {}
for item_id, item_data in items.items():
    if item_data.get('type') == '材料':
        herbs_in_items[item_data['name']] = item_id

# Find missing herbs
missing = []
for herb_name in sorted(herbs_in_recipes):
    if herb_name not in herbs_in_items:
        missing.append(herb_name)

print("=== Herbs in recipes but NOT in items.json ===")
for herb in missing:
    print(f"  - {herb}")

print(f"\n=== Summary ===")
print(f"Total unique herbs in recipes: {len(herbs_in_recipes)}")
print(f"Total herbs in items.json: {len(herbs_in_items)}")
print(f"Missing herbs: {len(missing)}")

if not missing:
    print("\n✓ All herbs from recipes are present in items.json!")
