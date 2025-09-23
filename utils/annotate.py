import os
import json
import difflib

BASE_DIR = "utils/geojson"
ASSIGNED_CITIES = ["Pasay", "Makati", "Taguig"]
CACHE_FILE = os.path.join(BASE_DIR, "amenity_cache.json")


def load_cache():
    """Load amenity cache from disk."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save amenity cache to disk."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def filter_similar_amenities(amenities, cutoff=0.85):
    """Removes duplicates and groups similar amenities."""
    normalized = {}
    for a in amenities:
        key = a.strip().lower()
        if key not in normalized:
            normalized[key] = a

    cleaned = []
    seen = set()

    for item in normalized.values():
        if item in seen:
            continue
        matches = difflib.get_close_matches(item, normalized.values(), cutoff=cutoff)
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
    return filter_similar_amenities(sorted(all_amenities))


def load_city_features(city_path):
    """Load all features in a city folder"""
    features = []
    for fname in os.listdir(city_path):
        if fname.endswith("_Geographic_Data_no_amenity.geojson"):
            with open(os.path.join(city_path, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
                features.extend(data.get("features", []))
    return features


def build_name_frequency(all_features):
    """
    Returns {name: count} for detecting chain stores.
    Skip features with missing or empty names.
    """
    freq = {}
    for feature in all_features:
        props = feature.get("properties") or {}
        raw_name = props.get("name")
        if not raw_name:  # skip None or empty
            continue
        name = str(raw_name).strip()
        if name:
            freq[name] = freq.get(name, 0) + 1
    return freq


def prefill_chains(cache, name_frequency, all_amenities):
    """
    Prompt the user for unknown chains and pre-fill the cache.
    Only prompts once per chain name.
    """
    for name, count in name_frequency.items():
        if count > 1 and name not in cache:
            print(f"⚡ Detected chain (appears {count} times): {name}")
            while True:
                user_input = input(f"Enter amenity for chain '{name}': ").strip()
                if user_input:
                    cache[name] = user_input
                    break
                print("❌ Amenity cannot be empty. Please enter a value.")
    save_cache(cache)


def process_geojson(geojson_path, all_amenities, cache):
    """Annotate geojson using pre-built cache"""
    work_file = geojson_path.replace("_no_amenity.geojson", "_annotated.geojson")
    path_to_load = work_file if os.path.exists(work_file) else geojson_path

    with open(path_to_load, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    total_entries = len(features)

    # Auto-fill all missing amenities from cache right away
    filled_from_cache = 0
    for feature in features:
        props = feature.get("properties") or {}
        if not props.get("amenity"):
            name = str(props.get("name") or "").strip()
            if name in cache:
                props["amenity"] = cache[name]
                filled_from_cache += 1
                print(f"✅ Auto-filled from cache: {name} → {cache[name]}")

    # Figure out how many are done vs left
    filled_count = sum(
        1 for f in features if (f.get("properties") or {}).get("amenity")
    )
    unfinished = [f for f in features if not (f.get("properties") or {}).get("amenity")]
    to_fill = len(unfinished)

    print(
        f"\n📊 {total_entries} total entries. "
        f"{filled_count} already filled "
        f"({filled_from_cache} from cache), {to_fill} left to annotate."
    )

    # Interactive loop
    for i, feature in enumerate(unfinished, 1):
        props = feature.get("properties") or {}
        name = str(props.get("name") or "").strip() or "Unnamed"

        # progress = how many are already filled (including past + current index)
        current_progress = filled_count + i
        print("\n--------------------------------")
        print(f"[{current_progress}/{total_entries}] Name: {name}")
        print(f"Coords: {feature['geometry']['coordinates']}")
        print(f"Current amenity: {props.get('amenity')}")

        if all_amenities:
            print("Available amenities (from all cities):")
            for idx, a in enumerate(all_amenities, 1):
                print(f"{idx}. {a}")

        while True:
            user_input = input("Enter amenity (number or text, 'q' to quit): ").strip()
            if user_input.lower() == "q":
                print("⏸ Quitting... progress saved.")
                with open(work_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                save_cache(cache)
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

        # Save progress after each manual edit
        with open(work_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        save_cache(cache)
        print(f"💾 Progress saved to: {work_file}")


def main():
    all_amenities = load_all_amenities(BASE_DIR)
    cache = load_cache()

    # 🔹 Collect all features to build name frequency
    all_features = []
    for city in ASSIGNED_CITIES:
        city_path = os.path.join(BASE_DIR, city)
        if os.path.isdir(city_path):
            all_features.extend(load_city_features(city_path))

    name_frequency = build_name_frequency(all_features)

    # 🔹 Prefill cache for chains before starting annotation
    prefill_chains(cache, name_frequency, all_amenities)

    # 🔹 Process each city using pre-built cache
    for city in ASSIGNED_CITIES:
        city_path = os.path.join(BASE_DIR, city)
        if os.path.isdir(city_path):
            geojson_file = None
            for fname in os.listdir(city_path):
                if fname.endswith("_Geographic_Data_no_amenity.geojson"):
                    geojson_file = os.path.join(city_path, fname)
                    break
            if geojson_file:
                print(f"\n=== Processing {city} ===")
                process_geojson(geojson_file, all_amenities, cache)

    save_cache(cache)
    print("\n✅ All cities processed. Cache saved.")


if __name__ == "__main__":
    main()
