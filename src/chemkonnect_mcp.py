# src/chemkonnect_mcp.py
"""
Chemkonnect Global - ₹100 Crore Sales MCP Server
Connects Antigravity AI agents to:
- Real Estate Projects Nearing Possession (99acres, MagicBricks, NoBroker, MahaRERA)
- Turnkey Commercial Interior Giants (Ashish Interbuild, Astitva Interiors, Cherry Hill)
- 7-Day Multi-platform Lead Harvester (IndiaMART, TradeIndia, Open Web, Tenders)
- Deal Tiering & Revenue Pipeline Valuation (Tier A Mega accounts, Tier B Commercial projects)
- Automated Quotations & WhatsApp Pitches for:
  Authorized Dealerships: Dyson Commercial Products & Pidilite Adhesives/Chemicals,
  Gypsum & Ceilings, Plywood, JSW Expansion Joints, and Industrial Bulk Solvents.
"""
import sys
import os
import json
from typing import Optional, Dict, Any, List

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from fastmcp import FastMCP
from lead_manager import LeadManager
from scraper import B2BLeadScraper
from pitch_generator import PitchGenerator
from indiamart_lead_puller import IndiaMartLeadPuller
from recent_web_leads import RecentWebLeadHarvester
from tradeindia_scraper import TradeIndiaScraper
from project_and_contractor_harvester import ProjectAndContractorHarvester
from titan_mailer import TitanMailer

mcp = FastMCP("Chemkonnect Sales Engine")
lm = LeadManager()
scraper = B2BLeadScraper(lead_manager=lm)
pitcher = PitchGenerator(lead_manager=lm)
indiamart = IndiaMartLeadPuller()
harvester = RecentWebLeadHarvester(lead_manager=lm)
tradeindia = TradeIndiaScraper(lead_manager=lm)
project_harvester = ProjectAndContractorHarvester(lead_manager=lm)
mailer = TitanMailer()

@mcp.tool()
def get_product_catalog(category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get Chemkonnect Global's complete product catalog.
    Available categories:
    - dyson_commercial_products (Dyson Airblade 9kJ/Wash+Dry/V Hand Dryers, Commercial HEPA Air Purifiers, Supersonic Hair Dryers - Authorized Dealer)
    - pidilite_adhesives (Fevicol SH, Marine, HeatX, ProBond - Authorized Dealer)
    - construction_chemicals (Dr. Fixit LW+, Fastflex, Raincoat - Authorized Dealer)
    - gypsum_and_ceilings (Plasterboards, GI Channels, Jointing Compound)
    - plywood_and_boards (BWP 710 Marine Ply, MR Ply, Calibrated Core, HDHMR)
    - structural_and_joints (JSW Expansion Joints, TMT Steel Rods)
    - industrial_chemicals_and_solvents (Acetone, IPA, Toluene, Ethyl Acetate)
    """
    catalog = pitcher.catalog
    if category:
        cat_data = catalog.get("categories", {}).get(category)
        if not cat_data:
            return {"error": f"Category '{category}' not found.", "available_categories": list(catalog.get("categories", {}).keys())}
        return {"category": category, "details": cat_data}
    return catalog

@mcp.tool()
def harvest_commercial_interior_giants() -> Dict[str, Any]:
    """
    Ingests high-ticket commercial turnkey interior giants (Ashish Interbuild, Astitva Interiors, Cherry Hill)
    and their specialized drywall, false ceiling, and plywood sub-contractors.
    """
    giants = project_harvester.harvest_commercial_interior_giants()
    csv_path = lm.export_to_csv()
    stats = lm.get_stats()
    return {
        "status": "success",
        "giants_ingested": len(giants),
        "pipeline_value_crores": stats["pipeline_value_crores"],
        "giants": giants,
        "exported_csv": csv_path
    }

@mcp.tool()
def harvest_nearing_possession_projects() -> Dict[str, Any]:
    """
    Ingests high-rise residential and commercial towers nearing possession (fit-out, gypsum ceiling,
    framing, plywood, and waterproofing phase) from 99acres, MagicBricks, NoBroker, and MahaRERA.
    """
    projects = project_harvester.harvest_nearing_possession_projects()
    csv_path = lm.export_to_csv()
    stats = lm.get_stats()
    return {
        "status": "success",
        "projects_ingested": len(projects),
        "pipeline_value_crores": stats["pipeline_value_crores"],
        "projects": projects,
        "exported_csv": csv_path
    }

@mcp.tool()
def harvest_recent_web_leads(product_keyword: str, location: str = "Mumbai", timelimit: str = "w") -> Dict[str, Any]:
    """
    Searches the open internet for fresh B2B requirements, contractors, tenders, and project leads.
    """
    fresh_leads = harvester.find_fresh_leads(product_keyword=product_keyword, location=location, timelimit=timelimit)
    csv_path = lm.export_to_csv()
    return {
        "status": "success",
        "timelimit": "Last 7 Days" if timelimit == "w" else "Last 24 Hours",
        "product_keyword": product_keyword,
        "location": location,
        "fresh_leads_found": len(fresh_leads),
        "leads": fresh_leads,
        "exported_csv": csv_path
    }

@mcp.tool()
def pull_indiamart_rfqs(days_back: int = 7) -> Dict[str, Any]:
    """
    Pulls buyer inquiries from IndiaMART Lead Manager API across a 7-day rolling window.
    """
    processed = indiamart.process_and_save_leads(days_back=days_back)
    csv_file = lm.export_to_csv()
    stats = lm.get_stats()
    return {
        "status": "success",
        "inquiries_processed": len(processed),
        "pipeline_value_crores": stats["pipeline_value_crores"],
        "leads": processed,
        "exported_csv": csv_file
    }

@mcp.tool()
def pull_tradeindia_accounts() -> Dict[str, Any]:
    """
    Harvests verified high-value enterprise accounts from TradeIndia directories.
    """
    accounts = tradeindia.harvest_directory()
    csv_file = lm.export_to_csv()
    stats = lm.get_stats()
    return {
        "status": "success",
        "accounts_added": len(accounts),
        "pipeline_value_crores": stats["pipeline_value_crores"],
        "accounts": accounts,
        "exported_csv": csv_file
    }

@mcp.tool()
def set_indiamart_crm_key(crm_key: str) -> Dict[str, str]:
    """
    Saves the user's IndiaMART CRM Integration Key for live API querying.
    """
    indiamart.save_crm_key(crm_key)
    return {
        "status": "success",
        "message": "IndiaMART CRM Key saved successfully. Live RFQs can now be pulled automatically."
    }

@mcp.tool()
def list_pipeline_leads(tier: Optional[str] = None, status: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    """
    List current B2B leads from the local pipeline database with Deal Tiers and valuations.
    """
    leads = lm.get_leads(deal_tier=tier, status=status, limit=limit)
    stats = lm.get_stats()
    return {
        "count": len(leads),
        "pipeline_value_crores": stats["pipeline_value_crores"],
        "percent_of_100cr_goal": stats["percent_of_100cr_goal"],
        "leads": leads,
        "pipeline_summary": stats
    }

@mcp.tool()
def generate_pitch_for_lead(lead_id: int) -> Dict[str, Any]:
    """
    Generates a personalized WhatsApp pitch and email draft for a specific lead ID.
    """
    try:
        res = pitcher.generate_pitch_for_lead(lead_id)
        return {
            "status": "success",
            "pitch_details": res
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def export_leads_to_csv() -> Dict[str, str]:
    """
    Exports all leads, contact info, deal tiers, and generated pitches to an Excel-ready CSV file in output/ directory.
    """
    csv_file = lm.export_to_csv()
    return {
        "status": "success",
        "csv_path": csv_file,
        "message": f"Successfully exported leads to: {csv_file}"
    }

@mcp.tool()
def trigger_pan_india_market_harvest(region: str = "Pan-India (All States)") -> Dict[str, Any]:
    """
    Triggers an instant multi-source market scan across all states of India:
    - Real estate towers nearing possession (99acres, MagicBricks, NoBroker)
    - Turnkey commercial interior giants (Ashish Interbuild, Astitva, Cherry Hill)
    - TradeIndia verified industrial accounts
    - IndiaMART 30-day inquiries
    - Web requirements for Gypsum, Marine Ply, Dr Fixit, Solvents, and JSW Joints across India.
    """
    project_harvester.harvest_nearing_possession_projects()
    project_harvester.harvest_commercial_interior_giants()
    tradeindia.harvest_directory()
    indiamart.process_and_save_leads(days_back=7)
    stats = lm.get_stats()
    return {
        "status": "success",
        "region_scanned": region,
        "total_leads_in_cloud_db": stats["total_leads"],
        "pipeline_value_crores": stats["pipeline_value_crores"],
        "percent_of_100cr_goal": stats["percent_of_100cr_goal"],
        "pipeline_breakdown": stats
    }

@mcp.tool()
def enrich_lead_contact_details(lead_id: int) -> Dict[str, Any]:
    """
    Searches the open internet and company web domain to identify the real contact person
    (Director, Proprietor, Purchase Manager) and verified corporate email for a specific lead.
    NEVER fabricates fake @gmail.com addresses.
    """
    leads = lm.get_leads(limit=2000)
    target = next((l for l in leads if l["id"] == lead_id), None)
    if not target:
        return {"error": f"Lead #{lead_id} not found."}
    
    from contact_enricher import ContactEnricher
    enricher = ContactEnricher()
    enriched = enricher.enrich_lead(
        company_name=target["name"],
        city=target.get("city", "Mumbai"),
        website_url=target.get("source") if (target.get("source") or "").startswith("http") else ""
    )
    
    if enriched.get("email") or enriched.get("contact_person") or enriched.get("phone"):
        lm.update_lead(
            lead_id=lead_id,
            contact_person=enriched.get("contact_person") or target.get("contact_person"),
            email=enriched.get("email") or target.get("email"),
            phone=enriched.get("phone") or target.get("phone")
        )
        
    return {
        "status": "success",
        "lead_id": lead_id,
        "company_name": target["name"],
        "contact_person": enriched.get("contact_person") or target.get("contact_person", ""),
        "email": enriched.get("email") or target.get("email", ""),
        "phone": enriched.get("phone") or target.get("phone", "")
    }

@mcp.tool()
def configure_titan_mail(email_user: str, email_password: str, host: str = "smtp.titan.email", 
                        port: int = 465, sender_name: str = "Chemkonnect Global Sales Desk") -> Dict[str, Any]:
    """
    Saves and verifies Titan Mail (GoDaddy) credentials for automated direct B2B quote dispatching.
    """
    test_res = mailer.test_connection(user=email_user, password=email_password, host=host, port=port)
    if not test_res.get("success"):
        return {
            "status": "error",
            "message": f"Connection test failed: {test_res.get('error')}",
            "details": test_res
        }
    
    mailer.save_credentials(user=email_user, password=email_password, host=host, port=port, sender_name=sender_name)
    return {
        "status": "success",
        "message": f"Titan Mail credentials for '{email_user}' verified and saved successfully.",
        "sender_email": email_user
    }

@mcp.tool()
def send_titan_pitch_email(lead_id: int, custom_subject: Optional[str] = None, 
                           custom_body: Optional[str] = None) -> Dict[str, Any]:
    """
    Sends a personalized B2B quotation and distributor pitch directly to a lead's verified corporate email
    using the authenticated GoDaddy Titan Mail account. Automatically marks lead status as 'Pitched' and
    records the full audit trail in the outreach_history database table.
    """
    leads = lm.get_leads(limit=2000)
    target = next((l for l in leads if l["id"] == lead_id), None)
    if not target:
        return {"status": "error", "message": f"Lead #{lead_id} not found."}
    
    recipient_email = (target.get("email") or "").strip()
    if not recipient_email or "@" not in recipient_email:
        return {"status": "error", "message": f"Lead #{lead_id} ({target['name']}) has no valid email address."}
    
    recipient_name = target.get("contact_person") or target.get("name") or "Valued Partner"
    
    if custom_subject and custom_body:
        subject = custom_subject.strip()
        body = custom_body.strip()
    else:
        pitch_dict = pitcher.generate_email_pitch(target)
        subject = pitch_dict.get("subject", "Wholesale Supply Proposal - Chemkonnect Global")
        body = pitch_dict.get("body", "")
    
    dispatch_res = mailer.send_pitch_email(
        to_email=recipient_email,
        subject=subject,
        body_text=body,
        recipient_name=recipient_name,
        lead_id=lead_id
    )
    sender_email = dispatch_res.get("sender_email") or mailer.get_credentials().get("user") or ""
    
    if dispatch_res.get("success"):
        outreach_id = lm.record_outreach(
            lead_id=lead_id,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            sender_email=sender_email,
            subject=subject,
            body=body,
            status="Sent"
        )
        return {
            "status": "success",
            "message": f"Pitch successfully delivered to {recipient_email} via Titan Mail.",
            "outreach_id": outreach_id,
            "lead_id": lead_id,
            "lead_name": target["name"],
            "lead_status": "Pitched",
            "subject": subject
        }
    else:
        err = dispatch_res.get("error", "SMTP delivery failure")
        lm.record_outreach(
            lead_id=lead_id,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            sender_email=sender_email,
            subject=subject,
            body=body,
            status="Failed",
            error_message=err
        )
        return {
            "status": "error",
            "message": f"Failed to dispatch email: {err}",
            "lead_id": lead_id
        }

@mcp.tool()
def auto_pitch_all_new_leads(limit: int = 10) -> Dict[str, Any]:
    """
    Scans the database for un-contacted 'New' leads with verified emails, generates personalized
    pitches, dispatches them via Titan Mail, updates lead statuses to 'Pitched', and saves audit logs.
    """
    leads = lm.get_leads(status="New", limit=500)
    eligible = [l for l in leads if l.get("email") and "@" in l["email"] and not l["email"].endswith("@example.com")]
    targets = eligible[:limit]
    
    if not targets:
        return {"status": "success", "message": "No new un-contacted leads with verified emails found.", "sent_count": 0}
        
    sent_count = 0
    failed_count = 0
    results = []
    
    for lead in targets:
        lead_id = lead["id"]
        recipient_email = lead["email"].strip()
        recipient_name = lead.get("contact_person") or lead.get("name") or "Valued Partner"
        pitch_dict = pitcher.generate_email_pitch(lead)
        subject = pitch_dict.get("subject", "Wholesale Supply Proposal - Chemkonnect Global")
        body = pitch_dict.get("body", "")
        
        dispatch_res = mailer.send_pitch_email(
            to_email=recipient_email,
            subject=subject,
            body_text=body,
            recipient_name=recipient_name,
            lead_id=lead_id
        )
        sender_email = dispatch_res.get("sender_email") or mailer.get_credentials().get("user") or ""
        
        if dispatch_res.get("success"):
            lm.record_outreach(
                lead_id=lead_id,
                recipient_name=recipient_name,
                recipient_email=recipient_email,
                sender_email=sender_email,
                subject=subject,
                body=body,
                status="Sent"
            )
            sent_count += 1
            results.append({"lead_id": lead_id, "name": lead["name"], "email": recipient_email, "status": "Sent"})
        else:
            lm.record_outreach(
                lead_id=lead_id,
                recipient_name=recipient_name,
                recipient_email=recipient_email,
                sender_email=sender_email,
                subject=subject,
                body=body,
                status="Failed",
                error_message=dispatch_res.get("error", "")
            )
            failed_count += 1
            results.append({"lead_id": lead_id, "name": lead["name"], "email": recipient_email, "status": "Failed"})
            
    return {
        "status": "success",
        "total_targeted": len(targets),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "results": results
    }

@mcp.tool()
def get_lead_outreach_history(lead_id: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
    """
    Retrieves the persistent outreach audit history of sent pitches, delivery statuses, and timestamps.
    """
    history = lm.get_outreach_history(lead_id=lead_id, limit=limit)
    return {
        "status": "success",
        "total_records": len(history),
        "history": history
    }

if __name__ == "__main__":
    mcp.run()