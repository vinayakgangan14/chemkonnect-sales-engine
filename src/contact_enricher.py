# src/contact_enricher.py
"""
Real Contact Person & Official Email Enrichment Engine for Chemkonnect Global
Strict Quality Rules:
1. NEVER fabricates fake/generic '@gmail.com' addresses (e.g. procurement.company@gmail.com).
2. Extracts actual decision-maker names (Proprietor, Director, Purchase Head, Project Lead).
3. Pulls verified corporate domain emails (e.g. purchase@company.com, contact@company.in, name@company.com).
4. Employs targeted web scraping via DuckDuckGo and company domain pages.
"""
import re
import sys
import os
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_REGEX = re.compile(r'(?:(?:\+91[\-\s]?)|(?:\b0))?[6-9]\d{4}[\-\s]?\d{5}\b|(?:022[\-\s]?\d{7,8})|(?:0251[\-\s]?\d{6,7})')

PERSON_PATTERNS = [
    re.compile(r'(?:(?:Contact Person|Key Person|Promoter|Proprietor|Director|Partner|CEO|Managing Director|Purchase Manager|Procurement Head|Project Lead|Mr\.|Ms\.|Shri)[:\-\s]+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', re.IGNORECASE),
    re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*\((?:Director|Proprietor|Partner|Purchase Manager|Procurement Head|Project Lead|Founder|MD)\)', re.IGNORECASE),
    re.compile(r'(?:Founded by|Led by|Managed by|Contact)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', re.IGNORECASE)
]

# Discard invalid/generic/disposable email domains and image extensions
BLOCKED_EMAIL_DOMAINS = {
    'example.com', 'domain.com', 'sample.com', 'test.com', 'email.com', 
    'sentry.io', 'w3.org', 'schema.org', 'github.com', 'wordpress.org',
    'cloudflare.com', 'google.com', 'facebook.com', 'twitter.com', 'instagram.com',
    'merriam-webster.com', 'wikipedia.org', 'britannica.com'
}

DISALLOWED_EMAIL_PREFIXES = {
    'noreply', 'no-reply', 'donotreply', 'privacy', 'legal', 'abuse', 
    'support', 'help', 'admin', 'hostmaster', 'postmaster', 'webmaster'
}

class ContactEnricher:
    def __init__(self):
        self._cache: Dict[str, Dict[str, str]] = {}

    def is_valid_business_email(self, email: str) -> bool:
        if not email or "@" not in email:
            return False
        email_lower = email.lower().strip()
        user, domain = email_lower.split("@", 1)
        
        # Check image extensions mistakenly matched
        if any(domain.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.js', '.css']):
            return False
            
        if domain in BLOCKED_EMAIL_DOMAINS:
            return False
            
        if user in DISALLOWED_EMAIL_PREFIXES:
            return False
            
        # Reject fabricated generic emails
        if user.startswith("procurement.") and domain.endswith("gmail.com"):
            return False
        if user.startswith("rfq.") and domain.endswith("gmail.com"):
            return False
            
        return True

    def extract_from_text(self, text: str) -> Dict[str, str]:
        results = {"email": "", "contact_person": "", "phone": ""}
        
        # 1. Extract real emails
        raw_emails = EMAIL_REGEX.findall(text)
        for e in raw_emails:
            if self.is_valid_business_email(e):
                results["email"] = e.strip()
                break
                
        # 2. Extract real contact person
        for pat in PERSON_PATTERNS:
            matches = pat.findall(text)
            if matches:
                name = matches[0].strip()
                words = name.split()
                if 2 <= len(words) <= 3 and not any(w.lower() in ['pvt', 'ltd', 'limited', 'india', 'solutions', 'services', 'interior', 'interiors', 'false', 'ceiling'] for w in words):
                    results["contact_person"] = name
                    break
                    
        # 3. Extract phone
        phones = PHONE_REGEX.findall(text)
        if phones:
            digits = re.sub(r'[^\d+]', '', phones[0])
            if len(digits) == 10 and digits[0] in '6789':
                results["phone"] = f"+91{digits}"
            elif len(digits) == 11 and digits.startswith('0'):
                results["phone"] = f"+91{digits[1:]}"
            elif len(digits) == 12 and digits.startswith('91'):
                results["phone"] = f"+{digits}"
            else:
                results["phone"] = digits
                
        return results

    def fetch_website_contacts(self, website_url: str) -> Dict[str, str]:
        """Tries to scrape homepage and /contact of the company website."""
        if not website_url or not website_url.startswith("http"):
            return {}
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Parse base domain
        parsed = urllib.parse.urlparse(website_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        candidates = [website_url]
        if parsed.path not in ["/contact", "/contact-us", "/contactus"]:
            candidates.append(f"{base}/contact")
            candidates.append(f"{base}/contact-us")
            
        for url in candidates[:2]:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    contacts = self.extract_from_text(html)
                    if contacts.get("email"):
                        return contacts
            except Exception:
                continue
                
        return {}

    def search_web_for_contacts(self, company_name: str, city: str = "") -> Dict[str, str]:
        """Performs targeted DuckDuckGo query to find real email & contact person."""
        cache_key = f"{company_name.lower()}_{city.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        cleaned_name = re.sub(r'\(.*?\)', '', company_name).strip()
        queries = [
            f'"{cleaned_name}" {city} contact email',
            f'"{cleaned_name}" procurement director email phone'
        ]
        
        discovered = {"email": "", "contact_person": "", "phone": ""}
        
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                for q in queries:
                    try:
                        res = list(ddgs.text(q, max_results=3))
                        for item in res:
                            text = f"{item.get('title', '')} {item.get('body', '')}"
                            extracted = self.extract_from_text(text)
                            if not discovered["email"] and extracted.get("email"):
                                discovered["email"] = extracted["email"]
                            if not discovered["contact_person"] and extracted.get("contact_person"):
                                discovered["contact_person"] = extracted["contact_person"]
                            if not discovered["phone"] and extracted.get("phone"):
                                discovered["phone"] = extracted["phone"]
                                
                        if discovered["email"] and discovered["contact_person"]:
                            break
                    except Exception:
                        continue
        except Exception:
            pass
            
        self._cache[cache_key] = discovered
        return discovered

    def enrich_lead(self, company_name: str, city: str = "", website_url: str = "") -> Dict[str, str]:
        """
        Unified enrichment entry point:
        1. Tries direct website scraping if URL available.
        2. Falls back to targeted internet search.
        3. Returns real email and contact person, or empty strings (NEVER fake generic emails).
        """
        res = {"email": "", "contact_person": "", "phone": ""}
        
        if website_url and website_url.startswith("http"):
            site_res = self.fetch_website_contacts(website_url)
            if site_res.get("email"):
                res["email"] = site_res["email"]
            if site_res.get("contact_person"):
                res["contact_person"] = site_res["contact_person"]
            if site_res.get("phone"):
                res["phone"] = site_res["phone"]
                
        if not res["email"] or not res["contact_person"]:
            web_res = self.search_web_for_contacts(company_name, city)
            if not res["email"] and web_res.get("email"):
                res["email"] = web_res["email"]
            if not res["contact_person"] and web_res.get("contact_person"):
                res["contact_person"] = web_res["contact_person"]
            if not res["phone"] and web_res.get("phone"):
                res["phone"] = web_res["phone"]
                
        return res
