# Upgrade src/lead_manager.py to support Deal Tiering and Revenue Pipeline Value
import sqlite3
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")))

if IS_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        IS_POSTGRES = False

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "leads.db")
SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seed_leads.json")

def get_connection(db_path: str = DB_PATH):
    if IS_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_cursor(conn):
    if IS_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()

def q_ph() -> str:
    return "%s" if IS_POSTGRES else "?"

def init_db(db_path: str = DB_PATH):
    with get_connection(db_path) as conn:
        cursor = get_cursor(conn)
        if IS_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    city TEXT DEFAULT 'Thane',
                    area TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    source TEXT DEFAULT 'Scraper',
                    status TEXT DEFAULT 'New',
                    pitch_draft TEXT,
                    deal_tier TEXT DEFAULT 'Tier C - Recurring',
                    estimated_deal_value BIGINT DEFAULT 50000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, phone)
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    city TEXT DEFAULT 'Thane',
                    area TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    source TEXT DEFAULT 'Scraper',
                    status TEXT DEFAULT 'New',
                    pitch_draft TEXT,
                    deal_tier TEXT DEFAULT 'Tier C - Recurring',
                    estimated_deal_value INTEGER DEFAULT 50000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, phone)
                )
            """)
            # Check if columns exist in case table was created earlier
            cursor.execute("PRAGMA table_info(leads)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "deal_tier" not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN deal_tier TEXT DEFAULT 'Tier C - Recurring'")
            if "estimated_deal_value" not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN estimated_deal_value INTEGER DEFAULT 50000")
        conn.commit()

class LeadManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)
        self.auto_seed_if_empty()

    def auto_seed_if_empty(self):
        try:
            stats = self.get_stats()
            if stats["total_leads"] == 0 and os.path.exists(SEED_PATH):
                with open(SEED_PATH, "r", encoding="utf-8") as f:
                    seeds = json.load(f)
                count = 0
                for s in seeds:
                    res = self.add_lead(
                        name=s.get("name", ""),
                        category=s.get("category", ""),
                        city=s.get("city", "Mumbai"),
                        area=s.get("area", ""),
                        phone=s.get("phone", ""),
                        email=s.get("email", ""),
                        address=s.get("address", ""),
                        source=s.get("source", "Seed"),
                        deal_tier=s.get("deal_tier"),
                        estimated_value=s.get("estimated_deal_value")
                    )
                    if res:
                        count += 1
                        if s.get("pitch_draft"):
                            self.update_lead(res, status=s.get("status", "Pitched"), pitch_draft=s.get("pitch_draft"))
                print(f"[✔] Seeded {count} initial enterprise accounts into pipeline.")
        except Exception as e:
            print(f"[!] Seed notice: {e}")

    def calculate_deal_tier(self, category: str, query_text: str = "") -> tuple[str, int]:
        """
        Calculates deal tier and estimated value for ₹100 Crore pipeline targets:
        - Tier A (Mega Accounts > ₹10 Lakhs): Bulk Chemicals, Solvents, Tankers, JSW Expansion Joints, Structural TMT
        - Tier B (Commercial Projects ₹2L - ₹10L): Gypsum Plasterboard Projects, Plywood Truckloads, Dr Fixit Fastflex
        - Tier C (Recurring Flow < ₹2L): Fevicol Retail, Carpentry Packs, Routine Maintenance
        """
        combined = f"{category} {query_text}".lower()
        if any(k in combined for k in ["solvent", "acetone", "toluene", "tanker", "drum", "chemical", "jsw", "expansion joint", "tmt", "rebar", "infrastructure", "tender"]):
            return "Tier A - Mega Account", 1500000  # Avg 15 Lakhs
        elif any(k in combined for k in ["gypsum", "plasterboard", "false ceiling", "plywood", "bwp", "marine ply", "fitout", "commercial interior", "fastflex"]):
            return "Tier B - Commercial Project", 500000  # Avg 5 Lakhs
        return "Tier C - Recurring Flow", 75000  # Avg 75k

    def add_lead(self, name: str, category: str, city: str = "Thane", 
                 area: str = "", phone: str = "", email: str = "", 
                 address: str = "", source: str = "Scraper",
                 deal_tier: Optional[str] = None, estimated_value: Optional[int] = None) -> Optional[int]:
        
        tier, val = self.calculate_deal_tier(category, address)
        final_tier = deal_tier or tier
        final_val = estimated_value if estimated_value is not None else val
        p = q_ph()

        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            try:
                if IS_POSTGRES:
                    cursor.execute(f"""
                        INSERT INTO leads (name, category, city, area, phone, email, address, source, deal_tier, estimated_deal_value)
                        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                        ON CONFLICT (name, phone) DO NOTHING
                        RETURNING id
                    """, (name.strip(), category.strip(), city.strip(), area.strip(), phone.strip(), email.strip(), address.strip(), source, final_tier, final_val))
                    row = cursor.fetchone()
                    conn.commit()
                    return row["id"] if row else None
                else:
                    cursor.execute(f"""
                        INSERT INTO leads (name, category, city, area, phone, email, address, source, deal_tier, estimated_deal_value)
                        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                    """, (name.strip(), category.strip(), city.strip(), area.strip(), phone.strip(), email.strip(), address.strip(), source, final_tier, final_val))
                    conn.commit()
                    return cursor.lastrowid
            except Exception:
                return None

    def get_leads(self, category: Optional[str] = None, status: Optional[str] = None, deal_tier: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        p = q_ph()
        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            query = "SELECT * FROM leads WHERE 1=1"
            params = []
            if category:
                query += f" AND category LIKE {p}"
                params.append(f"%{category}%")
            if status:
                query += f" AND status = {p}"
                params.append(status)
            if deal_tier:
                query += f" AND deal_tier LIKE {p}"
                params.append(f"%{deal_tier}%")
            query += f" ORDER BY estimated_deal_value DESC, id DESC LIMIT {p}"
            params.append(limit)
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_lead(self, lead_id: int, status: Optional[str] = None, pitch_draft: Optional[str] = None, deal_tier: Optional[str] = None, estimated_value: Optional[int] = None) -> bool:
        p = q_ph()
        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            updates = []
            params = []
            if status:
                updates.append(f"status = {p}")
                params.append(status)
            if pitch_draft is not None:
                updates.append(f"pitch_draft = {p}")
                params.append(pitch_draft)
            if deal_tier is not None:
                updates.append(f"deal_tier = {p}")
                params.append(deal_tier)
            if estimated_value is not None:
                updates.append(f"estimated_deal_value = {p}")
                params.append(estimated_value)
            if not updates:
                return False
            updates.append(f"updated_at = {p}")
            params.append(datetime.now().isoformat())
            params.append(lead_id)
            sep = ", "
            query = f"UPDATE leads SET {sep.join(updates)} WHERE id = {p}"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def export_to_csv(self, output_path: Optional[str] = None) -> str:
        if not output_path:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"chemkonnect_leads_{timestamp}.csv")

        leads = self.get_leads(limit=2000)
        if not leads:
            fieldnames = ["id", "name", "category", "city", "area", "phone", "email", "address", "source", "status", "deal_tier", "estimated_deal_value", "pitch_draft", "created_at", "updated_at"]
        else:
            fieldnames = list(leads[0].keys())

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)

        return output_path

    def get_stats(self) -> Dict[str, Any]:
        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            cursor.execute("SELECT count(*) FROM leads")
            res_total = cursor.fetchone()
            total = res_total[0] if not IS_POSTGRES else list(res_total.values())[0]
            
            cursor.execute("SELECT sum(estimated_deal_value) FROM leads")
            res_sum = cursor.fetchone()
            sum_val = (res_sum[0] if not IS_POSTGRES else list(res_sum.values())[0]) or 0
            
            cursor.execute("SELECT deal_tier, count(*), sum(estimated_deal_value) FROM leads GROUP BY deal_tier")
            rows = cursor.fetchall()
            by_tier = {}
            for r in rows:
                if IS_POSTGRES:
                    vals = list(r.values())
                    by_tier[vals[0]] = {"count": vals[1], "value": vals[2]}
                else:
                    by_tier[r[0]] = {"count": r[1], "value": r[2]}

            cursor.execute("SELECT status, count(*) FROM leads GROUP BY status")
            s_rows = cursor.fetchall()
            by_status = {}
            for r in s_rows:
                if IS_POSTGRES:
                    vals = list(r.values())
                    by_status[vals[0]] = vals[1]
                else:
                    by_status[r[0]] = r[1]

            # Convert pipeline to Crores
            pipeline_crores = round(sum_val / 10000000.0, 2)
            pct_of_100_cr = round((sum_val / 1000000000.0) * 100, 2)

            return {
                "total_leads": total,
                "pipeline_value_inr": sum_val,
                "pipeline_value_crores": pipeline_crores,
                "percent_of_100cr_goal": pct_of_100_cr,
                "by_tier": by_tier,
                "by_status": by_status
            }

if __name__ == "__main__":
    lm = LeadManager()
    print("Chemkonnect Sales Engine Database initialized. Current Stats:")
    print(lm.get_stats())