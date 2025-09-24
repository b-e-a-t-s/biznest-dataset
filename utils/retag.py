import os
import json

BASE_DIR = "utils/geojson"
ASSIGNED_CITIES = ["Pasay", "Makati", "Taguig"]
CACHE_FILE = os.path.join(BASE_DIR, "retag_cache.json")  # separate cache for retagging


def load_cache():
    """Load retag cache from disk."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save retag cache to disk."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def process_retag(geojson_path, cache):
    """Retag 'retail_store' to more specific amenities, modifying the annotated file directly."""
    work_file = geojson_path  # overwrite annotated file

    with open(work_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    targets = []
    for f in features:
        props = f.get("properties") or {}
        amenity = props.get("amenity")
        if amenity and str(amenity).lower() in ("retail_store", "retail store"):
            targets.append(f)

    if not targets:
        print(f"✅ No 'retail_store' entries in {geojson_path}")
        return

    total = len(targets)
    print(f"\n📊 Found {total} entries with 'retail_store' in {geojson_path}")

    for i, feature in enumerate(targets, 1):
        props = feature.get("properties") or {}
        name = str(props.get("name") or "").strip() or "Unnamed"

        # Use cache if available
        if name in cache:
            props["amenity"] = cache[name]
            print(f"[{i}/{total}] {name} → auto-retagged as {cache[name]}")
            continue

        print("\n--------------------------------")
        print(f"[{i}/{total}] Name: {name}")
        print(f"Coords: {feature['geometry']['coordinates']}")
        print(f"Current amenity: {props.get('amenity')}")

        while True:
            user_input = input(
                "Enter specific amenity (e.g., clothes, electronics, books) or 'q' to quit: "
            ).strip()
            if user_input.lower() == "q":
                print("⏸ Quitting... progress saved.")
                with open(work_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                save_cache(cache)
                return
            if user_input:
                props["amenity"] = user_input
                cache[name] = user_input  # save for reuse
                break
            else:
                print("❌ Amenity cannot be empty. Please enter a value.")

        # Save after each edit directly to the annotated file
        with open(work_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        save_cache(cache)
        print(f"💾 Progress saved to: {work_file}")


def main():
    cache = load_cache()

    for city in ASSIGNED_CITIES:
        city_path = os.path.join(BASE_DIR, city)
        if os.path.isdir(city_path):
            geojson_file = None
            for fname in os.listdir(city_path):
                if fname.endswith("_annotated.geojson"):  # use annotated files
                    geojson_file = os.path.join(city_path, fname)
                    break
            if geojson_file:
                print(f"\n=== Retagging {city} ===")
                process_retag(geojson_file, cache)

    save_cache(cache)
    print("\n✅ Retagging complete. Cache saved.")


if __name__ == "__main__":
    main()
