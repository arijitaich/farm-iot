import requests

def estimate_soil_moisture(coord_str):
    try:
        lat_str, lon_str = coord_str.split(",")
        lat = float(lat_str.strip())
        lon = float(lon_str.strip())
    except ValueError:
        return {"error": "Invalid coordinate format. Use 'lat,lon'"}

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
    )

    try:
        response = requests.get(url)
        if response.status_code == 200:
            current = response.json().get("current", {})
            temp = current.get("temperature_2m")
            rh = current.get("relative_humidity_2m")

            if temp is not None and rh is not None:
                # Empirical estimation
                estimated_soil_moisture = rh / (temp + 1)
                return {
                    "temperature_celsius": temp,
                    "humidity_percent": rh,
                    "estimated_soil_moisture_index": round(estimated_soil_moisture, 2)
                }
            else:
                return {"error": "Temperature or humidity not found"}
        else:
            return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Example usage
    coord_str = "23.9051278442229,87.7869049832224"  # San Francisco coordinates
    data = estimate_soil_moisture(coord_str)
    print(data)