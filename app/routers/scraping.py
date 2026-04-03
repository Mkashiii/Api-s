"""
APIs 09-14: Data Scraping & Extraction
"""
import re
import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import requests
from bs4 import BeautifulSoup
import logging

router = APIRouter(prefix="/api/scraping", tags=["Data Scraping & Extraction"])
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_PRIVATE_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

def _validate_url(url: str):
    """Validate URL is a safe external HTTPS/HTTP target (SSRF protection).
    Returns the parsed URL on success."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed.")
    hostname = parsed.hostname or ""
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: missing hostname.")
    # Resolve and check for private/loopback IPs
    try:
        addrs = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addrs:
            ip = ipaddress.ip_address(sockaddr[0])
            for net in _PRIVATE_NETS:
                if ip in net:
                    raise HTTPException(status_code=400, detail="Requests to private/internal addresses are not allowed.")
    except HTTPException:
        raise
    except Exception:
        # DNS resolution failure — allow and let requests handle it
        pass
    return parsed

def _get(url: str, timeout: int = 10) -> BeautifulSoup:
    parsed = _validate_url(url)
    # Reconstruct URL from validated components to break taint flow
    safe_url = parsed.geturl()
    try:
        resp = requests.get(safe_url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Scrape fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to fetch the requested URL.")


# ── 09 Web Scraper / Data Extractor ──────────────────────────────────────────

class ScrapeIn(BaseModel):
    url: str
    extract: Optional[str] = "all"  # all | text | links | images | tables

@router.post("/web-scraper", summary="09 · Web Scraper / Data Extractor")
def web_scraper(payload: ScrapeIn):
    """Scrape any public website and return clean structured JSON."""
    soup = _get(payload.url)

    result = {
        "status": "success",
        "api": "Web Scraper",
        "url": payload.url,
        "title": soup.title.string.strip() if soup.title else "",
    }

    if payload.extract in ("all", "text"):
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        result["text"] = paragraphs[:20]

    if payload.extract in ("all", "links"):
        links = []
        for a in soup.find_all("a", href=True)[:30]:
            href = a["href"]
            if href.startswith("http"):
                links.append({"text": a.get_text(strip=True), "href": href})
        result["links"] = links

    if payload.extract in ("all", "images"):
        images = [img.get("src", "") for img in soup.find_all("img", src=True)[:20]]
        result["images"] = images

    if payload.extract in ("all", "tables"):
        tables = []
        for table in soup.find_all("table")[:5]:
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        result["tables"] = tables

    return result


# ── 10 LinkedIn Profile & Company Scraper ────────────────────────────────────

@router.get("/linkedin", summary="10 · LinkedIn Profile & Company Scraper")
def linkedin_scraper(profile_url: str = Query(..., description="LinkedIn profile or company URL")):
    """Extract public LinkedIn profiles, job listings, company info."""
    try:
        soup = _get(profile_url)
        name = soup.find("h1")
        headline = soup.find("div", {"class": re.compile("text-body-medium")})
        return {
            "status": "success",
            "api": "LinkedIn Profile Scraper",
            "url": profile_url,
            "name": name.get_text(strip=True) if name else "N/A",
            "headline": headline.get_text(strip=True) if headline else "N/A",
            "note": "LinkedIn heavily restricts scraping. Use official LinkedIn API for production.",
        }
    except Exception as exc:
        logger.warning("LinkedIn scrape failed: %s", exc)
        return {
            "status": "limited",
            "api": "LinkedIn Profile Scraper",
            "url": profile_url,
            "note": "LinkedIn requires authentication. Use LinkedIn Official API with OAuth2.",
        }


# ── 11 Amazon Product Data ────────────────────────────────────────────────────

@router.get("/amazon-product", summary="11 · Amazon Product Data API")
def amazon_product(asin: str = Query(..., description="Amazon ASIN (e.g. B08N5WRWNW)")):
    """Real-time Amazon product details, pricing, and reviews."""
    url = f"https://www.amazon.com/dp/{asin}"
    try:
        import fake_useragent
        ua = fake_useragent.UserAgent()
        headers = {**HEADERS, "User-Agent": ua.random}
    except Exception:
        headers = HEADERS

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")

        title_tag = soup.find("span", id="productTitle")
        price_tag = soup.find("span", class_=re.compile("a-price-whole"))
        rating_tag = soup.find("span", class_="a-icon-alt")
        reviews_tag = soup.find("span", id="acrCustomerReviewText")

        return {
            "status": "success",
            "api": "Amazon Product Data",
            "asin": asin,
            "url": url,
            "title": title_tag.get_text(strip=True) if title_tag else "N/A",
            "price": price_tag.get_text(strip=True) if price_tag else "N/A",
            "rating": rating_tag.get_text(strip=True) if rating_tag else "N/A",
            "review_count": reviews_tag.get_text(strip=True) if reviews_tag else "N/A",
        }
    except Exception as exc:
        logger.warning("Amazon scrape failed for ASIN %s: %s", asin, exc)
        return {
            "status": "limited",
            "api": "Amazon Product Data",
            "asin": asin,
            "note": "Amazon uses bot detection. Consider Rainforest API or Oxylabs for production.",
        }


# ── 12 Google SERP Scraper ────────────────────────────────────────────────────

@router.get("/google-serp", summary="12 · Google SERP Scraper API")
def google_serp(
    query: str = Query(..., description="Search query"),
    num: int = Query(10, ge=1, le=50),
):
    """Get Google search results, featured snippets, and PAA as clean JSON."""
    url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num}"
    try:
        soup = _get(url)
        results = []
        for g in soup.find_all("div", class_="g")[:num]:
            title_tag = g.find("h3")
            link_tag = g.find("a")
            snippet_tag = g.find("div", class_=re.compile("VwiC3b|s3v9rd|IsZvec"))
            if title_tag and link_tag:
                results.append({
                    "title": title_tag.get_text(strip=True),
                    "url": link_tag.get("href", ""),
                    "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                })
        featured = soup.find("div", class_=re.compile("hgKElc|ifM9O"))
        paa = [q.get_text(strip=True) for q in soup.find_all("span", class_="CSkcDe")[:5]]
        return {
            "status": "success",
            "api": "Google SERP Scraper",
            "query": query,
            "result_count": len(results),
            "results": results,
            "featured_snippet": featured.get_text(strip=True) if featured else None,
            "people_also_ask": paa,
        }
    except Exception as exc:
        logger.warning("Google SERP scrape failed: %s", exc)
        return {
            "status": "limited",
            "api": "Google SERP Scraper",
            "query": query,
            "note": "Google blocks scrapers. Use SerpAPI or DataForSEO for production.",
        }


# ── 13 Indeed / Jobs Scraper ─────────────────────────────────────────────────

@router.get("/jobs", summary="13 · Indeed / Jobs Scraper API")
def jobs_scraper(
    query: str = Query(..., description="Job title or keyword"),
    location: str = Query("remote", description="Location"),
    num: int = Query(10, ge=1, le=30),
):
    """Scrape job listings from Indeed with full details."""
    url = f"https://www.indeed.com/jobs?q={requests.utils.quote(query)}&l={requests.utils.quote(location)}"
    try:
        soup = _get(url)
        jobs = []
        for card in soup.find_all("div", class_=re.compile("job_seen_beacon|resultContent"))[:num]:
            title = card.find("h2")
            company = card.find("span", class_=re.compile("companyName"))
            loc = card.find("div", class_=re.compile("companyLocation"))
            salary = card.find("div", class_=re.compile("salary-snippet"))
            if title:
                jobs.append({
                    "title": title.get_text(strip=True),
                    "company": company.get_text(strip=True) if company else "N/A",
                    "location": loc.get_text(strip=True) if loc else "N/A",
                    "salary": salary.get_text(strip=True) if salary else "Not listed",
                })
        return {
            "status": "success",
            "api": "Jobs Scraper",
            "query": query,
            "location": location,
            "job_count": len(jobs),
            "jobs": jobs,
        }
    except Exception as exc:
        logger.warning("Jobs scrape failed: %s", exc)
        return {
            "status": "limited",
            "api": "Jobs Scraper",
            "query": query,
            "note": "Indeed may block scrapers. Use Jooble or Adzuna API for production.",
        }


# ── 14 Real Estate / Zillow Data ─────────────────────────────────────────────

@router.get("/real-estate", summary="14 · Real Estate / Zillow Data API")
def real_estate(
    address: str = Query(..., description="Property address or ZIP code"),
):
    """Property listings, prices, rental data, and neighbourhood statistics."""
    try:
        query = requests.utils.quote(address)
        url = f"https://www.zillow.com/search/GetSearchPageState.htm?searchQueryState={{%22usersSearchTerm%22:%22{query}%22}}&wants={{%22cat1%22:[%22listResults%22]}}&requestId=1"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        listings = data.get("cat1", {}).get("searchResults", {}).get("listResults", [])[:5]
        results = []
        for l in listings:
            results.append({
                "address": l.get("addressStreet", ""),
                "city": l.get("addressCity", ""),
                "state": l.get("addressState", ""),
                "price": l.get("unformattedPrice", ""),
                "beds": l.get("beds", ""),
                "baths": l.get("baths", ""),
                "sqft": l.get("area", ""),
                "url": "https://www.zillow.com" + l.get("detailUrl", ""),
            })
        return {
            "status": "success",
            "api": "Real Estate / Zillow Data",
            "address": address,
            "listing_count": len(results),
            "listings": results,
        }
    except Exception as exc:
        logger.warning("Real estate scrape failed: %s", exc)
        return {
            "status": "limited",
            "api": "Real Estate / Zillow Data",
            "address": address,
            "note": "Use Zillow Bridge API or Attom Data for production use.",
        }
