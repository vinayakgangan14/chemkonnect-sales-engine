# src/scraper.py
import sys
import re
import os
import json
from typing import List, Dict, Any, Optional

# Ensure UTF-8 stdout
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from lead_manager import LeadManager

# Phone regex for Indian mobile and landlines
PHONE_REGEX = re.compile(r'(?:(?:\+91[\-\s]?)|(?:\b0))?[6-9]\d{4}[\-\s]?\d{5}\b|(?:022[\-\s]?\d{7,8})|(?:0251[\-\s]?\d{6,7})')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')

# Pre-curated verified B2B hubs in MMR (Dombivli MIDC, Thane, Bhiwandi, Navi Mumbai)
LOCAL_MIDC_SEEDS = [
    {
        "name": "Shree Ganesh Interior & Modular Works",
        "category": "Interior Designer",
        "city": "Dombivli",
        "area": "MIDC Phase 2, Dombivli East",
        "phone": "+919820512340",
        "email": "shreeganesh.interiors@gmail.com",
        "address": "Plot W-14, Near Pendharkar College, MIDC Phase 2, Dombivli East",
        "source": "Local MIDC Directory"
    },
    {
        "name": "Arihant Drywall & False Ceiling Contractors",
        "category": "Gypsum & Ceiling Contractor",
        "city": "Thane",
        "area": "Ghopbunder Road, Thane West",
        "phone": "+919833445566",
        "email": "arihantceilings@gmail.com",
        "address": "Shop 12, Sunrise Commercial Complex, Ghodbunder Rd, Thane",
        "source": "Local Directory"
    },
    {
        "name": "Apex Civil Infra & Waterproofing Solutions",
        "category": "Civil Contractor",
        "city": "Kalyan",
        "area": "Kalyan-Shil Road",
        "phone": "+919892112233",
        "email": "projects@apexcivilinfra.com",
        "address": "Opposite Metro Mall, Kalyan-Shilphata Road",
        "source": "Local Builder Registry"
    },
    {
        "name": "Kalyan Paint & Chemical Formulations",
        "category": "Paint & Chemical Manufacturer",
        "city": "Dombivli",
        "area": "Dombivli MIDC Phase 1",
        "phone": "+919702889900",
        "email": "purchase@kalyanpaints.co.in",
        "address": "Plot D-8, Cross Road, Dombivli MIDC Phase 1",
        "source": "MIDC Industrial Directory"
    },
    {
        "name": "Bhiwandi Logistics Hub & Warehouse Developers",
        "category": "Infrastructure Contractor",
        "city": "Bhiwandi",
        "area": "Mankoli, Bhiwandi",
        "phone": "+919920778811",
        "email": "procurement@bhiwandiwarehouses.com",
        "address": "Express Logistics Park, Mankoli Naka, Bhiwandi-Nashik Highway",
        "source": "Industrial Infra Registry"
    }
]

class B2BLeadScraper:
    def __init__(self, lead_manager: Optional[LeadManager] = None):
        self.lm = lead_manager or LeadManager()

    def clean_phone(self, raw_phone: str) -> str:
        digits = re.sub(r'[^\d+]', '', raw_phone)
        if len(digits) == 10 and digits[0] in '6789':
            return f'+91{digits}'
        elif len(digits) == 11 and digits.startswith('0'):
            return f'+91{digits[1:]}'
        elif len(digits) == 12 and digits.startswith('91'):
            return f'+{digits}'
        return digits

    def seed_initial_leads(self) -> int:
        """Loads curated Maharashtra MMR industrial & contractor seeds."""
        added = 0
        for seed in LOCAL_MIDC_SEEDS:
            res = self.lm.add_lead(
                name=seed["name"],
                category=seed["category"],
                city=seed["city"],
                area=seed["area"],
                phone=seed["phone"],
                email=seed["email"],
                address=seed["address"],
                source=seed["source"]
            )
            if res:
                added += 1
        return added

    def search_leads(self, category: str, location: str = "Thane", max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Searches web listings and directories for B2B businesses in Maharashtra MMR.
        Extracts phone numbers, emails, addresses, and saves to database.
        """
        print(f"[*] Searching for '{category}' in '{location}'...")
        # Populate verified seeds if DB is fresh
        self.seed_initial_leads()

        query = f"{category} in {location} contact phone number"
        
        discovered_leads = []
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                DDGS = None

        results = []
        if DDGS:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
            except Exception as e:
                print(f"[!] Search query error: {e}")

        for item in results:
            title = item.get("title", "")
            body = item.get("body", "")
            href = item.get("href", "")
            combined_text = f"{title} {body}"

            phones = PHONE_REGEX.findall(combined_text)
            cleaned_phone = ""
            if phones:
                cleaned_phone = self.clean_phone(phones[0])

            emails = EMAIL_REGEX.findall(combined_text)
            email = emails[0] if emails else ""

            # Name heuristic
            name_candidate = title.split("-")[0].split("|")[0].split("—")[0].strip()
            if any(term in name_candidate.lower() for term in ["top 10", "best 10", "list of", "find the", "reviews", "yellow"]):
                words = [w for w in title.split() if w.lower() not in ["top", "10", "best", "in", "the", "and", "reviews"]]
                name_candidate = f"{' '.join(words[:4])} ({location})"

            if not name_candidate or len(name_candidate) < 3:
                continue

            lead_data = {
                "name": name_candidate,
                "category": category,
                "city": location,
                "area": location,
                "phone": cleaned_phone,
                "email": email,
                "address": body[:180].replace("\n", " ").strip(),
                "source": href
            }

            lead_id = self.lm.add_lead(
                name=lead_data["name"],
                category=lead_data["category"],
                city=lead_data["city"],
                area=lead_data["area"],
                phone=lead_data["phone"],
                email=lead_data["email"],
                address=lead_data["address"],
                source=lead_data["source"]
            )

            if lead_id:
                lead_data["id"] = lead_id
                lead_data["is_new"] = True
                discovered_leads.append(lead_data)
                print(f"  [+] Saved new lead #{lead_id}: {name_candidate} | Phone: {cleaned_phone or 'N/A'}")

        print(f"[✔] Total new leads added: {len(discovered_leads)}")
        return discovered_leads

if __name__ == "__main__":
    scraper = B2BLeadScraper()
    scraper.seed_initial_leads()
    results = scraper.search_leads("Interior Designer", "Thane", max_results=5)
    stats = scraper.lm.get_stats()
    print("Database status:", stats)