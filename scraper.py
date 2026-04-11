"""
Lead Scraper Engine
- Scrapes Google Search results for businesses
- Falls back to demo data if scraping fails
"""

import requests
from bs4 import BeautifulSoup
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def scrape_google(keyword: str, location: str, limit: int = 10) -> list[dict]:
    """Scrape business listings from Google search."""
    results = []
    query = f"{keyword} businesses in {location}"
    url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=20"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract organic results
        for g in soup.select("div.g")[:limit]:
            title_el = g.select_one("h3")
            link_el = g.select_one("a")
            snippet_el = g.select_one("div.VwiC3b")

            if title_el and link_el:
                href = link_el.get("href", "")
                if href.startswith("/url?q="):
                    href = href.split("/url?q=")[1].split("&")[0]
                if not href.startswith("http"):
                    continue

                results.append({
                    "business": title_el.get_text(strip=True),
                    "website": href,
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "source": "google"
                })

        time.sleep(random.uniform(1, 2))  # polite delay

    except Exception as e:
        print(f"[Scraper] Google scrape failed: {e}")

    return results[:limit]


def scrape_leads(keyword: str, location: str, limit: int = 10) -> list[dict]:
    """
    Main scraping function. Tries Google, falls back to demo data.
    """
    results = scrape_google(keyword, location, limit)

    # If scraping returned too few results, supplement with demo data
    if len(results) < 3:
        results = _demo_leads(keyword, location, limit)

    return results[:limit]


def _demo_leads(keyword: str, location: str, limit: int) -> list[dict]:
    """Returns realistic demo leads when scraping isn't available."""
    industry_map = {
        "restaurant": ["Spice Garden", "The Food Corner", "Tasty Bites", "Royal Kitchen", "Urban Cafe"],
        "real estate": ["Prime Properties", "City Homes", "Dream Realty", "Elite Estates", "Urban Builders"],
        "coaching": ["Success Academy", "BrightMind Institute", "TopRank Coaching", "Excel Classes", "Future Leaders"],
        "healthcare": ["City Health Clinic", "LifeCare Hospital", "Wellness Center", "MedPlus Clinic", "Health First"],
        "interior": ["Creative Spaces", "HomeStyle Interiors", "Design Studio", "Luxe Interiors", "Space Craft"],
        "ecommerce": ["ShopNow Online", "QuickBuy Store", "Daily Deals", "FastCart", "TrendShop"],
        "gym": ["PowerFit Gym", "IronZone", "FitLife Center", "Flex Studio", "ActiveBody"],
        "salon": ["Glamour Studio", "Style Zone", "Bliss Salon", "ChicCuts", "Beauty Hub"],
    }

    key = keyword.lower()
    names = None
    for k, v in industry_map.items():
        if k in key:
            names = v
            break
    if not names:
        names = [f"{keyword.title()} Business {i+1}" for i in range(10)]

    demo = []
    for i, name in enumerate(names[:limit]):
        slug = name.lower().replace(" ", "")
        demo.append({
            "business": f"{name} - {location}",
            "website": f"https://www.{slug}.com",
            "snippet": f"{name} is a leading {keyword} business in {location}.",
            "source": "demo"
        })
    return demo
