# src/chemkonnect_mcp.py
"""
Chemkonnect Global - ₹100 Crore Sales MCP Server
Connects Antigravity AI agents to:
- Real Estate Projects Nearing Possession (99acres, MagicBricks, NoBroker, MahaRERA)
- Turnkey Commercial Interior Giants (Ashish Interbuild, Astitva Interiors, Cherry Hill)
- 30-Day Multi-platform Lead Harvester (IndiaMART, TradeIndia, Open Web, Tenders)
- Deal Tiering & Revenue Pipeline Valuation (Tier A Mega accounts, Tier B Commercial projects)
- Automated Quotations & WhatsApp Pitches for:
  Pidilite, Gypsum, Plywood, JSW Expansion Joints, and Industrial Bulk Solvents.
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

mcp = FastMCP("Chemkonnect Sales Engine")
lm = LeadManager()
scraper = B2BLeadScraper(lead_manager=lm)
pitcher = PitchGenerator(lead_manager=lm)
indiamart = IndiaMartLeadPuller()
harvester = RecentWebLeadHarvester(lead_manager=lm)
tradeindia = TradeIndiaScraper(lead_manager=lm)
project_harvester = ProjectAndContractorHarvester(lead_manager=lm)

@mcp.tool()
def get_product_catalog(category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get Chemkonnect Global's complete product catalog.
    Available categories:
    - pidilite_adhesives (Fevicol SH, Marine, HeatX, ProBond)
    - construction_chemicals (Dr. Fixit LW+, Fastflex, Raincoat)
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
def pull_indiamart_rfqs(days_back: int = 30) -> Dict[str, Any]:
    """
    Pulls buyer inquiries from IndiaMART Lead Manager API across a 30-day (1 Month) rolling window.
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
    indiamart.process_and_save_leads(days_back=30)
    stats = lm.get_stats()
    return {
        "status": "success",
        "region_scanned": region,
        "total_leads_in_cloud_db": stats["total_leads"],
        "pipeline_value_crores": stats["pipeline_value_crores"],
        "percent_of_100cr_goal": stats["percent_of_100cr_goal"],
        "pipeline_breakdown": stats
    }

if __name__ == "__main__":
    mcp.run()