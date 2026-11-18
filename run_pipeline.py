# run_pipeline.py
"""
Chemkonnect Global - ₹100 Crore B2B AI Sales Engine CLI Runner
Usage:
  uv run python run_pipeline.py
  uv run python run_pipeline.py --projects
  uv run python run_pipeline.py --giants
  uv run python run_pipeline.py --indiamart
  uv run python run_pipeline.py --tradeindia
  uv run python run_pipeline.py --export
"""
import sys
import os
import argparse

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lead_manager import LeadManager
from scraper import B2BLeadScraper
from pitch_generator import PitchGenerator
from indiamart_lead_puller import IndiaMartLeadPuller
from recent_web_leads import RecentWebLeadHarvester
from tradeindia_scraper import TradeIndiaScraper
from project_and_contractor_harvester import ProjectAndContractorHarvester

def print_banner():
    print("=" * 75)
    print("   CHEMKONNECT GLOBAL - ₹100 CRORE B2B AI SALES ENGINE")
    print("   Pidilite | Gypsum Boards | Plywood | Expansion Joints | Solvents")
    print("   Nearing-Possession Projects (99acres) & Commercial Interior Giants")
    print("=" * 75)

def main():
    parser = argparse.ArgumentParser(description="Chemkonnect ₹100 Cr Sales Engine")
    parser.add_argument("--projects", action="store_true", help="Harvest nearing-possession projects from 99acres/MagicBricks/NoBroker")
    parser.add_argument("--giants", action="store_true", help="Harvest turnkey interior giants (Ashish Interbuild, Astitva, etc.)")
    parser.add_argument("--indiamart", action="store_true", help="Fetch 30-day IndiaMART RFQ buyer inquiries")
    parser.add_argument("--tradeindia", action="store_true", help="Harvest verified TradeIndia enterprise accounts")
    parser.add_argument("--recent", action="store_true", help="Harvest fresh internet leads active in recent time window")
    parser.add_argument("--category", type=str, default="Gypsum board", help="Product keyword")
    parser.add_argument("--location", type=str, default="Mumbai", help="Target city")
    parser.add_argument("--pitch-all", action="store_true", help="Generate pitches for all unpitched leads")
    parser.add_argument("--export", action="store_true", help="Export pipeline to CSV file")

    args = parser.parse_args()
    print_banner()

    lm = LeadManager()
    scraper = B2BLeadScraper(lead_manager=lm)
    pitcher = PitchGenerator(lead_manager=lm)
    indiamart = IndiaMartLeadPuller()
    harvester = RecentWebLeadHarvester(lead_manager=lm)
    tradeindia = TradeIndiaScraper(lead_manager=lm)
    project_harvester = ProjectAndContractorHarvester(lead_manager=lm)

    scraper.seed_initial_leads()

    if args.projects:
        print("\n[*] Ingesting Nearing-Possession Projects (99acres / MagicBricks / NoBroker)...")
        project_harvester.harvest_nearing_possession_projects()

    if args.giants:
        print("\n[*] Ingesting Turnkey Commercial Interior Giants & Sub-Contractors...")
        project_harvester.harvest_commercial_interior_giants()

    if args.indiamart:
        print("\n[*] Processing IndiaMART RFQs across 30-Day window...")
        indiamart.process_and_save_leads(days_back=30)

    if args.tradeindia:
        print("\n[*] Ingesting TradeIndia verified industrial accounts...")
        tradeindia.harvest_directory()

    if args.recent:
        print(f"\n[*] Scanning the internet for '{args.category}' in '{args.location}'...")
        harvester.find_fresh_leads(product_keyword=args.category, location=args.location)

    if args.pitch_all:
        leads = lm.get_leads(status="New", limit=50)
        print(f"\n[*] Generating Pitches for {len(leads)} unpitched leads...")
        for lead in leads:
            res = pitcher.generate_pitch_for_lead(lead['id'])
            print(f"  [✔] Pitch created for #{lead['id']}: {lead['name']} ({lead['category']})")

    # Display ₹100 Crore Pipeline Summary
    stats = lm.get_stats()
    print("\n" + "=" * 75)
    print("   🏆 ₹100 CRORE ANNUAL PIPELINE PROGRESS REPORT")
    print("=" * 75)
    print(f"Total Leads in Pipeline   : {stats['total_leads']} Accounts")
    print(f"Total Identified Value    : ₹{stats['pipeline_value_crores']} Crores ({stats['percent_of_100cr_goal']}% of ₹100 Cr Goal)")
    print("\nBreakdown by Deal Tier    :")
    for tier, data in stats['by_tier'].items():
        val_cr = round(data['value'] / 10000000.0, 2)
        print(f"  • {tier:27}: {data['count']:2} leads | ₹{val_cr:5.2f} Cr")
    
    print("\nBreakdown by Status       :")
    for status, count in stats['by_status'].items():
        print(f"  • {status:15}: {count} leads")

    csv_file = lm.export_to_csv()
    print(f"\n[✔] Live Pipeline CSV exported to:\n    {csv_file}")
    print("=" * 75)

if __name__ == "__main__":
    main()