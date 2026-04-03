"""
APIs 39-42: Location, Maps & Weather
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import requests

router = APIRouter(prefix="/api/location", tags=["Location, Maps & Weather"])


# ── 39 Geocoding & Reverse Geocoding ─────────────────────────────────────────

@router.get("/geocode", summary="39 · Geocoding & Reverse Geocoding API")
def geocode(
    address: Optional[str] = Query(None, description="Address to geocode"),
    lat: Optional[float] = Query(None, description="Latitude for reverse geocoding"),
    lon: Optional[float] = Query(None, description="Longitude for reverse geocoding"),
):
    """Convert addresses to coordinates and vice versa. Global coverage."""
    try:
        if address:
            url = "https://nominatim.openstreetmap.org/search"
            resp = requests.get(url, params={"q": address, "format": "json", "limit": 5},
                                headers={"User-Agent": "RapidAPI-Platform/1.0"}, timeout=10)
            data = resp.json()
            results = [
                {
                    "display_name": r.get("display_name"),
                    "latitude": float(r.get("lat")),
                    "longitude": float(r.get("lon")),
                    "type": r.get("type"),
                    "importance": r.get("importance"),
                    "bounding_box": r.get("boundingbox"),
                }
                for r in data
            ]
            return {
                "status": "success",
                "api": "Geocoding",
                "query": address,
                "result_count": len(results),
                "results": results,
            }
        elif lat is not None and lon is not None:
            url = "https://nominatim.openstreetmap.org/reverse"
            resp = requests.get(url, params={"lat": lat, "lon": lon, "format": "json"},
                                headers={"User-Agent": "RapidAPI-Platform/1.0"}, timeout=10)
            data = resp.json()
            addr = data.get("address", {})
            return {
                "status": "success",
                "api": "Reverse Geocoding",
                "latitude": lat,
                "longitude": lon,
                "display_name": data.get("display_name"),
                "address": {
                    "house_number": addr.get("house_number"),
                    "road": addr.get("road"),
                    "suburb": addr.get("suburb"),
                    "city": addr.get("city") or addr.get("town") or addr.get("village"),
                    "county": addr.get("county"),
                    "state": addr.get("state"),
                    "postcode": addr.get("postcode"),
                    "country": addr.get("country"),
                    "country_code": addr.get("country_code", "").upper(),
                },
            }
        else:
            raise HTTPException(status_code=400, detail="Provide 'address' OR 'lat' and 'lon'")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(exc)}")


# ── 40 Weather Forecast ───────────────────────────────────────────────────────

@router.get("/weather", summary="40 · Weather Forecast API")
def weather_forecast(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    days: int = Query(7, ge=1, le=16, description="Forecast days"),
    units: str = Query("celsius", description="Temperature units: celsius | fahrenheit"),
):
    """Current conditions, 7-day forecasts, hourly data, UV index, air quality."""
    try:
        temp_unit = "celsius" if units.lower() == "celsius" else "fahrenheit"
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weathercode,windspeed_10m,uv_index",
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,sunrise,sunset,uv_index_max",
            "hourly": "temperature_2m,precipitation_probability,weathercode",
            f"temperature_unit": temp_unit,
            "wind_speed_unit": "kmh",
            "timezone": "auto",
            "forecast_days": days,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        wmo_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 61: "Slight rain",
            63: "Moderate rain", 65: "Heavy rain", 71: "Slight snow", 73: "Moderate snow",
            75: "Heavy snow", 80: "Slight showers", 81: "Moderate showers", 82: "Heavy showers",
            95: "Thunderstorm", 99: "Thunderstorm with hail",
        }

        current = data.get("current", {})
        daily = data.get("daily", {})
        forecast = []
        for i in range(len(daily.get("time", []))):
            code = daily["weathercode"][i] if daily.get("weathercode") else 0
            forecast.append({
                "date": daily["time"][i],
                "condition": wmo_codes.get(code, "Unknown"),
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "precipitation_mm": daily["precipitation_sum"][i],
                "wind_max_kmh": daily["windspeed_10m_max"][i],
                "sunrise": daily["sunrise"][i],
                "sunset": daily["sunset"][i],
                "uv_index": daily.get("uv_index_max", [None] * (i + 1))[i],
            })

        current_code = current.get("weathercode", 0)
        return {
            "status": "success",
            "api": "Weather Forecast",
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone"),
            "units": units,
            "current": {
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity_percent": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
                "wind_kmh": current.get("windspeed_10m"),
                "uv_index": current.get("uv_index"),
                "condition": wmo_codes.get(current_code, "Unknown"),
            },
            "forecast": forecast,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Weather API error: {str(exc)}")


# ── 41 Places & Points of Interest ───────────────────────────────────────────

@router.get("/places", summary="41 · Places & Points of Interest API")
def places_poi(
    lat: float = Query(..., description="Latitude of search center"),
    lon: float = Query(..., description="Longitude of search center"),
    category: str = Query("restaurant", description="Category: restaurant | hotel | hospital | school | cafe | park | atm | pharmacy"),
    radius_m: int = Query(1000, ge=100, le=50000, description="Search radius in metres"),
    limit: int = Query(10, ge=1, le=30),
):
    """Find restaurants, hotels, attractions, and businesses near any location."""
    try:
        amenity_map = {
            "restaurant": "amenity=restaurant",
            "hotel": "tourism=hotel",
            "hospital": "amenity=hospital",
            "school": "amenity=school",
            "cafe": "amenity=cafe",
            "park": "leisure=park",
            "atm": "amenity=atm",
            "pharmacy": "amenity=pharmacy",
            "mosque": "amenity=place_of_worship][religion=muslim",
            "ev_charging": "amenity=charging_station",
        }
        osm_filter = amenity_map.get(category, f"amenity={category}")

        overpass_query = f"""
        [out:json][timeout:15];
        node[{osm_filter}](around:{radius_m},{lat},{lon});
        out {limit};
        """
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": overpass_query},
            timeout=20,
        )
        data = resp.json()
        places = []
        for element in data.get("elements", [])[:limit]:
            tags = element.get("tags", {})
            places.append({
                "id": element.get("id"),
                "name": tags.get("name", "Unnamed"),
                "category": category,
                "latitude": element.get("lat"),
                "longitude": element.get("lon"),
                "address": tags.get("addr:full") or ", ".join(filter(None, [
                    tags.get("addr:housenumber"),
                    tags.get("addr:street"),
                    tags.get("addr:city"),
                ])),
                "phone": tags.get("phone"),
                "website": tags.get("website"),
                "opening_hours": tags.get("opening_hours"),
                "cuisine": tags.get("cuisine"),
                "stars": tags.get("stars"),
            })
        return {
            "status": "success",
            "api": "Places & Points of Interest",
            "center": {"lat": lat, "lon": lon},
            "category": category,
            "radius_m": radius_m,
            "place_count": len(places),
            "places": places,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Places API error: {str(exc)}")


# ── 42 Distance & Routing ─────────────────────────────────────────────────────

class WaypointIn(BaseModel):
    lat: float
    lon: float
    label: Optional[str] = None

class RouteIn(BaseModel):
    waypoints: List[WaypointIn]
    mode: Optional[str] = "driving"  # driving | walking | cycling

@router.post("/routing", summary="42 · Distance & Routing API")
def distance_routing(payload: RouteIn):
    """Calculate driving/walking/cycling distance and time between locations."""
    try:
        if len(payload.waypoints) < 2:
            raise HTTPException(status_code=400, detail="Provide at least 2 waypoints")

        profile_map = {
            "driving": "routed-car",
            "walking": "routed-foot",
            "cycling": "routed-bike",
        }
        profile = profile_map.get(payload.mode or "driving", "routed-car")
        coords = ";".join(f"{wp.lon},{wp.lat}" for wp in payload.waypoints)
        url = f"https://router.project-osrm.org/route/v1/{profile}/{coords}"
        params = {
            "overview": "simplified",
            "geometries": "geojson",
            "steps": "true",
            "annotations": "false",
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        if data.get("code") != "Ok":
            raise Exception(data.get("message", "Routing failed"))

        route = data["routes"][0]
        legs = route.get("legs", [])
        leg_details = []
        for leg in legs:
            steps = []
            for step in leg.get("steps", [])[:10]:
                maneuver = step.get("maneuver", {})
                steps.append({
                    "instruction": f"{maneuver.get('type', '')} {maneuver.get('modifier', '')}".strip(),
                    "distance_m": round(step.get("distance", 0)),
                    "duration_s": round(step.get("duration", 0)),
                    "name": step.get("name"),
                })
            leg_details.append({
                "distance_m": round(leg.get("distance", 0)),
                "duration_s": round(leg.get("duration", 0)),
                "distance_km": round(leg.get("distance", 0) / 1000, 2),
                "duration_minutes": round(leg.get("duration", 0) / 60, 1),
                "steps": steps,
            })
        return {
            "status": "success",
            "api": "Distance & Routing",
            "mode": payload.mode,
            "waypoints": [{"lat": wp.lat, "lon": wp.lon, "label": wp.label} for wp in payload.waypoints],
            "total_distance_km": round(route.get("distance", 0) / 1000, 2),
            "total_duration_minutes": round(route.get("duration", 0) / 60, 1),
            "legs": leg_details,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Routing error: {str(exc)}")
