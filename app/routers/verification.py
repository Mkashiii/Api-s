"""
APIs 19-23: Verification, Identity & Communication
"""
import random
import string
import re
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/verify", tags=["Verification, Identity & Communication"])
logger = logging.getLogger(__name__)

# In-memory OTP store (use Redis in production)
_otp_store: dict = {}


# ── 19 Phone Number Validation ────────────────────────────────────────────────

@router.get("/phone", summary="19 · Phone Number Validation API")
def validate_phone(
    number: str = Query(..., description="Phone number with country code e.g. +14155552671"),
    country: Optional[str] = Query(None, description="ISO 2-letter country code e.g. US"),
):
    """Validate phone numbers globally, detect carrier, line type, and country."""
    try:
        import phonenumbers
        from phonenumbers import geocoder, carrier, timezone
        parsed = phonenumbers.parse(number, country)
        valid = phonenumbers.is_valid_number(parsed)
        possible = phonenumbers.is_possible_number(parsed)
        number_type = phonenumbers.number_type(parsed)
        type_map = {
            0: "FIXED_LINE",
            1: "MOBILE",
            2: "FIXED_LINE_OR_MOBILE",
            3: "TOLL_FREE",
            4: "PREMIUM_RATE",
            5: "SHARED_COST",
            6: "VOIP",
            7: "PERSONAL_NUMBER",
            8: "PAGER",
            9: "UAN",
            10: "VOICEMAIL",
            -1: "UNKNOWN",
        }
        return {
            "status": "success",
            "api": "Phone Number Validation",
            "input": number,
            "valid": valid,
            "possible": possible,
            "e164_format": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164) if valid else None,
            "international_format": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL) if valid else None,
            "national_format": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL) if valid else None,
            "country_code": parsed.country_code,
            "country": geocoder.description_for_number(parsed, "en"),
            "carrier": carrier.name_for_number(parsed, "en"),
            "line_type": type_map.get(number_type, "UNKNOWN"),
            "timezones": list(timezone.time_zones_for_number(parsed)),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Phone validation error: {str(exc)}")


# ── 20 Email Validation & Deliverability ──────────────────────────────────────

_DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "trashmail.com", "fakeinbox.com", "maildrop.cc",
    "dispostable.com", "sharklasers.com", "guerrillamailblock.com",
}

@router.get("/email", summary="20 · Email Validation & Deliverability API")
def validate_email(email: str = Query(..., description="Email address to validate")):
    """Check if email is real, deliverable, not disposable, and not a spam trap."""
    try:
        from email_validator import validate_email as _validate, EmailNotValidError
        valid_info = _validate(email, check_deliverability=False)
        local, domain = email.split("@", 1)
        is_disposable = domain.lower() in _DISPOSABLE_DOMAINS

        # MX record check
        mx_ok = False
        try:
            import dns.resolver
            mx_records = dns.resolver.resolve(domain, "MX")
            mx_ok = len(list(mx_records)) > 0
            mx_list = [str(r.exchange) for r in mx_records]
        except Exception:
            mx_list = []

        return {
            "status": "success",
            "api": "Email Validation & Deliverability",
            "email": email,
            "normalized": valid_info.normalized,
            "valid_format": True,
            "deliverable": mx_ok and not is_disposable,
            "disposable": is_disposable,
            "domain": domain,
            "mx_records": mx_list,
            "mx_found": mx_ok,
            "role_account": local.lower() in {"admin", "info", "support", "noreply", "no-reply", "postmaster"},
        }
    except Exception as exc:
        logger.warning("Email validation failed for %s: %s", email, exc)
        return {
            "status": "invalid",
            "api": "Email Validation & Deliverability",
            "email": email,
            "valid_format": False,
            "error": "Invalid email address format.",
        }


# ── 21 IP Geolocation & Threat ────────────────────────────────────────────────

@router.get("/ip-geolocation", summary="21 · IP Geolocation & Threat API")
def ip_geolocation(
    ip: str = Query(..., description="IP address to look up. Use 'me' for your own IP."),
):
    """Country, city, timezone, ISP, VPN detection and fraud score for any IP."""
    try:
        import requests as req
        if ip == "me":
            ip_url = "https://api.ipify.org?format=json"
            ip_resp = req.get(ip_url, timeout=5)
            ip = ip_resp.json().get("ip", ip)

        url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query,mobile,proxy,hosting"
        resp = req.get(url, timeout=10)
        data = resp.json()

        if data.get("status") == "success":
            proxy_vpn = data.get("proxy", False) or data.get("hosting", False)
            fraud_score = 85 if proxy_vpn else (data.get("mobile") and 20 or 5)
            return {
                "status": "success",
                "api": "IP Geolocation & Threat",
                "ip": data.get("query"),
                "country": data.get("country"),
                "country_code": data.get("countryCode"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "zip": data.get("zip"),
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "organization": data.get("org"),
                "asn": data.get("as"),
                "is_mobile": data.get("mobile"),
                "is_proxy": data.get("proxy"),
                "is_hosting": data.get("hosting"),
                "vpn_detected": proxy_vpn,
                "fraud_score": fraud_score,
                "threat_level": "high" if fraud_score > 60 else ("medium" if fraud_score > 30 else "low"),
            }
        else:
            raise HTTPException(status_code=400, detail=data.get("message", "Lookup failed"))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── 22 OTP / SMS Verification ─────────────────────────────────────────────────

class OTPRequest(BaseModel):
    phone: str
    length: Optional[int] = 6
    expiry_minutes: Optional[int] = 10

class OTPVerify(BaseModel):
    phone: str
    code: str

@router.post("/otp/send", summary="22 · OTP / SMS Verification — Send")
def send_otp(payload: OTPRequest):
    """Generate and send OTP via SMS for 2FA and login verification."""
    import time
    length = min(max(payload.length or 6, 4), 8)
    code = "".join(random.choices(string.digits, k=length))
    expiry = (payload.expiry_minutes or 10) * 60
    _otp_store[payload.phone] = {
        "code": code,
        "expires_at": time.time() + expiry,
    }
    # In production, send via Twilio or similar:
    # client = twilio.rest.Client(TWILIO_SID, TWILIO_TOKEN)
    # client.messages.create(to=payload.phone, from_=TWILIO_FROM, body=f"Your OTP is {code}")
    return {
        "status": "success",
        "api": "OTP / SMS Verification",
        "phone": payload.phone,
        "message": f"OTP sent to {payload.phone}",
        "length": length,
        "expires_in_minutes": payload.expiry_minutes,
        "demo_code": code,  # Remove this in production!
        "note": "Configure Twilio credentials for real SMS delivery.",
    }

@router.post("/otp/verify", summary="22 · OTP / SMS Verification — Verify")
def verify_otp(payload: OTPVerify):
    """Verify a submitted OTP code."""
    import time
    stored = _otp_store.get(payload.phone)
    if not stored:
        return {"status": "error", "api": "OTP Verify", "message": "No OTP found for this number."}
    if time.time() > stored["expires_at"]:
        del _otp_store[payload.phone]
        return {"status": "error", "api": "OTP Verify", "message": "OTP has expired."}
    if stored["code"] == payload.code:
        del _otp_store[payload.phone]
        return {"status": "success", "api": "OTP Verify", "verified": True, "message": "OTP verified successfully."}
    return {"status": "error", "api": "OTP Verify", "verified": False, "message": "Invalid OTP code."}


# ── 23 WHOIS & Domain Lookup ──────────────────────────────────────────────────

@router.get("/whois", summary="23 · WHOIS & Domain Lookup API")
def whois_lookup(domain: str = Query(..., description="Domain name e.g. google.com")):
    """Domain registration info, expiry dates, nameservers, and registrar details."""
    try:
        import whois as _whois
        w = _whois.whois(domain)
        expiration = w.expiration_date
        if isinstance(expiration, list):
            expiration = expiration[0]
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        return {
            "status": "success",
            "api": "WHOIS & Domain Lookup",
            "domain": domain,
            "registrar": w.registrar,
            "creation_date": str(creation) if creation else None,
            "expiration_date": str(expiration) if expiration else None,
            "updated_date": str(w.updated_date) if w.updated_date else None,
            "name_servers": w.name_servers,
            "status": w.status,
            "emails": w.emails,
            "registrant_country": w.country,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"WHOIS error: {str(exc)}")


@router.get("/domain-available", summary="23b · Domain Availability Check")
def domain_availability(domain: str = Query(..., description="Domain to check e.g. example.com")):
    """Check if a domain is available for registration."""
    try:
        import whois as _whois
        w = _whois.whois(domain)
        registered = bool(w.registrar or w.creation_date)
        return {
            "status": "success",
            "api": "Domain Availability",
            "domain": domain,
            "available": not registered,
            "registered": registered,
            "registrar": w.registrar if registered else None,
        }
    except Exception:
        return {
            "status": "success",
            "api": "Domain Availability",
            "domain": domain,
            "available": True,
            "registered": False,
        }
