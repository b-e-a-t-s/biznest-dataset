import os
import json

BASE_DIR = "utils/geojson"
ASSIGNED_CITIES = ["Paranaque"]

import difflib


def filter_similar_amenities(amenities, cutoff=0.85):
    """
    Removes duplicates and groups similar amenities.
    Returns a cleaned list while preserving unique values.
    """
    normalized = {}
    for a in amenities:
        key = a.strip().lower()
        if key not in normalized:
            normalized[key] = a  # keep original casing of first occurrence

    cleaned = []
    seen = set()

    for item in normalized.values():
        if item in seen:
            continue

        # Find similar matches in the remaining list
        matches = difflib.get_close_matches(item, normalized.values(), cutoff=cutoff)

        # Pick the first as representative
        rep = matches[0]
        cleaned.append(rep)
        seen.update(matches)

        if len(matches) > 1:
            print(f"ℹ️ Grouped similar amenities: {matches} → kept '{rep}'")

    return sorted(cleaned)


def load_all_amenities(base_dir):
    """Load amenities from all amenities.txt files under geojson/"""
    all_amenities = set()
    for city in os.listdir(base_dir):
        city_path = os.path.join(base_dir, city)
        if os.path.isdir(city_path):
            amenities_file = os.path.join(city_path, "amenities.txt")
            if os.path.exists(amenities_file):
                with open(amenities_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            all_amenities.add(line)

    # 🔹 Apply filtering
    return filter_similar_amenities(sorted(all_amenities))


def process_geojson(geojson_path, all_amenities):
    """Open geojson, force user to input amenity for each feature, save progress"""

    # Prefer working on the _with_amenity file if it exists (resume progress)
    work_file = geojson_path.replace("_no_amenity.geojson", "_annotated.geojson")
    if os.path.exists(work_file):
        print(f"▶️ Resuming from existing file: {work_file}")
        path_to_load = work_file
    else:
        path_to_load = geojson_path

    with open(path_to_load, "r", encoding="utf-8") as f:
        data = json.load(f)

    unfinished = [
        f
        for f in data.get("features", [])
        if f.get("properties", {}).get("amenity") in (None, "")
    ]

    if not unfinished:
        print(f"✅ All features already annotated in {work_file}")
        return

    total = len(unfinished)
    for i, feature in enumerate(unfinished, 1):
        props = feature.get("properties", {})
        print("\n--------------------------------")
        print(f"[{i}/{total}]")
        print(f"Name: {props.get('name', 'Unnamed')}")
        print(f"Coords: {feature['geometry']['coordinates']}")
        print(f"Current amenity: {props.get('amenity')}")

        if all_amenities:
            print("Available amenities (from all cities):")
            for idx, a in enumerate(all_amenities, 1):
                print(f"{idx}. {a}")

        # Require valid input and retry until correct
        while True:
            user_input = input("Enter amenity (number or text, 'q' to quit): ").strip()

            if user_input.lower() == "q":
                print("⏸ Quitting... progress saved.")
                with open(work_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return

            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(all_amenities):
                    props["amenity"] = all_amenities[idx]
                    break
                else:
                    print("❌ Invalid number. Try again.")
            elif user_input:
                props["amenity"] = user_input
                break
            else:
                print("❌ Amenity cannot be empty. Please enter a value.")

        # Save progress after every valid edit
        with open(work_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Progress saved to: {work_file}")

    print(f"\n✅ Finished session (all amenities filled in {work_file})")


def main():
    # load one big amenity list
    all_amenities = load_all_amenities(BASE_DIR)

    for city in ASSIGNED_CITIES:
        city_path = os.path.join(BASE_DIR, city)
        if os.path.isdir(city_path):
            geojson_file = None

            # Find geojson file
            for fname in os.listdir(city_path):
                if fname.endswith("_Geographic_Data_no_amenity.geojson"):
                    geojson_file = os.path.join(city_path, fname)
                    break

            if geojson_file:
                print(f"\n=== Processing {city} ===")
                process_geojson(geojson_file, all_amenities)


if __name__ == "__main__":
    main()
