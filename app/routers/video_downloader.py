"""
Social Media Video Downloader API
Supports: Twitter/X, TikTok, Instagram, Facebook, YouTube, and 1 000+ more sites
powered by yt-dlp.

Endpoints
---------
GET  /api/video/info      – fetch video metadata + available formats (no download)
GET  /api/video/download  – return the best direct stream URL for a given quality
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["Social Video Downloader"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _detect_platform(url: str) -> str:
    """Return a friendly platform name from the URL."""
    patterns = {
        "Twitter / X": r"(twitter\.com|x\.com)",
        "TikTok": r"tiktok\.com",
        "Instagram": r"instagram\.com",
        "Facebook": r"facebook\.com|fb\.watch",
        "YouTube": r"(youtube\.com|youtu\.be)",
        "Vimeo": r"vimeo\.com",
        "Dailymotion": r"dailymotion\.com",
        "Reddit": r"reddit\.com",
        "Pinterest": r"pinterest\.com",
        "Snapchat": r"snapchat\.com",
        "LinkedIn": r"linkedin\.com",
        "Twitch": r"twitch\.tv",
        "Bilibili": r"bilibili\.com",
        "Rumble": r"rumble\.com",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return name
    return "Unknown"


def _get_ydl_opts(quiet: bool = True, no_download: bool = True) -> dict:
    return {
        "quiet": quiet,
        "no_warnings": quiet,
        "noplaylist": True,
        "skip_download": no_download,
        # Some sites need cookies – try without first; users can add
        # cookiefile / cookiesfrombrowser via env if needed
        "socket_timeout": 15,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    }


def _extract_info(url: str) -> dict:
    """Run yt-dlp extract_info and return raw info dict."""
    try:
        import yt_dlp
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail=(
                "yt-dlp is not installed. "
                "Run: pip install yt-dlp==2026.3.17"
            ),
        )

    opts = _get_ydl_opts(quiet=True, no_download=True)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info or {}
    except Exception as exc:
        msg = str(exc)
        # Provide friendlier error messages for common failures
        if "Private" in msg or "private" in msg:
            raise HTTPException(status_code=403, detail="This video is private or requires login.")
        if "not available" in msg or "removed" in msg.lower():
            raise HTTPException(status_code=404, detail="Video not found or has been removed.")
        if "Unsupported URL" in msg:
            raise HTTPException(status_code=400, detail=f"Unsupported platform or URL: {url}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {msg}")


def _pick_best_format(formats: list, quality: str) -> Optional[dict]:
    """Pick the best video format matching requested quality."""
    quality_map = {"best": None, "hd": 720, "sd": 480, "low": 360}
    target_height = quality_map.get(quality)

    # Filter to formats that have both video + audio merged, or video only with audio
    candidates = [
        f for f in formats
        if f.get("vcodec") not in (None, "none")
        and f.get("url")
    ]
    if not candidates:
        candidates = [f for f in formats if f.get("url")]

    if not candidates:
        return None

    if target_height is None:
        # Return highest quality
        candidates.sort(key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
        return candidates[0]

    # Try to find exact height, then nearest
    exact = [f for f in candidates if f.get("height") == target_height]
    if exact:
        exact.sort(key=lambda f: f.get("tbr") or 0, reverse=True)
        return exact[0]

    # Pick nearest
    candidates.sort(key=lambda f: abs((f.get("height") or 0) - target_height))
    return candidates[0]


# ── API 49 · Video Info ───────────────────────────────────────────────────────

@router.get("/info", summary="49 · Social Video Info (metadata + formats)")
def video_info(
    url: str = Query(..., description="Full video URL from Twitter/X, TikTok, Instagram, Facebook, YouTube, etc."),
):
    """
    Return video title, thumbnail, duration, uploader, and all available
    quality formats — **no download happens on the server**.
    Supports 1 000+ sites via yt-dlp.
    """
    platform = _detect_platform(url)
    info = _extract_info(url)

    formats_raw = info.get("formats", [])
    formats = []
    seen_heights = set()
    for f in sorted(formats_raw, key=lambda x: (x.get("height") or 0), reverse=True):
        h = f.get("height")
        label = f"{h}p" if h else (f.get("format_note") or f.get("format_id", "unknown"))
        if label in seen_heights:
            continue
        seen_heights.add(label)
        has_audio = f.get("acodec") not in (None, "none")
        has_video = f.get("vcodec") not in (None, "none")
        if not (has_audio or has_video):
            continue
        formats.append({
            "format_id": f.get("format_id"),
            "label": label,
            "ext": f.get("ext"),
            "height": h,
            "width": f.get("width"),
            "fps": f.get("fps"),
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "has_video": has_video,
            "has_audio": has_audio,
            "tbr": f.get("tbr"),
        })

    return {
        "status": "success",
        "api": "Social Video Downloader — Info",
        "platform": platform,
        "url": url,
        "title": info.get("title"),
        "description": (info.get("description") or "")[:300],
        "uploader": info.get("uploader") or info.get("channel"),
        "duration_seconds": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "thumbnail": info.get("thumbnail"),
        "upload_date": info.get("upload_date"),
        "original_url": info.get("original_url") or url,
        "formats_available": len(formats),
        "formats": formats[:20],
        "note": "Use /api/video/download?url=...&quality=best to get a direct stream URL.",
    }


# ── API 50 · Video Download URL ───────────────────────────────────────────────

@router.get("/download", summary="50 · Social Video Download URL")
def video_download_url(
    url: str = Query(..., description="Full video URL"),
    quality: str = Query(
        "best",
        description="Quality preset: best | hd (720p) | sd (480p) | low (360p)",
    ),
    format_id: Optional[str] = Query(
        None,
        description="Specific yt-dlp format_id (overrides quality preset, get from /api/video/info)",
    ),
):
    """
    Return the **direct stream/download URL** for the requested quality.

    The URL can be opened directly in a browser or passed to a downloader —
    **no file is stored on the server**.  The link is usually short-lived
    (minutes to hours depending on the platform).

    Supported platforms include **Twitter/X, TikTok, Instagram, Facebook,
    YouTube, Vimeo, Dailymotion, Reddit**, and 1 000+ more.
    """
    platform = _detect_platform(url)
    info = _extract_info(url)

    formats = info.get("formats", [])
    if not formats:
        # Some extractors return a single url directly
        direct = info.get("url")
        if direct:
            return {
                "status": "success",
                "api": "Social Video Downloader — Download URL",
                "platform": platform,
                "title": info.get("title"),
                "quality": "original",
                "ext": info.get("ext", "mp4"),
                "download_url": direct,
                "thumbnail": info.get("thumbnail"),
                "duration_seconds": info.get("duration"),
                "note": "Right-click → Save As, or pass to curl/wget to download.",
            }
        raise HTTPException(status_code=404, detail="No downloadable formats found for this URL.")

    if format_id:
        chosen = next((f for f in formats if f.get("format_id") == format_id), None)
        if not chosen:
            raise HTTPException(status_code=404, detail=f"Format ID '{format_id}' not found. Use /api/video/info to list formats.")
    else:
        chosen = _pick_best_format(formats, quality)

    if not chosen or not chosen.get("url"):
        raise HTTPException(status_code=404, detail="Could not resolve a direct URL for the requested quality.")

    h = chosen.get("height")
    label = f"{h}p" if h else (chosen.get("format_note") or chosen.get("format_id", "unknown"))

    return {
        "status": "success",
        "api": "Social Video Downloader — Download URL",
        "platform": platform,
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "thumbnail": info.get("thumbnail"),
        "duration_seconds": info.get("duration"),
        "quality": label,
        "ext": chosen.get("ext", "mp4"),
        "width": chosen.get("width"),
        "height": h,
        "fps": chosen.get("fps"),
        "filesize_bytes": chosen.get("filesize") or chosen.get("filesize_approx"),
        "download_url": chosen.get("url"),
        "http_headers": chosen.get("http_headers", {}),
        "note": (
            "This URL may expire. "
            "Use it immediately — right-click → Save As in the browser, "
            "or: curl -L -o video.mp4 '<download_url>'"
        ),
    }


# ── API 51 · Supported Sites ──────────────────────────────────────────────────

@router.get("/supported-sites", summary="51 · List Supported Platforms")
def supported_sites():
    """Return highlights of the 1 000+ supported platforms."""
    highlights = [
        {"name": "Twitter / X", "url": "twitter.com / x.com", "notes": "Videos, GIFs"},
        {"name": "TikTok", "url": "tiktok.com", "notes": "Videos (public)"},
        {"name": "Instagram", "url": "instagram.com", "notes": "Reels, posts, stories (public)"},
        {"name": "Facebook", "url": "facebook.com / fb.watch", "notes": "Public videos"},
        {"name": "YouTube", "url": "youtube.com / youtu.be", "notes": "Videos, Shorts, live"},
        {"name": "Vimeo", "url": "vimeo.com", "notes": "Public videos"},
        {"name": "Dailymotion", "url": "dailymotion.com", "notes": "Videos"},
        {"name": "Reddit", "url": "reddit.com", "notes": "Video posts"},
        {"name": "Pinterest", "url": "pinterest.com", "notes": "Video pins"},
        {"name": "Twitch", "url": "twitch.tv", "notes": "VODs, clips"},
        {"name": "Bilibili", "url": "bilibili.com", "notes": "Videos"},
        {"name": "Rumble", "url": "rumble.com", "notes": "Videos"},
        {"name": "SoundCloud", "url": "soundcloud.com", "notes": "Audio tracks"},
        {"name": "Spotify", "url": "open.spotify.com", "notes": "Podcast episodes (audio)"},
        {"name": "LinkedIn", "url": "linkedin.com", "notes": "Public videos"},
    ]
    return {
        "status": "success",
        "api": "Social Video Downloader — Supported Sites",
        "highlighted_platforms": highlights,
        "total_supported": "1 000+",
        "powered_by": "yt-dlp",
        "note": "Use /api/video/info?url=... to check if a specific URL is supported.",
    }
