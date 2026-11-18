# src/portal.py
"""
Chemkonnect Global - ₹100 Crore B2B AI Sales Portal & Cloud MCP Server
Runs locally at http://127.0.0.1:5000 and is deployable to Render / Cloud.
Exposes both:
  - Web Dashboard UI at /
  - Remote MCP SSE Server at /mcp/sse
"""
import sys
import os
import json
import urllib.parse
from typing import Optional, List, Dict, Any

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from lead_manager import LeadManager
from pitch_generator import PitchGenerator
from recent_web_leads import RecentWebLeadHarvester
from indiamart_lead_puller import IndiaMartLeadPuller
from tradeindia_scraper import TradeIndiaScraper
from project_and_contractor_harvester import ProjectAndContractorHarvester
from chemkonnect_mcp import mcp

app = FastAPI(title="Chemkonnect Global ₹100 Crore Sales Portal & Cloud MCP")
lm = LeadManager()
pitcher = PitchGenerator(lead_manager=lm)
harvester = RecentWebLeadHarvester(lead_manager=lm)
indiamart = IndiaMartLeadPuller()
tradeindia = TradeIndiaScraper(lead_manager=lm)
project_harvester = ProjectAndContractorHarvester(lead_manager=lm)

# Mount Remote Cloud MCP (SSE Transport) at /mcp
try:
    mcp_sub = mcp.http_app(transport="sse")
    app.mount("/mcp", mcp_sub)
    print("[✔] Remote MCP SSE mounted at: /mcp/sse")
except Exception as e:
    print(f"[!] Notice: MCP SSE mount: {e}")

class HarvestRequest(BaseModel):
    category: str = "Gypsum board"
    location: str = "Mumbai"
    timelimit: str = "w"

class StatusUpdateRequest(BaseModel):
    status: str

@app.get("/api/leads")
def get_leads(category: Optional[str] = None, status: Optional[str] = None, tier: Optional[str] = None, search: Optional[str] = None):
    leads = lm.get_leads(category=category, status=status, deal_tier=tier, limit=1000)
    if search:
        s = search.lower()
        leads = [l for l in leads if s in l["name"].lower() or s in l["category"].lower() or s in l["city"].lower() or s in (l["phone"] or "")]
    
    for l in leads:
        loc = f"{l['city']} {l['area'] or ''}"
        l["priority_zone"] = pitcher.classify_region_priority(loc)
        
        pitch_text = l.get("pitch_draft") or ""
        if "--- WHATSAPP PITCH ---" in pitch_text:
            parts = pitch_text.split("--- EMAIL PITCH ---")[0].replace("--- WHATSAPP PITCH ---", "").strip()
        else:
            parts = pitcher.generate_whatsapp_pitch(l)
            
        clean_phone = (l.get("phone") or "").replace("+", "").replace(" ", "").replace("-", "")
        if clean_phone.startswith("0"):
            clean_phone = "91" + clean_phone[1:]
        elif len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        l["whatsapp_text"] = parts
        l["whatsapp_url"] = f"https://api.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote(parts)}" if clean_phone else ""

    stats = lm.get_stats()
    core_count = sum(1 for l in leads if "High Priority" in l["priority_zone"])
    indiamart_count = sum(1 for l in leads if "IndiaMART" in (l.get("source") or ""))
    tradeindia_count = sum(1 for l in leads if "TradeIndia" in (l.get("source") or ""))
    projects_count = sum(1 for l in leads if "MagicBricks" in (l.get("source") or "") or "99acres" in (l.get("source") or "") or "NoBroker" in (l.get("source") or "") or "MahaRERA" in (l.get("source") or ""))
    giants_count = sum(1 for l in leads if "Giant" in (l.get("source") or "") or "Corporate Fitout" in (l.get("source") or ""))

    return {
        "leads": leads,
        "total_count": len(leads),
        "core_belt_count": core_count,
        "indiamart_count": indiamart_count,
        "tradeindia_count": tradeindia_count,
        "projects_count": projects_count,
        "giants_count": giants_count,
        "stats": stats
    }

@app.post("/api/harvest")
def harvest_leads(req: HarvestRequest):
    new_leads = harvester.find_fresh_leads(
        product_keyword=req.category,
        location=req.location,
        timelimit=req.timelimit
    )
    return {
        "status": "success",
        "found_count": len(new_leads),
        "leads": new_leads
    }

@app.post("/api/indiamart")
def fetch_indiamart(days_back: int = 30):
    leads = indiamart.process_and_save_leads(days_back=days_back)
    return {
        "status": "success",
        "processed_count": len(leads),
        "leads": leads
    }

@app.post("/api/tradeindia")
def fetch_tradeindia():
    leads = tradeindia.harvest_directory()
    return {
        "status": "success",
        "processed_count": len(leads),
        "leads": leads
    }

@app.post("/api/projects")
def fetch_projects():
    projects = project_harvester.harvest_nearing_possession_projects()
    return {
        "status": "success",
        "processed_count": len(projects),
        "projects": projects
    }

@app.post("/api/giants")
def fetch_giants():
    giants = project_harvester.harvest_commercial_interior_giants()
    return {
        "status": "success",
        "processed_count": len(giants),
        "giants": giants
    }

@app.post("/api/leads/{lead_id}/status")
def update_status(lead_id: int, req: StatusUpdateRequest):
    success = lm.update_lead(lead_id=lead_id, status=req.status)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "success", "lead_id": lead_id, "new_status": req.status}

@app.get("/api/export")
def export_csv():
    csv_path = lm.export_to_csv()
    return FileResponse(csv_path, media_type="text/csv", filename=os.path.basename(csv_path))

@app.get("/", response_class=HTMLResponse)
def index_page():
    html_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portal_ui.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Chemkonnect Portal UI Loading...</h1>"

if __name__ == "__main__":
    uvicorn.run("portal:app", host="0.0.0.0", port=5000, reload=True)