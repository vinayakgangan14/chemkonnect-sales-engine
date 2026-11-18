# Chemkonnect Global - B2B AI Sales Automation Engine

A 100% free, local AI sales automation system and custom Model Context Protocol (MCP) server built for **Chemkonnect Global** (`chemkonnect.com`).

Built specifically for:
- **Authorized Pidilite & Fevicol Woodworking Adhesives** (Fevicol SH, Marine, HeatX, ProBond)
- **Pidilite Construction Chemicals & Waterproofing** (Dr. Fixit LW+, Fastflex, Raincoat)
- **Gypsum Boards, Channels & False Ceiling Systems**
- **JSW Expansion Joints & TMT Steel Rods**
- **Industrial Solvents & Chemicals** (Acetone, IPA, Toluene, Ethyl Acetate)

---

## Architecture Overview

```
chemkonnect-sales-engine/
├── data/
│   ├── products.json           # Live catalog of Chemkonnect product lines & pack sizes
│   └── leads.db                # Local SQLite pipeline database (auto-created)
├── src/
│   ├── lead_manager.py         # SQLite database CRUD operations & CSV exporter
│   ├── scraper.py              # Zero-cost B2B lead scraper for MMR (Thane/Dombivli/Mumbai)
│   ├── pitch_generator.py      # Automated WhatsApp & Email personalized pitch builder
│   └── chemkonnect_mcp.py      # Model Context Protocol (MCP) server for Antigravity
├── output/                     # Auto-exported CSV lead lists ready for WhatsApp & Excel
├── run_pipeline.py             # CLI runner for quick terminal execution
├── register_mcp.py             # Registers MCP server in ~/.gemini/config/mcp_config.json
└── README.md
```

---

## Quickstart (Zero-Cost Terminal Commands)

Run commands from this project directory using `uv run python`:

### 1. View Current Pipeline & Export CSV
```powershell
uv run python run_pipeline.py
```

### 2. Search for New Leads
Search for contractors, interior designers, or factories in any Maharashtra location:
```powershell
# Search for Interior Designers in Thane:
uv run python run_pipeline.py --category "Interior Designer" --location "Thane"

# Search for Civil Contractors in Dombivli:
uv run python run_pipeline.py --category "Civil Contractor" --location "Dombivli"

# Search for Paint or Chemical Manufacturers in MIDC:
uv run python run_pipeline.py --category "Paint Manufacturer" --location "Dombivli MIDC"
```

### 3. Generate Pitches for All Unpitched Leads
```powershell
uv run python run_pipeline.py --pitch-all
```

---

## Using via Antigravity MCP Server

The server is registered in `~/.gemini/config/mcp_config.json` under `chemkonnect-sales`.

Once Antigravity reloads or boots, you can prompt your agent in natural language:
- *"Show me our current Chemkonnect leads in the database."*
- *"Find 5 new gypsum false ceiling contractors in Thane and prepare WhatsApp intro messages."*
- *"Export our sales pipeline to CSV."*

The agent will call the MCP tools (`list_pipeline_leads`, `search_and_save_leads`, `generate_pitch_for_lead`, `export_leads_to_csv`) automatically!

---

## Leads & Output Files
- Database: `data/leads.db` (SQLite)
- CSV Output: `output/chemkonnect_leads_*.csv` (Opens in Excel with formatted phone numbers and full WhatsApp pitches).