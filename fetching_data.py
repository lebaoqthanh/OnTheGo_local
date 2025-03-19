import sys
import os
from dotenv import load_dotenv
import serpapi
import json
import traceback

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

if len(sys.argv) < 3:
    print('Usage: python fetching_data.py <latitude> <longitude> [amenity]')
    sys.exit(1)

try:
    latitude = float(sys.argv[1])
    longitude = float(sys.argv[2])
except ValueError as ve:
    print("[ERROR] Invalid latitude or longitude:", ve)
    sys.exit(1)

amenity = sys.argv[3] if len(sys.argv) >= 4 else "restaurant"

serp_api_key = os.getenv('SERPAPI_KEY')
if not serp_api_key:
    print("Error: SERPAPI_KEY not found in environment variables.")
    sys.exit(1)

client = serpapi.Client(api_key=serp_api_key)

def generate_ll_param(lat, lon, zoom=16):
    return f"@{lat},{lon},{zoom}z"

def main():
    try:
        ll_param = generate_ll_param(latitude, longitude)
        params = {
            'engine': 'google_maps',
            'q': amenity,
            'type': 'search',
            'll': ll_param
        }

        results = client.search(params)
        locations = results.get("places_results") or results.get("local_results") or results.get("results") or []
        locations = locations[:5]

        output_data = []
        for loc in locations:
            gps = loc.get("gps_coordinates", {})
            lat_val = gps.get("latitude")
            lon_val = gps.get("longitude")
            if lat_val is None or lon_val is None:
                geo = loc.get("geometry", {}).get("location", {})
                lat_val = geo.get("lat")
                lon_val = geo.get("lng")
            output_data.append({
                "Name": loc.get("title"),
                "Address": loc.get("address"),
                "Rating": loc.get("rating"),
                "Price": loc.get("price"),
                "Opening Hour": loc.get("hours", loc.get("open_state")),
                "Latitude": lat_val,
                "Longitude": lon_val
            })

        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4)

        print(f"[INFO] result.json saved with {len(output_data)} results.")
    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
