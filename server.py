from flask import Flask, request, jsonify, send_from_directory
import json
import subprocess
import os
import time
import sys

app = Flask(__name__)

# File and script names
FETCHING_DATA_SCRIPT = "fetching_data.py"
RESTAURANT_JSON = "restaurant.json"
HOTEL_JSON = "hotel.json"
RESULT_JSON = "result.json"

# ✅ **1. Serve the InteractiveMap.html page**
@app.route('/')
def serve_html():
    return send_from_directory('.', 'InteractiveMap.html')

# ✅ **2. Automatically fetch restaurants & hotels when a location is selected**
@app.route('/search_location', methods=['POST'])
def search_location():
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')

    if lat is None or lon is None:
        return jsonify({"error": "Missing latitude or longitude"}), 400

    results = {}

    # Run fetching script twice: once for restaurants, once for hotels
    for amenity, outfile in [('restaurant', RESTAURANT_JSON), ('hotel', HOTEL_JSON)]:
        if os.path.exists(RESULT_JSON):
            os.remove(RESULT_JSON)  # Ensure result.json is fresh for each run.

        cmd = [sys.executable, FETCHING_DATA_SCRIPT, str(lat), str(lon), amenity]
        print(f"Executing: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Error fetching {amenity}: {e.stderr}"}), 500

        # **Wait for result.json to be created**
        start_time = time.time()
        timeout = 5
        while not os.path.exists(RESULT_JSON):
            if (time.time() - start_time) > timeout:
                return jsonify({"error": f"{RESULT_JSON} not found after fetching {amenity}"}), 500
            time.sleep(0.5)

        # **Rename result.json to restaurant.json or hotel.json**
        try:
            os.rename(RESULT_JSON, outfile)
        except Exception as ex:
            return jsonify({"error": f"Failed to rename {RESULT_JSON} to {outfile}: {str(ex)}"}), 500

        # **Read & store results**
        try:
            with open(outfile, "r", encoding="utf-8") as f:
                results[amenity] = json.load(f)
        except Exception as ex:
            return jsonify({"error": f"Error reading {outfile}: {str(ex)}"}), 500

    return jsonify({"message": "Location search completed", "results": results})

# ✅ **3. Fetching data dynamically for restaurants & hotels**
@app.route('/fetching_data', methods=['POST'])
def run_fetching_data():
    data = request.json
    lat = data.get('latitude')
    lon = data.get('longitude')
    amenity = data.get('amenity', 'restaurant')

    if lat is None or lon is None:
        return jsonify({"error": "Missing lat/lon"}), 400

    print(f"Received /fetching_data: lat={lat}, lon={lon}, amenity={amenity}")

    if not os.path.exists(FETCHING_DATA_SCRIPT):
        return jsonify({"error": f"{FETCHING_DATA_SCRIPT} not found"}), 500

    # Run fetching_data.py script
    cmd = [sys.executable, FETCHING_DATA_SCRIPT, str(lat), str(lon), amenity]
    print("Executing:", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("fetching_data.py stdout:\n", result.stdout)
        if result.stderr:
            print("fetching_data.py stderr:\n", result.stderr)
    except subprocess.CalledProcessError as e:
        print("Error during subprocess call:", e.stderr)
        return jsonify({"error": f"fetching_data failed: {e.stderr}"}), 500
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

    # **Wait for result.json**
    start_time = time.time()
    timeout = 5
    while not os.path.exists(RESULT_JSON):
        if (time.time() - start_time) > timeout:
            return jsonify({"error": "result.json not found after running fetching_data"}), 500
        time.sleep(0.5)

    try:
        with open(RESULT_JSON, "r", encoding="utf-8") as f:
            recommendations = json.load(f)
        if not isinstance(recommendations, list):
            return jsonify({"error": "Invalid format in result.json"}), 500

        return jsonify(recommendations)

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON in result.json"}), 500

# ✅ **4. Serve restaurant data**
@app.route('/restaurant_data', methods=['GET'])
def restaurant_data():
    try:
        with open(RESTAURANT_JSON, "r") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "restaurant.json not found"}), 404

# ✅ **5. Serve hotel data**
@app.route('/hotel_data', methods=['GET'])
def hotel_data():
    try:
        with open(HOTEL_JSON, "r") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "hotel.json not found"}), 404

# ✅ **6. Handle user search queries & save results in result.json**
@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    query = data.get('query', '').strip()

    if lat is None or lon is None or not query:
        return jsonify({"error": "Missing latitude, longitude, or query"}), 400

    # Clean previous result
    if os.path.exists(RESULT_JSON):
        os.remove(RESULT_JSON)

    cmd = [sys.executable, FETCHING_DATA_SCRIPT, str(lat), str(lon), query]
    print(f"Executing recommendations: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Error fetching recommendations: {e.stderr}"}), 500

    # **Wait for result.json**
    start_time = time.time()
    timeout = 5
    while not os.path.exists(RESULT_JSON):
        if (time.time() - start_time) > timeout:
            return jsonify({"error": "result.json not found after fetching recommendations"}), 500
        time.sleep(0.5)

    # Read & return recommendations
    try:
        with open(RESULT_JSON, "r", encoding="utf-8") as f:
            recommendations = json.load(f)
        return jsonify({"message": "Recommendations fetched", "recommendations": recommendations})
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON in result.json"}), 500

# ✅ **7. Start the Flask server with the correct host & port**
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
