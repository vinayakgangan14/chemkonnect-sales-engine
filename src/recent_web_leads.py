# src/recent_web_leads.py
"""
Internet-Wide Real-Time B2B Lead Harvester for Chemkonnect Global
Searches public web, project announcements, social platforms, tenders, and directories
strictly within the LAST 7 DAYS (timelimit='w') across:
Mumbai, Navi Mumbai, Pune, Gujarat, and Maharashtra.
"""
import sys
import re
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from lead_manager import LeadManager
from pitch_generator import PitchGenerator

PHONE_REGEX = re.compile(r'(?:(?:\+91[\-\s]?)|(?:\b0))?[6-9]\d{4}[\-\s]?\d{5}\b|(?:022[\-\s]?\d{7,8})|(?:0251[\-\s]?\d{6,7})')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')

class RecentWebLeadHarvester:
    def __init__(self, lead_manager: Optional[LeadManager] = None):
        self.lm = lead_manager or LeadManager()
        self.pitcher = PitchGenerator(lead_manager=self.lm)

    def clean_phone(self, raw: str) -> str:
        digits = re.sub(r'[^\d+]', '', raw)
        if len(digits) == 10 and digits[0] in '6789':
            return f"+91{digits}"
        elif len(digits) == 11 and digits.startswith('0'):
            return f"+91{digits[1:]}"
        elif len(digits) == 12 and digits.startswith('91'):
            return f"+{digits}"
        return digits

    def find_fresh_leads(self, 
                         product_keyword: str = "Gypsum board", 
                         location: str = "Mumbai", 
                         timelimit: str = "w", 
                         max_results_per_pattern: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the open internet for posts, tenders, contractors, and businesses active in the LAST 7 DAYS.
        timelimit: 'w' = past 7 days, 'd' = past 24 hours.
        """
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        print(f"\n[*] Scanning the internet for fresh leads in the LAST 7 DAYS...")
        print(f"[*] Target Product: '{product_keyword}' | Target Region: '{location}' (Time Window: Past 7 Days)")

        # Natural search patterns that return rich recent results
        patterns = [
            f"{product_keyword} {location}",
            f"{product_keyword} dealers {location}",
            f"{product_keyword} contractor {location}",
            f"interior designer {location}",
            f"construction tenders Maharashtra"
        ]

        raw_results = []
        with DDGS() as ddgs:
            for query in patterns:
                try:
                    res = list(ddgs.text(query, timelimit=timelimit, max_results=max_results_per_pattern))
                    print(f"  [+] Query '{query}' returned {len(res)} recent 7-day items")
                    raw_results.extend(res)
                except Exception as e:
                    print(f"  [!] Query '{query}' notice: {e}")

        # Deduplicate results by URL
        seen_urls = set()
        unique_results = []
        for r in raw_results:
            url = r.get("href", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)

        print(f"[*] Processing {len(unique_results)} fresh results from the past 7 days across the web...")

        discovered_leads = []
        for item in unique_results:
            title = item.get("title", "")
            body = item.get("body", "")
            href = item.get("href", "")
            combined_text = f"{title} {body}"

            phones = PHONE_REGEX.findall(combined_text)
            phone = self.clean_phone(phones[0]) if phones else ""

            emails = EMAIL_REGEX.findall(combined_text)
            email = emails[0] if emails else ""

            # Detect location mentioned
            detected_city = location
            for loc in ["Navi Mumbai", "Pune", "Thane", "Dombivli", "Kalyan", "Bhiwandi", "Surat", "Vapi", "Ahmedabad", "Gujarat", "Maharashtra", "Mumbai"]:
                if loc.lower() in combined_text.lower():
                    detected_city = loc
                    break

            # Clean name candidate
            name = title.split("-")[0].split("|")[0].split("—")[0].strip()
            if any(term in name.lower() for term in ["top 10", "best 10", "list of", "find the", "reviews"]):
                name = f"{product_keyword} Business ({detected_city})"

            if not name or len(name) < 3:
                continue

            priority_zone = self.pitcher.classify_region_priority(detected_city)

            lead_id = self.lm.add_lead(
                name=name,
                category=product_keyword,
                city=detected_city,
                area=detected_city,
                phone=phone,
                email=email,
                address=f"Web 7-Day Discovery: {body[:190]}...",
                source=href
            )

            if lead_id:
                pitch_res = self.pitcher.generate_pitch_for_lead(lead_id)
                lead_summary = {
                    "lead_id": lead_id,
                    "name": name,
                    "phone": phone or "Found via web link",
                    "email": email or "N/A",
                    "city": detected_city,
                    "priority_zone": priority_zone,
                    "source_url": href,
                    "whatsapp_pitch": pitch_res["whatsapp_message"]
                }
                discovered_leads.append(lead_summary)
                print(f"  [✔] Saved Lead #{lead_id}: {name} ({detected_city})")

        print(f"[✔] Total fresh leads saved: {len(discovered_leads)}")
        return discovered_leads

if __name__ == "__main__":
    harvester = RecentWebLeadHarvester()
    fresh = harvester.find_fresh_leads("Gypsum board", "Mumbai", timelimit="w")
    print(f"\nHarvested {len(fresh)} fresh leads from past 7 days.")
    csv_file = harvester.lm.export_to_csv()
    print("CSV updated at:", csv_file)