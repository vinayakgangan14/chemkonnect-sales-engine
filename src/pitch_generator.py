# src/pitch_generator.py
import sys
import json
import os
from typing import Dict, Any, Optional

# Ensure UTF-8 stdout
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from lead_manager import LeadManager

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'products.json')

class PitchGenerator:
    def __init__(self, catalog_path: str = CATALOG_PATH, lead_manager: Optional[LeadManager] = None):
        self.catalog_path = catalog_path
        self.lm = lead_manager or LeadManager()
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> Dict[str, Any]:
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def match_product_category(self, query_or_category: str) -> str:
        text = query_or_category.lower()
        # Priority order matching: Check specific keywords first
        if any(k in text for k in ['gypsum', 'false ceiling', 'plasterboard', 'ceiling', 'drywall', 'perimeter channel']):
            return 'gypsum_and_ceilings'
        elif any(k in text for k in ['expansion joint', 'jsw', 'movement joint', 'tmt', 'rebar', 'steel rod']):
            return 'structural_and_joints'
        elif any(k in text for k in ['dr. fixit', 'fixit', 'waterproof', 'pidiproof', 'fastflex', 'raincoat']):
            return 'construction_chemicals'
        elif any(k in text for k in ['plywood', 'marine ply', 'bwp 710', 'mr grade ply', 'calibrated ply', 'hdhmr', 'shuttering ply', 'ply']):
            return 'plywood_and_boards'
        elif any(k in text for k in ['fevicol', 'adhesive', 'sh', 'marine adhesive', 'heatx', 'probond', 'carpenter', 'modular']):
            return 'pidilite_adhesives'
        elif any(k in text for k in ['chemical', 'solvent', 'acetone', 'toluene', 'ipa', 'isopropanol', 'acetate', 'resin', 'paint', 'pharma', 'intermediate']):
            return 'industrial_chemicals_and_solvents'
        elif any(k in text for k in ['civil', 'builder', 'contractor', 'concrete']):
            return 'construction_chemicals'
        elif any(k in text for k in ['interior', 'designer', 'architect']):
            return 'gypsum_and_ceilings'
        return 'pidilite_adhesives'

    def classify_region_priority(self, location: str) -> str:
        loc_lower = location.lower()
        priority_keywords = ['mumbai', 'navi mumbai', 'thane', 'dombivli', 'kalyan', 'bhiwandi', 'pune', 'gujarat', 'vapi', 'surat', 'ahmedabad', 'maharashtra']
        if any(k in loc_lower for k in priority_keywords):
            return "High Priority (Core Belt: MMR / Pune / Gujarat / MH)"
        elif any(k in loc_lower for k in ['uae', 'dubai', 'oman', 'usa', 'africa', 'singapore', 'export', 'abroad', '+971', '+1', '+44']):
            return "Export (Global)"
        return "Pan-India"

    def generate_whatsapp_pitch(self, lead: Dict[str, Any]) -> str:
        name = lead.get('name', 'Sir/Madam')
        category = lead.get('category', 'Material Requirements')
        city = lead.get('city') or lead.get('area') or 'Maharashtra'
        matched_cat_key = self.match_product_category(category)
        matched_cat = self.catalog['categories'].get(matched_cat_key, {})
        
        products_list = matched_cat.get('products', [])
        product_highlights = "\n".join([f"• *{p['name']}*: {p['description']}" for p in products_list[:2]])

        whatsapp_text = f"""Hello {name},

Greetings from *Chemkonnect Global* (Dombivli / Thane).

We noticed your requirement for *{category}* in *{city}*. We are authorized B2B distributors providing wholesale direct-to-site supply:

{product_highlights}

✔ Direct Authorized Sourcing & GST Billing
✔ Ready Stock in Dombivli/Thane Hub (Prompt dispatch to Mumbai, Navi Mumbai, Pune, Gujarat & Pan-India)
✔ Project-tier contractor and bulk pricing

Would you like us to share our current contractor wholesale rate sheet or send an instant quote for your site?

Best regards,
*Sales Desk | Chemkonnect Global*
📞 +91 76780 51141
🌐 chemkonnect.com"""
        return whatsapp_text

    def generate_email_pitch(self, lead: Dict[str, Any]) -> Dict[str, str]:
        name = lead.get('name', 'Business Owner')
        category = lead.get('category', 'Valued Partner')
        city = lead.get('city') or lead.get('area') or 'Maharashtra'
        matched_cat_key = self.match_product_category(category)
        matched_cat = self.catalog['categories'].get(matched_cat_key, {})
        
        products_list = matched_cat.get('products', [])
        product_bullets = "\n".join([f"- **{p['name']}**: {p['application']} (Available in: {', '.join(p['pack_sizes'])})" for p in products_list])

        subject = f"B2B Material Supply & Distributor Pricing for {name} ({city})"
        
        body = f"""Dear {name} Team,

I hope this message finds you well.

I am reaching out from Chemkonnect Global, an authorized distributor and industrial supplier headquartered in Dombivli/Thane.

For your requirements in {city}, we maintain dedicated inventory with rapid logistics across Mumbai, Navi Mumbai, Pune, Maharashtra, Gujarat, and Pan-India:

{product_bullets}

Why partner with Chemkonnect Global?
1. Authorized Direct Distribution: Pidilite adhesives, Dr. Fixit, Certified Plywood (BWP 710/MR), Gypsum ceiling systems, JSW expansion joints, and industrial solvents.
2. Competitive Bulk Rates: Dedicated price tiers for ongoing contractors, interior fit-outs, and manufacturing units.
3. Rapid Site Dispatch: Local warehouse inventory ensures zero project downtime.

Could we share our commercial rate card or prepare a customized quote for your upcoming requirements?

Warm regards,

Chemkonnect Global Sales Team
Email: info@chemkonnect.com
Phone: +91 76780 51141
Website: https://chemkonnect.com
Dombivli / Thane, Maharashtra
"""
        return {"subject": subject, "body": body}

    def generate_pitch_for_lead(self, lead_id: int) -> Dict[str, Any]:
        leads = self.lm.get_leads(limit=500)
        target_lead = next((l for l in leads if l['id'] == lead_id), None)
        if not target_lead:
            raise ValueError(f"Lead with ID #{lead_id} not found.")

        wa_pitch = self.generate_whatsapp_pitch(target_lead)
        email_pitch = self.generate_email_pitch(target_lead)

        full_pitch = f"--- WHATSAPP PITCH ---\n{wa_pitch}\n\n--- EMAIL PITCH ---\nSubject: {email_pitch['subject']}\n\n{email_pitch['body']}"
        self.lm.update_lead(lead_id, pitch_draft=full_pitch, status='Pitched')

        return {
            "lead_id": lead_id,
            "lead_name": target_lead['name'],
            "category": target_lead['category'],
            "whatsapp_message": wa_pitch,
            "email_pitch": email_pitch
        }

if __name__ == "__main__":
    pg = PitchGenerator()
    print("Testing matching logic:")
    print("Gypsum query ->", pg.match_product_category("Gypsum Plasterboards 12.5mm and GI Channels"))
    print("Plywood query ->", pg.match_product_category("BWP 710 Marine Plywood 16mm"))
    print("Expansion joint query ->", pg.match_product_category("JSW Architectural Expansion Joints"))
    print("Solvents query ->", pg.match_product_category("Acetone and industrial solvents"))