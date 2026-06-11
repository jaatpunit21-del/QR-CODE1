import re
import requests
from urllib.parse import unquote
from utils.logger import get_logger

logger = get_logger("utils.link_resolver")

def resolve_maps_url(target_url):
    """
    Resolves standard or shortened Google Maps links to direct Google Write Review URLs.
    Also extracts the business name.
    Returns (review_url, business_name, error_message)
    """
    # If already a direct review link, return as is
    if "writereview" in target_url:
        # Try to find placeid to use as name fallback or extract query params if name exists
        return target_url, "Google Maps Business", None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        logger.info(f"Resolving Google Maps URL: {target_url}")
        
        # Follow redirects to get the full maps URL
        response = requests.get(target_url, headers=headers, timeout=10)
        final_url = response.url
        html_content = response.text
        
        # Extract Business Name
        business_name = "Google Maps Business"
        
        # Try extracting name from maps URL path: e.g. /maps/place/Five+Star+Pizza/...
        name_match = re.search(r'/maps/place/([^/]+)', final_url)
        if name_match:
            raw_name = name_match.group(1)
            business_name = unquote(raw_name.replace('+', ' '))
            logger.info(f"Extracted business name from URL path: {business_name}")
        else:
            # Fallback: Extract from HTML title tag
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1)
                business_name = title.replace(" - Google Maps", "").replace(" - Google Search", "").strip()
                logger.info(f"Extracted business name from HTML title: {business_name}")
        
        # 1. Search for Place ID (ChI...)
        place_id_match = re.search(r'ChI[a-zA-Z0-9_-]{24}', html_content)
        if place_id_match:
            place_id = place_id_match.group(0)
            resolved_url = f"https://search.google.com/local/writereview?placeid={place_id}"
            logger.info(f"Successfully resolved Place ID: {place_id}")
            return resolved_url, business_name, None
            
        # 2. Search for Customer ID (CID) inside final URL
        cid_match = re.search(r'cid=(\d+)', final_url)
        if cid_match:
            cid = cid_match.group(1)
            resolved_url = f"https://maps.google.com/?cid={cid}&view=create-review"
            logger.info(f"Successfully resolved CID: {cid}")
            return resolved_url, business_name, None
            
        # 3. Search for ludocid inside HTML
        ludocid_match = re.search(r'ludocid=(\d+)', html_content)
        if ludocid_match:
            ludocid = ludocid_match.group(1)
            resolved_url = f"https://maps.google.com/?cid={ludocid}&view=create-review"
            logger.info(f"Successfully resolved Ludocid: {ludocid}")
            return resolved_url, business_name, None

        return None, None, "Could not extract Place ID or CID. Ensure the link points to a physical business."
    except Exception as e:
        logger.error(f"Error during link resolution: {e}")
        return None, None, f"Network error: {str(e)}"
