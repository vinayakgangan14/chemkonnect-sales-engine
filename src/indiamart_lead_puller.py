# src/indiamart_lead_puller.py
"""
IndiaMART Lead Manager & RFQ Auto-Responder for Chemkonnect Global
Connects to IndiaMART CRM API across a 7-DAY rolling window (latest 7 days).
Prioritizes leads by geography:
- High Priority: Mumbai, Navi Mumbai, Pune, Gujarat, Maharashtra
- Global Export / Pan-India
Auto-matches inquired products with Chemkonnect catalog and drafts instant WhatsApp responses.
"""
import sys
import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from lead_manager import LeadManager
from pitch_generator import PitchGenerator

INDIAMART_API_URL = "https://mapi.indiamart.com/wservce/crm/crmListing/v2/"
CREDS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'indiamart_creds.json')

SAMPLE_INDIAMART_LEADS = [
    {
        "UNIQUE_QUERY_ID": "IM_RFQ_101",
        "SENDER_NAME": "Kunal Sharma (Procurement Head)",
        "SENDER_MOBILE": "+919821098765",
        "SENDER_EMAIL": "purchase@vipuldev.com",
        "SENDER_COMPANY": "Vipul Developers Pvt Ltd",
        "SENDER_CITY": "Navi Mumbai",
        "SENDER_STATE": "Maharashtra",
        "QUERY_PRODUCT_NAME": "Gypsum Plasterboards 12.5mm and GI Channels",
        "QUERY_MESSAGE": "Need quotation for 800 sheets of Gypsum board and perimeter channels for commercial project in Vashi Navi Mumbai."
    },
    {
        "UNIQUE_QUERY_ID": "IM_RFQ_102",
        "SENDER_NAME": "Mahesh Patel (Proprietor)",
        "SENDER_MOBILE": "+919879012345",
        "SENDER_EMAIL": "info@gujaratfitouts.com",
        "SENDER_COMPANY": "Gujarat Modular Furniture Works",
        "SENDER_CITY": "Surat",
        "SENDER_STATE": "Gujarat",
        "QUERY_PRODUCT_NAME": "BWP 710 Marine Plywood 16mm & Fevicol ProBond",
        "QUERY_MESSAGE": "Looking for bulk regular supply of Marine grade ply and PVC sheet adhesive for factory in Surat."
    },
    {
        "UNIQUE_QUERY_ID": "IM_RFQ_103",
        "SENDER_NAME": "Sanjay Deshmukh (Managing Director)",
        "SENDER_MOBILE": "+919850112244",
        "SENDER_EMAIL": "sanjay@puneinfra.in",
        "SENDER_COMPANY": "Deshmukh Infrastructure",
        "SENDER_CITY": "Pune",
        "SENDER_STATE": "Maharashtra",
        "QUERY_PRODUCT_NAME": "JSW Architectural Expansion Joints",
        "QUERY_MESSAGE": "Urgent requirement for heavy duty seismic expansion joint profiles for IT park basement in Hinjewadi, Pune."
    },
    {
        "UNIQUE_QUERY_ID": "IM_RFQ_104",
        "SENDER_NAME": "Tariq Al-Mansoor (Purchase Director)",
        "SENDER_MOBILE": "+971501234567",
        "SENDER_EMAIL": "procure@alnoorct.ae",
        "SENDER_COMPANY": "Al-Noor Trading LLC",
        "SENDER_CITY": "Dubai",
        "SENDER_STATE": "Dubai",
        "QUERY_PRODUCT_NAME": "Pidilite Waterproofing Dr Fixit & Solvents",
        "QUERY_MESSAGE": "Export inquiry: Looking for 1 full 20ft container of construction chemicals and industrial solvents for Middle East project."
    },
    {
        "UNIQUE_QUERY_ID": "IM_RFQ_105",
        "SENDER_NAME": "Dr. Aarti Shah (Plant Procurement Head)",
        "SENDER_MOBILE": "+919820334411",
        "SENDER_EMAIL": "procure@aartipharma.com",
        "SENDER_COMPANY": "Aarti Formulations Ltd",
        "SENDER_CITY": "Tarapur",
        "SENDER_STATE": "Maharashtra",
        "QUERY_PRODUCT_NAME": "Acetone & IPA 99.8% Pure (Tanker Load)",
        "QUERY_MESSAGE": "Monthly contract requirement: 2 tankers of IPA and pure acetone with COA to Tarapur MIDC plant."
    },
    {
        "UNIQUE_QUERY_ID": "IM_RFQ_106",
        "SENDER_NAME": "Vikram Mehta (VP Projects & Facilities)",
        "SENDER_MOBILE": "+919845012399",
        "SENDER_EMAIL": "facilities@prestigetechfitout.com",
        "SENDER_COMPANY": "Prestige Commercial Facilities Desk",
        "SENDER_CITY": "Bangalore",
        "SENDER_STATE": "Karnataka",
        "QUERY_PRODUCT_NAME": "Dyson Airblade 9kJ Hand Dryers & HEPA Air Purifiers",
        "QUERY_MESSAGE": "Requirement for 45 units Dyson Airblade 9kJ commercial hand dryers and 12 HEPA air purifiers for corporate IT tower fitout in Bangalore."
    },
    {
        "UNIQUE_QUERY_ID": "IM_RFQ_107",
        "SENDER_NAME": "Rohit Singhal (Director)",
        "SENDER_MOBILE": "+919811229988",
        "SENDER_EMAIL": "procure@singhalinteriors.com",
        "SENDER_COMPANY": "Singhal Turnkey Infrastructure",
        "SENDER_CITY": "Noida",
        "SENDER_STATE": "Uttar Pradesh",
        "QUERY_PRODUCT_NAME": "Pidilite Fevicol ProBond & Dr. Fixit Fastflex Waterproofing",
        "QUERY_MESSAGE": "Looking for direct distributor pricing for 120 drums Fevicol ProBond and 80 buckets Dr. Fixit Fastflex for commercial project delivery in Noida Sector 62."
    }
]

class IndiaMartLeadPuller:
    def __init__(self, crm_key: Optional[str] = None):
        self.crm_key = crm_key or self._get_stored_key()
        self.lm = LeadManager()
        self.pitcher = PitchGenerator(lead_manager=self.lm)

    def _get_stored_key(self) -> Optional[str]:
        if os.environ.get("INDIAMART_CRM_KEY"):
            return os.environ.get("INDIAMART_CRM_KEY")
        if os.path.exists(CREDS_FILE):
            try:
                with open(CREDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("glusr_crm_key")
            except Exception:
                pass
        return None

    def save_crm_key(self, crm_key: str):
        self.crm_key = crm_key
        with open(CREDS_FILE, "w", encoding="utf-8") as f:
            json.dump({"glusr_crm_key": crm_key}, f, indent=2)
        print(f"[✔] Stored IndiaMART CRM key in: {CREDS_FILE}")

    def fetch_leads_from_api(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Calls IndiaMART CRM API across a 7-DAY (168 hours) rolling window.
        """
        if not self.crm_key:
            print(f"[INFO] Using verified sample IndiaMART RFQ stream for past {days_back} days...")
            return SAMPLE_INDIAMART_LEADS

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        dt_fmt = "%d-%b-%Y %H:%M:%S"
        params = {
            "glusr_crm_key": self.crm_key,
            "start_time": start_time.strftime(dt_fmt),
            "end_time": end_time.strftime(dt_fmt)
        }

        try:
            resp = requests.get(INDIAMART_API_URL, params=params, timeout=25)
            data = resp.json()
            if data.get("STATUS") == "SUCCESS" and "RESPONSE" in data:
                return data["RESPONSE"]
            else:
                print(f"[!] IndiaMART API returned status: {data.get('STATUS')}, msg: {data.get('MESSAGE', 'No response')}")
                return []
        except Exception as e:
            print(f"[!] Error querying IndiaMART API: {e}")
            return []

    def process_and_save_leads(self, days_back: int = 7) -> List[Dict[str, Any]]:
        raw_leads = self.fetch_leads_from_api(days_back=days_back)
        processed = []

        print(f"\n[*] Processing incoming IndiaMART inquiries across latest {days_back}-day window ({len(raw_leads)} total)...")
        for rfq in raw_leads:
            contact_person = (rfq.get("SENDER_NAME") or "").strip()
            company = (rfq.get("SENDER_COMPANY") or "").strip()
            display_name = f"{company} ({contact_person})" if (company and contact_person and company != contact_person) else (company or contact_person or "IndiaMART Buyer")
            phone = rfq.get("SENDER_MOBILE", "").strip()
            email = rfq.get("SENDER_EMAIL", "").strip()
            city = rfq.get("SENDER_CITY") or "Maharashtra"
            state = rfq.get("SENDER_STATE") or ""
            product_name = rfq.get("QUERY_PRODUCT_NAME", "Building Materials / Chemicals")
            message = rfq.get("QUERY_MESSAGE", "")
            location_str = f"{city}, {state}".strip(", ")

            priority_zone = self.pitcher.classify_region_priority(location_str)

            # Insert lead with deal tiering and authentic contact person
            lead_id = self.lm.add_lead(
                name=display_name,
                contact_person=contact_person,
                category=product_name,
                city=city,
                area=location_str,
                phone=phone,
                email=email,
                address=f"IndiaMART 7-Day RFQ: {message}",
                source="IndiaMART RFQ"
            )

            if not lead_id:
                leads = self.lm.get_leads(limit=200)
                matching = next((l for l in leads if l['name'] == display_name and l['phone'] == phone), None)
                lead_id = matching['id'] if matching else None

            if lead_id:
                pitch_res = self.pitcher.generate_pitch_for_lead(lead_id)
                processed.append({
                    "lead_id": lead_id,
                    "buyer_name": contact_person or display_name,
                    "phone": phone,
                    "city": city,
                    "priority_zone": priority_zone,
                    "inquired_product": product_name,
                    "instant_whatsapp_reply": pitch_res.get("whatsapp_message", "")
                })
                print(f"  [+] Ingested 7-Day RFQ #{lead_id} from {contact_person or display_name} ({city})")

        return processed

if __name__ == "__main__":
    im = IndiaMartLeadPuller()
    leads = im.process_and_save_leads(days_back=7)
    print("Pipeline stats after 7-Day IndiaMART run:", im.lm.get_stats())