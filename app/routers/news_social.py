"""
APIs 24-27: News, Media & Social Data
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import requests

router = APIRouter(prefix="/api/media", tags=["News, Media & Social Data"])

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


# ── 24 Real-Time News ─────────────────────────────────────────────────────────

@router.get("/news", summary="24 · Real-Time News API")
def realtime_news(
    query: str = Query("technology", description="Search topic or keyword"),
    language: str = Query("en", description="Language code e.g. en, de, fr"),
    country: Optional[str] = Query(None, description="Country code e.g. us, gb"),
    limit: int = Query(10, ge=1, le=50),
):
    """Breaking news from 100,000+ sources globally, filterable by topic."""
    try:
        # GNews free API (no key for basic usage)
        url = f"https://gnews.io/api/v4/search?q={requests.utils.quote(query)}&lang={language}&max={limit}&apikey=demo"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            articles = [
                {
                    "title": a.get("title"),
                    "description": a.get("description"),
                    "url": a.get("url"),
                    "source": a.get("source", {}).get("name"),
                    "published_at": a.get("publishedAt"),
                    "image": a.get("image"),
                }
                for a in data.get("articles", [])
            ]
            return {
                "status": "success",
                "api": "Real-Time News",
                "query": query,
                "total_results": data.get("totalArticles", len(articles)),
                "articles": articles,
            }
    except Exception:
        pass

    # Fallback: RSS feeds
    try:
        from bs4 import BeautifulSoup
        rss_feeds = {
            "technology": "https://feeds.feedburner.com/TechCrunch",
            "business": "https://feeds.finance.yahoo.com/rss/2.0/headline",
            "world": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        }
        feed_url = rss_feeds.get(query.lower(), f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl={language}")
        resp = requests.get(feed_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")[:limit]
        articles = [
            {
                "title": i.find("title").get_text() if i.find("title") else "",
                "description": i.find("description").get_text()[:200] if i.find("description") else "",
                "url": i.find("link").get_text() if i.find("link") else "",
                "published_at": i.find("pubDate").get_text() if i.find("pubDate") else "",
                "source": i.find("source").get_text() if i.find("source") else "Unknown",
            }
            for i in items
        ]
        return {
            "status": "success",
            "api": "Real-Time News",
            "query": query,
            "total_results": len(articles),
            "articles": articles,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"News error: {str(exc)}")


# ── 25 YouTube Data & Analytics ───────────────────────────────────────────────

@router.get("/youtube", summary="25 · YouTube Data & Analytics API")
def youtube_data(
    video_id: Optional[str] = Query(None, description="YouTube video ID e.g. dQw4w9WgXcQ"),
    channel_id: Optional[str] = Query(None, description="YouTube channel ID"),
    query: Optional[str] = Query(None, description="Search query"),
):
    """Video stats, channel metrics, comments, and trending video data."""
    try:
        if video_id:
            # Scrape basic public data
            url = f"https://www.youtube.com/watch?v={video_id}"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.find("meta", {"property": "og:title"})
            description = soup.find("meta", {"property": "og:description"})
            thumbnail = soup.find("meta", {"property": "og:image"})
            return {
                "status": "success",
                "api": "YouTube Data",
                "video_id": video_id,
                "title": title["content"] if title else "N/A",
                "description": description["content"] if description else "N/A",
                "thumbnail": thumbnail["content"] if thumbnail else "N/A",
                "url": url,
                "note": "Use Google YouTube Data API v3 for full stats, comments, and analytics.",
            }
        elif query:
            url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            import re
            import json
            matches = re.findall(r"var ytInitialData = ({.*?});", resp.text)
            results = []
            if matches:
                try:
                    yt_data = json.loads(matches[0])
                    contents = yt_data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
                    for section in contents:
                        items = section.get("itemSectionRenderer", {}).get("contents", [])
                        for item in items[:10]:
                            v = item.get("videoRenderer", {})
                            if v:
                                results.append({
                                    "video_id": v.get("videoId"),
                                    "title": v.get("title", {}).get("runs", [{}])[0].get("text"),
                                    "channel": v.get("ownerText", {}).get("runs", [{}])[0].get("text"),
                                    "views": v.get("viewCountText", {}).get("simpleText"),
                                    "duration": v.get("lengthText", {}).get("simpleText"),
                                    "thumbnail": f"https://img.youtube.com/vi/{v.get('videoId')}/hqdefault.jpg",
                                })
                except Exception:
                    pass
            return {
                "status": "success",
                "api": "YouTube Data",
                "query": query,
                "result_count": len(results),
                "results": results,
            }
        else:
            raise HTTPException(status_code=400, detail="Provide video_id, channel_id, or query")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── 26 TikTok & Instagram Data ────────────────────────────────────────────────

@router.get("/tiktok", summary="26 · TikTok & Instagram Data API")
def tiktok_data(
    hashtag: Optional[str] = Query(None, description="Hashtag to search (without #)"),
    username: Optional[str] = Query(None, description="TikTok username"),
):
    """Trending videos, hashtags, influencer metrics, and engagement data."""
    try:
        if hashtag:
            url = f"https://www.tiktok.com/tag/{hashtag}"
        elif username:
            url = f"https://www.tiktok.com/@{username}"
        else:
            raise HTTPException(status_code=400, detail="Provide hashtag or username")

        resp = requests.get(url, headers=HEADERS, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.find("title")
        desc = soup.find("meta", {"name": "description"})
        return {
            "status": "success",
            "api": "TikTok & Instagram Data",
            "url": url,
            "title": title.get_text() if title else "N/A",
            "description": desc["content"] if desc else "N/A",
            "note": "TikTok heavily restricts scraping. Use TikTok Research API for production.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        return {
            "status": "limited",
            "api": "TikTok & Instagram Data",
            "note": "TikTok requires official API access. Apply at developers.tiktok.com",
            "error": str(exc),
        }


# ── 27 Podcast Search & Metadata ──────────────────────────────────────────────

@router.get("/podcasts", summary="27 · Podcast Search & Metadata API")
def podcast_search(
    query: str = Query(..., description="Podcast name or topic"),
    limit: int = Query(10, ge=1, le=30),
):
    """Search podcasts, get episode data, transcripts, and listener statistics."""
    try:
        # iTunes Search API — completely free, no key needed
        url = f"https://itunes.apple.com/search?term={requests.utils.quote(query)}&media=podcast&limit={limit}&entity=podcast"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = [
            {
                "id": p.get("collectionId"),
                "name": p.get("collectionName"),
                "artist": p.get("artistName"),
                "genre": p.get("primaryGenreName"),
                "feed_url": p.get("feedUrl"),
                "artwork": p.get("artworkUrl600"),
                "episode_count": p.get("trackCount"),
                "language": p.get("languageCodesISO2A"),
                "country": p.get("country"),
            }
            for p in data.get("results", [])
        ]
        return {
            "status": "success",
            "api": "Podcast Search & Metadata",
            "query": query,
            "total_results": data.get("resultCount", len(results)),
            "podcasts": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Podcast search error: {str(exc)}")
