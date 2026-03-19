from fastapi import FastAPI, HTTPException
from urllib.parse import urlparse, parse_qs, unquote, quote
import re
from fastapi.responses import RedirectResponse
import requests

app = FastAPI()


# ---------- Utils ----------

def expand_url(url: str) -> str:
    """Expand shortened Google Maps URLs"""
    try:
        res = requests.get(url, allow_redirects=True, timeout=5)
        return res.url
    except:
        return url


def extract_lat_lng(url: str):
    """Extract coordinates from URL"""
    match = re.search(r"@([-0-9.]+),([-0-9.]+)", url)
    if match:
        return match.group(1), match.group(2)

    # fallback: sometimes in query
    parsed = urlparse(url)
    q = parse_qs(parsed.query)

    if "ll" in q:
        lat, lng = q["ll"][0].split(",")
        return lat, lng

    return None, None


def extract_place(url: str):
    """Extract place name"""
    parsed = urlparse(url)
    q = parse_qs(parsed.query)

    # case 1: ?q=
    if "q" in q:
        return unquote(q["q"][0])

    # case 2: /place/NAME/
    match = re.search(r"/place/([^/]+)", url)
    if match:
        return unquote(match.group(1)).replace("+", " ")

    return None


def reverse_geocode(lat: str, lng: str):
    """Fallback to get human-readable place name"""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}"
        headers = {"User-Agent": "maps-converter"}
        res = requests.get(url, headers=headers, timeout=5).json()

        return res.get("display_name")
    except:
        return None


def build_apple_maps_url(place: str, lat: str, lng: str):
    """Construct Apple Maps URL"""
    if not lat or not lng:
        raise ValueError("Missing coordinates")

    if not place:
        place = f"{lat},{lng}"

    encoded_place = quote(place)

    return f"https://maps.apple.com/?q={encoded_place}&ll={lat},{lng}"


# ---------- API ----------

@app.get("/")
def root():
    return {"message": "Google Maps → Apple Maps API running"}


@app.get("/convert")
def convert(google_url: str):
    if not google_url:
        raise HTTPException(status_code=400, detail="Missing google_url")

    # Step 1: expand URL
    expanded_url = expand_url(google_url)

    # Step 2: extract data
    place = extract_place(expanded_url)
    lat, lng = extract_lat_lng(expanded_url)

    if not lat or not lng:
        raise HTTPException(status_code=400, detail="Could not extract coordinates")

    # Step 3: fallback to reverse geocode
    if not place:
        place = reverse_geocode(lat, lng)

    # Step 4: build Apple Maps link
    apple_url = build_apple_maps_url(place, lat, lng)
    print(f"Converted Google Maps URL: {google_url} to Apple Maps URL: {apple_url}")
    # return redirect 
    return RedirectResponse(apple_url)
    return {
        "input_url": google_url,
        "expanded_url": expanded_url,
        "place": place,
        "lat": lat,
        "lng": lng,
        "apple_maps": apple_url
    }