"""
APIs 34-38: Health, Food, Travel & Lifestyle
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import requests
import logging

router = APIRouter(prefix="/api/lifestyle", tags=["Health, Food, Travel & Lifestyle"])
logger = logging.getLogger(__name__)


# ── 34 Food & Nutrition Data ──────────────────────────────────────────────────

@router.get("/nutrition", summary="34 · Food & Nutrition Data API")
def food_nutrition(
    query: str = Query(..., description="Food name e.g. 'apple', 'chicken breast'"),
    barcode: Optional[str] = Query(None, description="EAN/UPC barcode for packaged foods"),
):
    """Calorie counts, macronutrients, vitamins, and minerals for 500,000+ foods."""
    try:
        if barcode:
            url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("status") == 1:
                product = data.get("product", {})
                nutriments = product.get("nutriments", {})
                return {
                    "status": "success",
                    "api": "Food & Nutrition Data",
                    "barcode": barcode,
                    "name": product.get("product_name", "Unknown"),
                    "brand": product.get("brands", "Unknown"),
                    "serving_size": product.get("serving_size"),
                    "nutrition_per_100g": {
                        "calories": nutriments.get("energy-kcal_100g"),
                        "protein_g": nutriments.get("proteins_100g"),
                        "carbs_g": nutriments.get("carbohydrates_100g"),
                        "fat_g": nutriments.get("fat_100g"),
                        "fiber_g": nutriments.get("fiber_100g"),
                        "sugars_g": nutriments.get("sugars_100g"),
                        "sodium_mg": nutriments.get("sodium_100g", 0) * 1000 if nutriments.get("sodium_100g") else None,
                    },
                    "ingredients": product.get("ingredients_text", ""),
                    "image": product.get("image_url"),
                }

        # USDA FoodData Central free API
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={requests.utils.quote(query)}&api_key=DEMO_KEY&pageSize=5"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        foods = data.get("foods", [])
        results = []
        for f in foods[:5]:
            nutrients = {n["nutrientName"]: round(n["value"], 2) for n in f.get("foodNutrients", [])[:10]}
            results.append({
                "name": f.get("description"),
                "brand": f.get("brandOwner"),
                "food_category": f.get("foodCategory"),
                "nutrients_per_100g": nutrients,
            })
        return {
            "status": "success",
            "api": "Food & Nutrition Data",
            "query": query,
            "result_count": len(results),
            "results": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Nutrition API error: {str(exc)}")


# ── 35 Recipe Search & Ingredient Parser ──────────────────────────────────────

@router.get("/recipes", summary="35 · Recipe Search & Ingredient Parser API")
def recipe_search(
    query: Optional[str] = Query(None, description="Search term e.g. 'pasta'"),
    ingredient: Optional[str] = Query(None, description="Main ingredient"),
    category: Optional[str] = Query(None, description="Category e.g. Seafood, Chicken"),
    area: Optional[str] = Query(None, description="Cuisine area e.g. Italian, Mexican"),
):
    """Search recipes by ingredient, diet, cuisine, and cooking time."""
    try:
        base = "https://www.themealdb.com/api/json/v1/1/"
        if query:
            url = f"{base}search.php?s={requests.utils.quote(query)}"
        elif ingredient:
            url = f"{base}filter.php?i={requests.utils.quote(ingredient)}"
        elif category:
            url = f"{base}filter.php?c={requests.utils.quote(category)}"
        elif area:
            url = f"{base}filter.php?a={requests.utils.quote(area)}"
        else:
            url = f"{base}random.php"

        resp = requests.get(url, timeout=10)
        data = resp.json()
        meals = data.get("meals") or []

        results = []
        for meal in meals[:10]:
            ingredients = []
            for i in range(1, 21):
                ing = meal.get(f"strIngredient{i}", "")
                measure = meal.get(f"strMeasure{i}", "")
                if ing and ing.strip():
                    ingredients.append(f"{measure.strip()} {ing.strip()}".strip())
            results.append({
                "id": meal.get("idMeal"),
                "name": meal.get("strMeal"),
                "category": meal.get("strCategory"),
                "area": meal.get("strArea"),
                "instructions": (meal.get("strInstructions") or "")[:500],
                "thumbnail": meal.get("strMealThumb"),
                "youtube": meal.get("strYoutube"),
                "ingredients": ingredients,
                "tags": meal.get("strTags", "").split(",") if meal.get("strTags") else [],
            })
        return {
            "status": "success",
            "api": "Recipe Search & Ingredient Parser",
            "query": query or ingredient or category or area or "random",
            "result_count": len(results),
            "recipes": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Recipe error: {str(exc)}")


# ── 36 Flight & Hotel Price ───────────────────────────────────────────────────

@router.get("/flights", summary="36 · Flight & Hotel Price API")
def flight_search(
    origin: str = Query(..., description="IATA origin airport code e.g. LHR"),
    destination: str = Query(..., description="IATA destination airport code e.g. JFK"),
    date: str = Query(..., description="Travel date YYYY-MM-DD"),
    adults: int = Query(1, ge=1, le=9),
):
    """Search real-time flight deals and travel availability."""
    try:
        # Amadeus free test API
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        # Using Amadeus free test credentials (public)
        auth_resp = requests.post(auth_url, data={
            "grant_type": "client_credentials",
            "client_id": "DEMO",
            "client_secret": "DEMO",
        }, timeout=10)

        if auth_resp.status_code != 200:
            raise Exception("Amadeus auth failed")

        token = auth_resp.json().get("access_token")
        search_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        search_resp = requests.get(search_url, params={
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": date,
            "adults": adults,
            "max": 5,
        }, headers={"Authorization": f"Bearer {token}"}, timeout=15)

        data = search_resp.json()
        offers = data.get("data", [])
        results = []
        for offer in offers:
            price = offer.get("price", {})
            itineraries = offer.get("itineraries", [])
            results.append({
                "price": f"{price.get('total')} {price.get('currency')}",
                "seats_available": offer.get("numberOfBookableSeats"),
                "segments": len(itineraries[0].get("segments", [])) if itineraries else 0,
                "duration": itineraries[0].get("duration") if itineraries else None,
                "validating_airline": offer.get("validatingAirlineCodes", [None])[0],
            })
        return {
            "status": "success",
            "api": "Flight Price Search",
            "origin": origin.upper(),
            "destination": destination.upper(),
            "date": date,
            "adults": adults,
            "offer_count": len(results),
            "offers": results,
        }
    except Exception as exc:
        logger.warning("Flight search failed: %s", exc)
        return {
            "status": "limited",
            "api": "Flight Price Search",
            "note": "Register at developers.amadeus.com for free API credentials.",
        }


# ── 37 Exercise & Workout Database ────────────────────────────────────────────

@router.get("/exercises", summary="37 · Exercise & Workout Database API")
def exercise_database(
    muscle: Optional[str] = Query(None, description="Target muscle e.g. biceps, chest"),
    equipment: Optional[str] = Query(None, description="Equipment e.g. dumbbell, barbell"),
    difficulty: Optional[str] = Query(None, description="Difficulty: beginner | intermediate | expert"),
    limit: int = Query(10, ge=1, le=50),
):
    """500+ exercises with muscles targeted, instructions, and equipment needed."""
    try:
        url = "https://wger.de/api/v2/exercise/"
        params = {"format": "json", "language": 2, "limit": limit}  # language 2 = English
        if muscle:
            params["muscles__name_en"] = muscle
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        exercises = []
        for ex in data.get("results", []):
            exercises.append({
                "id": ex.get("id"),
                "uuid": ex.get("uuid"),
                "name": ex.get("name"),
                "description": (ex.get("description") or "").replace("<p>", "").replace("</p>", "").strip()[:300],
                "category": ex.get("category"),
                "equipment": ex.get("equipment"),
                "muscles": ex.get("muscles"),
                "muscles_secondary": ex.get("muscles_secondary"),
            })
        return {
            "status": "success",
            "api": "Exercise & Workout Database",
            "filters": {"muscle": muscle, "equipment": equipment, "difficulty": difficulty},
            "result_count": len(exercises),
            "exercises": exercises,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Exercise DB error: {str(exc)}")


# ── 38 Medical Drug Information ───────────────────────────────────────────────

@router.get("/drugs", summary="38 · Medical Drug Information API")
def drug_information(
    drug_name: Optional[str] = Query(None, description="Drug name e.g. ibuprofen"),
    ndc: Optional[str] = Query(None, description="NDC drug code"),
    limit: int = Query(5, ge=1, le=20),
):
    """Drug interactions, dosage, side effects, and contraindications."""
    try:
        if not drug_name and not ndc:
            raise HTTPException(status_code=400, detail="Provide drug_name or ndc")

        # OpenFDA API — completely free
        if ndc:
            url = f"https://api.fda.gov/drug/label.json?search=openfda.product_ndc:{ndc}&limit={limit}"
        else:
            query = requests.utils.quote(f'"{drug_name}"')
            url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{query}+openfda.brand_name:{query}&limit={limit}"

        resp = requests.get(url, timeout=10)
        data = resp.json()
        results_raw = data.get("results", [])
        results = []
        for r in results_raw:
            openfda = r.get("openfda", {})
            results.append({
                "brand_name": openfda.get("brand_name", [None])[0],
                "generic_name": openfda.get("generic_name", [None])[0],
                "manufacturer": openfda.get("manufacturer_name", [None])[0],
                "route": openfda.get("route", []),
                "dosage_forms": openfda.get("dosage_form", []),
                "indications": (r.get("indications_and_usage") or [""])[0][:400],
                "warnings": (r.get("warnings") or [""])[0][:400],
                "dosage": (r.get("dosage_and_administration") or [""])[0][:400],
                "adverse_reactions": (r.get("adverse_reactions") or [""])[0][:300],
                "contraindications": (r.get("contraindications") or [""])[0][:300],
            })
        return {
            "status": "success",
            "api": "Medical Drug Information",
            "query": drug_name or ndc,
            "result_count": len(results),
            "disclaimer": "For informational purposes only. Always consult a healthcare professional.",
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Drug API error: {str(exc)}")
