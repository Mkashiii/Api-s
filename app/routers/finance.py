"""
APIs 15-18: Finance, Stocks & Crypto
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import requests

router = APIRouter(prefix="/api/finance", tags=["Finance, Stocks & Crypto"])


# ── 15 Real-Time Stock Price ──────────────────────────────────────────────────

@router.get("/stock", summary="15 · Real-Time Stock Price API")
def stock_price(
    symbol: str = Query(..., description="Stock symbol e.g. AAPL, TSLA"),
    period: str = Query("1mo", description="Period: 1d 5d 1mo 3mo 6mo 1y 2y 5y"),
):
    """Live and historical OHLCV data, market cap, P/E ratios."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        hist = ticker.history(period=period)
        hist_data = []
        for date, row in hist.tail(10).iterrows():
            hist_data.append({
                "date": str(date.date()),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })
        return {
            "status": "success",
            "api": "Real-Time Stock Price",
            "symbol": symbol.upper(),
            "name": info.get("longName", symbol),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange"),
            "history": hist_data,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Stock data error: {str(exc)}")


# ── 16 Crypto Price & Market Data ────────────────────────────────────────────

@router.get("/crypto", summary="16 · Crypto Price & Market Data API")
def crypto_price(
    coin_id: str = Query("bitcoin", description="CoinGecko coin ID e.g. bitcoin, ethereum"),
    vs_currency: str = Query("usd", description="Currency to compare against"),
):
    """BTC, ETH, and 10,000+ altcoin prices, volume, market cap."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id.lower()}"
        resp = requests.get(url, timeout=10, headers={"Accept": "application/json"})
        if resp.status_code == 429:
            # Fallback to simple price endpoint
            url2 = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id.lower()}&vs_currencies={vs_currency.lower()}&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true"
            resp = requests.get(url2, timeout=10, headers={"Accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()
            coin_data = data.get(coin_id.lower(), {})
            currency = vs_currency.lower()
            return {
                "status": "success",
                "api": "Crypto Price & Market Data",
                "id": coin_id.lower(),
                "name": coin_id.title(),
                "symbol": coin_id[:3].upper(),
                "current_price": coin_data.get(currency),
                "market_cap": coin_data.get(f"{currency}_market_cap"),
                "total_volume": coin_data.get(f"{currency}_24h_vol"),
                "price_change_24h": coin_data.get(f"{currency}_24h_change"),
            }
        resp.raise_for_status()
        data = resp.json()
        market = data.get("market_data", {})
        currency = vs_currency.lower()
        return {
            "status": "success",
            "api": "Crypto Price & Market Data",
            "id": data.get("id"),
            "name": data.get("name"),
            "symbol": data.get("symbol", "").upper(),
            "rank": data.get("market_cap_rank"),
            "current_price": market.get("current_price", {}).get(currency),
            "market_cap": market.get("market_cap", {}).get(currency),
            "total_volume": market.get("total_volume", {}).get(currency),
            "price_change_24h": market.get("price_change_percentage_24h"),
            "price_change_7d": market.get("price_change_percentage_7d"),
            "ath": market.get("ath", {}).get(currency),
            "atl": market.get("atl", {}).get(currency),
            "circulating_supply": market.get("circulating_supply"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crypto data error: {str(exc)}")


@router.get("/crypto/trending", summary="16b · Trending Cryptocurrencies")
def crypto_trending():
    """Get trending cryptocurrencies from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        coins = [
            {
                "name": c["item"]["name"],
                "symbol": c["item"]["symbol"],
                "rank": c["item"]["market_cap_rank"],
                "price_btc": c["item"].get("price_btc"),
            }
            for c in data.get("coins", [])
        ]
        return {
            "status": "success",
            "api": "Trending Cryptocurrencies",
            "trending": coins,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── 17 Currency Exchange Rate ─────────────────────────────────────────────────

@router.get("/currency", summary="17 · Currency Exchange Rate API")
def currency_exchange(
    base: str = Query("USD", description="Base currency code e.g. USD, EUR, GBP"),
    target: Optional[str] = Query(None, description="Target currency. If blank, returns all rates."),
    amount: float = Query(1.0, description="Amount to convert"),
):
    """Live and historical forex rates for 170+ currencies."""
    try:
        url = f"https://api.frankfurter.app/latest?from={base.upper()}"
        if target:
            url += f"&to={target.upper()}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        converted = None
        if target:
            rate = rates.get(target.upper())
            converted = round(amount * rate, 6) if rate else None
        return {
            "status": "success",
            "api": "Currency Exchange Rate",
            "base": data.get("base"),
            "date": data.get("date"),
            "amount": amount,
            "target": target.upper() if target else None,
            "converted_amount": converted,
            "rates": rates,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Currency API error: {str(exc)}")


# ── 18 Financial News & Earnings ──────────────────────────────────────────────

@router.get("/financial-news", summary="18 · Financial News & Earnings API")
def financial_news(
    symbol: Optional[str] = Query(None, description="Stock symbol e.g. AAPL"),
    query: Optional[str] = Query("stock market", description="Search query"),
    limit: int = Query(10, ge=1, le=50),
):
    """Company earnings reports, analyst ratings, and financial news."""
    try:
        import yfinance as yf
        if symbol:
            ticker = yf.Ticker(symbol.upper())
            news = ticker.news or []
            articles = [
                {
                    "title": n.get("title"),
                    "publisher": n.get("publisher"),
                    "link": n.get("link"),
                    "published_at": n.get("providerPublishTime"),
                    "type": n.get("type"),
                }
                for n in news[:limit]
            ]
            return {
                "status": "success",
                "api": "Financial News & Earnings",
                "symbol": symbol.upper(),
                "article_count": len(articles),
                "news": articles,
            }
        else:
            # General market news from free RSS
            url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=yhoo,aapl&region=US&lang=en-US"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")[:limit]
            articles = [
                {
                    "title": i.find("title").get_text() if i.find("title") else "",
                    "link": i.find("link").get_text() if i.find("link") else "",
                    "published_at": i.find("pubDate").get_text() if i.find("pubDate") else "",
                }
                for i in items
            ]
            return {
                "status": "success",
                "api": "Financial News & Earnings",
                "query": query,
                "article_count": len(articles),
                "news": articles,
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"News error: {str(exc)}")
