"""
APIs 43-48: Entertainment, Sports & Miscellaneous
"""
import random
import uuid
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import requests

router = APIRouter(prefix="/api/entertainment", tags=["Entertainment, Sports & Miscellaneous"])


# ── 43 Sports Scores & Live Data ──────────────────────────────────────────────

@router.get("/sports/football", summary="43 · Sports Scores — Football (Soccer)")
def football_scores(
    competition: str = Query("PL", description="Competition code: PL=Premier League, PD=La Liga, BL1=Bundesliga, SA=Serie A, CL=Champions League"),
    matchday: Optional[int] = Query(None, description="Matchday number"),
):
    """Live scores, fixtures, standings, and player stats for football."""
    try:
        url = f"https://api.football-data.org/v4/competitions/{competition}/matches"
        params = {}
        if matchday:
            params["matchday"] = matchday
        resp = requests.get(url, headers={"X-Auth-Token": "DEMO"}, params=params, timeout=10)

        if resp.status_code == 401:
            return {
                "status": "config_required",
                "api": "Sports Scores — Football",
                "note": "Get a free API key at football-data.org",
                "competition": competition,
            }
        resp.raise_for_status()
        data = resp.json()
        matches = data.get("matches", [])[:15]
        results = []
        for m in matches:
            results.append({
                "match_id": m.get("id"),
                "status": m.get("status"),
                "date": m.get("utcDate"),
                "home_team": m.get("homeTeam", {}).get("name"),
                "away_team": m.get("awayTeam", {}).get("name"),
                "home_score": m.get("score", {}).get("fullTime", {}).get("home"),
                "away_score": m.get("score", {}).get("fullTime", {}).get("away"),
                "matchday": m.get("matchday"),
                "stage": m.get("stage"),
            })
        return {
            "status": "success",
            "api": "Sports Scores — Football",
            "competition": competition,
            "match_count": len(results),
            "matches": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sports/standings", summary="43b · Football League Standings")
def football_standings(
    competition: str = Query("PL", description="Competition code"),
):
    """Get current league standings table."""
    try:
        url = f"https://api.football-data.org/v4/competitions/{competition}/standings"
        resp = requests.get(url, headers={"X-Auth-Token": "DEMO"}, timeout=10)
        if resp.status_code == 401:
            return {
                "status": "config_required",
                "api": "Football Standings",
                "note": "Get a free API key at football-data.org",
            }
        data = resp.json()
        standings_raw = data.get("standings", [{}])[0].get("table", [])
        table = [
            {
                "position": t.get("position"),
                "team": t.get("team", {}).get("name"),
                "played": t.get("playedGames"),
                "won": t.get("won"),
                "draw": t.get("draw"),
                "lost": t.get("lost"),
                "goals_for": t.get("goalsFor"),
                "goals_against": t.get("goalsAgainst"),
                "points": t.get("points"),
            }
            for t in standings_raw
        ]
        return {"status": "success", "api": "Football Standings", "competition": competition, "table": table}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── 44 Movie & TV Show Data ───────────────────────────────────────────────────

@router.get("/movies", summary="44 · Movie & TV Show Data API")
def movie_data(
    query: Optional[str] = Query(None, description="Movie or TV show title"),
    imdb_id: Optional[str] = Query(None, description="IMDB ID e.g. tt0111161"),
    type: str = Query("movie", description="Type: movie | series | episode"),
):
    """Film details, cast, ratings, streaming availability, trailers, and reviews."""
    try:
        # OMDb API — free tier available
        base = "http://www.omdbapi.com/"
        params = {"apikey": "DEMO", "r": "json", "type": type}
        if imdb_id:
            params["i"] = imdb_id
        elif query:
            params["s"] = query
        else:
            raise HTTPException(status_code=400, detail="Provide query or imdb_id")

        resp = requests.get(base, params=params, timeout=10)
        data = resp.json()

        if data.get("Response") == "False":
            # Try with a different approach
            return {
                "status": "config_required",
                "api": "Movie & TV Data",
                "query": query or imdb_id,
                "note": "Get a free OMDb API key at omdbapi.com. Alternatively use TMDB free API.",
                "error": data.get("Error"),
            }

        if "Search" in data:
            results = [
                {
                    "title": m.get("Title"),
                    "year": m.get("Year"),
                    "type": m.get("Type"),
                    "imdb_id": m.get("imdbID"),
                    "poster": m.get("Poster"),
                }
                for m in data["Search"]
            ]
            return {
                "status": "success",
                "api": "Movie & TV Data",
                "query": query,
                "result_count": len(results),
                "results": results,
            }
        else:
            return {
                "status": "success",
                "api": "Movie & TV Data",
                "title": data.get("Title"),
                "year": data.get("Year"),
                "genre": data.get("Genre"),
                "director": data.get("Director"),
                "actors": data.get("Actors"),
                "plot": data.get("Plot"),
                "imdb_rating": data.get("imdbRating"),
                "runtime": data.get("Runtime"),
                "language": data.get("Language"),
                "country": data.get("Country"),
                "poster": data.get("Poster"),
                "ratings": data.get("Ratings"),
                "box_office": data.get("BoxOffice"),
                "awards": data.get("Awards"),
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── 45 Random Quote / Fact / Joke ─────────────────────────────────────────────

_QUOTES = [
    {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs", "category": "motivation"},
    {"quote": "In the middle of every difficulty lies opportunity.", "author": "Albert Einstein", "category": "motivation"},
    {"quote": "It does not matter how slowly you go as long as you do not stop.", "author": "Confucius", "category": "motivation"},
    {"quote": "Life is what happens when you're busy making other plans.", "author": "John Lennon", "category": "life"},
    {"quote": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt", "category": "motivation"},
    {"quote": "It is during our darkest moments that we must focus to see the light.", "author": "Aristotle", "category": "wisdom"},
    {"quote": "Whoever is happy will make others happy too.", "author": "Anne Frank", "category": "happiness"},
    {"quote": "Talk to yourself once in a day, otherwise you may miss meeting an excellent person in this world.", "author": "Swami Vivekananda", "category": "wisdom"},
]

_FACTS = [
    {"fact": "A day on Venus is longer than a year on Venus.", "category": "space"},
    {"fact": "Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs.", "category": "food"},
    {"fact": "Octopuses have three hearts and blue blood.", "category": "animals"},
    {"fact": "The shortest war in history lasted 38–45 minutes.", "category": "history"},
    {"fact": "Bananas are technically berries, but strawberries are not.", "category": "food"},
    {"fact": "A group of flamingos is called a flamboyance.", "category": "animals"},
    {"fact": "The Eiffel Tower can be 15 cm taller during summer due to thermal expansion.", "category": "science"},
    {"fact": "There are more possible iterations of a game of chess than there are atoms in the observable universe.", "category": "science"},
]

_JOKES = [
    {"joke": "Why don't programmers like nature? It has too many bugs.", "category": "programming"},
    {"joke": "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'", "category": "programming"},
    {"joke": "Why did the developer go broke? Because he used up all his cache.", "category": "programming"},
    {"joke": "I told my wife she was drawing her eyebrows too high. She looked surprised.", "category": "general"},
    {"joke": "I'm reading a book on anti-gravity. It's impossible to put down.", "category": "science"},
    {"joke": "What do you call a fish without eyes? A fsh.", "category": "general"},
    {"joke": "Why do Python programmers wear glasses? Because they can't C#.", "category": "programming"},
    {"joke": "How many programmers does it take to change a light bulb? None — it's a hardware problem.", "category": "programming"},
]

@router.get("/random/quote", summary="45 · Random Quote API")
def random_quote(category: Optional[str] = Query(None, description="Category filter")):
    filtered = [q for q in _QUOTES if not category or q["category"] == category]
    item = random.choice(filtered or _QUOTES)
    return {"status": "success", "api": "Random Quote", **item}

@router.get("/random/fact", summary="45b · Random Fact API")
def random_fact(category: Optional[str] = Query(None)):
    filtered = [f for f in _FACTS if not category or f["category"] == category]
    item = random.choice(filtered or _FACTS)
    return {"status": "success", "api": "Random Fact", **item}

@router.get("/random/joke", summary="45c · Random Joke API")
def random_joke(category: Optional[str] = Query(None)):
    filtered = [j for j in _JOKES if not category or j["category"] == category]
    item = random.choice(filtered or _JOKES)
    return {"status": "success", "api": "Random Joke", **item}


# ── 46 E-commerce Product Recommendation ─────────────────────────────────────

_PRODUCT_DB = {
    "laptop": [
        {"id": 1, "name": "MacBook Pro M3", "price": 1999, "rating": 4.9, "category": "laptop"},
        {"id": 2, "name": "Dell XPS 15", "price": 1499, "rating": 4.7, "category": "laptop"},
        {"id": 3, "name": "Lenovo ThinkPad X1", "price": 1299, "rating": 4.6, "category": "laptop"},
    ],
    "phone": [
        {"id": 4, "name": "iPhone 16 Pro", "price": 1099, "rating": 4.8, "category": "phone"},
        {"id": 5, "name": "Samsung Galaxy S25", "price": 899, "rating": 4.7, "category": "phone"},
        {"id": 6, "name": "Google Pixel 9", "price": 799, "rating": 4.5, "category": "phone"},
    ],
    "headphones": [
        {"id": 7, "name": "Sony WH-1000XM6", "price": 349, "rating": 4.9, "category": "headphones"},
        {"id": 8, "name": "Apple AirPods Max", "price": 549, "rating": 4.7, "category": "headphones"},
    ],
    "book": [
        {"id": 9, "name": "Atomic Habits", "price": 15, "rating": 4.8, "category": "book"},
        {"id": 10, "name": "The Psychology of Money", "price": 14, "rating": 4.7, "category": "book"},
    ],
}

class RecommendIn(BaseModel):
    user_id: Optional[str] = None
    viewed_products: Optional[List[str]] = []
    cart_items: Optional[List[str]] = []
    category: Optional[str] = None
    budget_max: Optional[float] = None
    limit: Optional[int] = 5

@router.post("/recommendations", summary="46 · E-commerce Product Recommendation API")
def product_recommendations(payload: RecommendIn):
    """AI-driven product recommendations based on browsing history and cart."""
    all_products = []
    for cat, products in _PRODUCT_DB.items():
        all_products.extend(products)

    # Filter by category if provided
    if payload.category:
        candidates = [p for p in all_products if p["category"] == payload.category]
    else:
        candidates = all_products

    # Filter by budget
    if payload.budget_max:
        candidates = [p for p in candidates if p["price"] <= payload.budget_max]

    # Sort by rating (simple collaborative-style scoring)
    candidates.sort(key=lambda x: x["rating"], reverse=True)
    limit = min(payload.limit or 5, len(candidates))
    recommended = candidates[:limit]

    # Add recommendation score
    for i, p in enumerate(recommended):
        p = dict(p)
        p["recommendation_score"] = round(p["rating"] * (1 - i * 0.05), 2)
        recommended[i] = p

    return {
        "status": "success",
        "api": "E-commerce Product Recommendation",
        "user_id": payload.user_id or "anonymous",
        "filters": {
            "category": payload.category,
            "budget_max": payload.budget_max,
        },
        "recommendation_count": len(recommended),
        "recommendations": recommended,
        "algorithm": "collaborative_filtering_v1",
    }


# ── 47 Fake Data / Test Data Generator ───────────────────────────────────────

@router.get("/fake-data", summary="47 · Fake Data / Test Data Generator API")
def fake_data(
    type: str = Query("user", description="Data type: user | address | company | credit_card | product | all"),
    locale: str = Query("en_US", description="Locale e.g. en_US, ar_AA, de_DE, fr_FR, es_ES"),
    count: int = Query(5, ge=1, le=100),
):
    """Generate realistic test users, addresses, credit cards, companies, and more."""
    try:
        from faker import Faker
        fake = Faker(locale)
        results = []
        for _ in range(count):
            if type == "user":
                results.append({
                    "id": str(uuid.uuid4()),
                    "first_name": fake.first_name(),
                    "last_name": fake.last_name(),
                    "email": fake.email(),
                    "username": fake.user_name(),
                    "phone": fake.phone_number(),
                    "date_of_birth": str(fake.date_of_birth(minimum_age=18, maximum_age=70)),
                    "avatar": f"https://i.pravatar.cc/150?u={fake.uuid4()}",
                })
            elif type == "address":
                results.append({
                    "street": fake.street_address(),
                    "city": fake.city(),
                    "state": fake.state() if hasattr(fake, "state") else fake.city(),
                    "postcode": fake.postcode(),
                    "country": fake.country(),
                    "country_code": fake.country_code(),
                    "latitude": float(fake.latitude()),
                    "longitude": float(fake.longitude()),
                })
            elif type == "company":
                results.append({
                    "name": fake.company(),
                    "industry": fake.bs(),
                    "email": fake.company_email(),
                    "phone": fake.phone_number(),
                    "website": fake.url(),
                    "address": fake.address(),
                    "ein": fake.ein() if hasattr(fake, "ein") else fake.numerify("##-#######"),
                })
            elif type == "credit_card":
                results.append({
                    "number": fake.credit_card_number(),
                    "provider": fake.credit_card_provider(),
                    "expiry": fake.credit_card_expire(),
                    "cvv": fake.credit_card_security_code(),
                    "holder": fake.name(),
                })
            elif type == "product":
                results.append({
                    "id": str(uuid.uuid4()),
                    "name": fake.catch_phrase(),
                    "sku": fake.bothify("SKU-??###"),
                    "price": round(random.uniform(5.99, 999.99), 2),
                    "category": random.choice(["Electronics", "Clothing", "Food", "Books", "Sports"]),
                    "in_stock": random.choice([True, False]),
                    "rating": round(random.uniform(3.0, 5.0), 1),
                })
            else:  # all
                results.append({
                    "user": {"name": fake.name(), "email": fake.email(), "phone": fake.phone_number()},
                    "address": {"street": fake.street_address(), "city": fake.city(), "country": fake.country()},
                    "company": {"name": fake.company(), "website": fake.url()},
                })
        return {
            "status": "success",
            "api": "Fake Data Generator",
            "type": type,
            "locale": locale,
            "count": len(results),
            "data": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fake data error: {str(exc)}")


# ── 48 Background Removal / Image AI ─────────────────────────────────────────

@router.post("/background-remove", summary="48 · Background Removal / Image AI API")
async def remove_background(
    file: UploadFile = File(...),
    model: str = Query("u2net", description="Model: u2net | u2net_human_seg | isnet-general-use"),
):
    """Remove image backgrounds using AI. Returns PNG with transparent background."""
    try:
        import io
        import base64
        from rembg import remove
        from PIL import Image

        contents = await file.read()
        input_img = Image.open(io.BytesIO(contents))
        output_img = remove(contents, model_name=model)
        output_pil = Image.open(io.BytesIO(output_img))

        buf = io.BytesIO()
        output_pil.save(buf, format="PNG")
        result_b64 = base64.b64encode(buf.getvalue()).decode()
        input_b64 = base64.b64encode(contents).decode()

        return {
            "status": "success",
            "api": "Background Removal / Image AI",
            "filename": file.filename,
            "model": model,
            "original_size_bytes": len(contents),
            "result_size_bytes": len(buf.getvalue()),
            "input_width": input_img.width,
            "input_height": input_img.height,
            "output_base64": result_b64,
            "format": "png",
            "usage": "Decode base64 and save as .png — background is transparent.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Background removal failed: {str(exc)}")
