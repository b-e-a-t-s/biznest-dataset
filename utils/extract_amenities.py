import json
import os


def process_geojson(geojson_path):
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    amenity_set = set()
    with_amenity = []
    no_amenity = []

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        amenity = props.get("amenity")

        if amenity is None:
            no_amenity.append(feature)
        else:
            amenity_set.add(amenity)
            with_amenity.append(feature)

    return amenity_set, with_amenity, no_amenity


def save_geojson(path, features):
    geojson = {"type": "FeatureCollection", "features": features}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))

    geojson_path = os.path.join(
        base_dir, "geojson", "Valenzuela", "Valenzuela_Geographic_Data.geojson"
    )  # /geojson/North Caloocan/North_Caloocan_Geographic_Data.geojson

    base_name = os.path.splitext(geojson_path)[0]

    amenity_set, with_amenity, no_amenity = process_geojson(geojson_path)

    save_geojson(base_name + "_with_amenity.geojson", with_amenity)
    save_geojson(base_name + "_no_amenity.geojson", no_amenity)

    amenities_txt_path = os.path.join(os.path.dirname(geojson_path), "amenities.txt")
    with open(amenities_txt_path, "w", encoding="utf-8") as f:
        for amenity in sorted(amenity_set):
            f.write(amenity + "\n")

    print("Unique amenities found:")
    print(list(amenity_set))
    print(f"\nSaved {len(with_amenity)} features to {base_name}_with_amenity.geojson")
    print(f"Saved {len(no_amenity)} features to {base_name}_no_amenity.geojson")
    print(f"Saved amenities list to {amenities_txt_path}")
