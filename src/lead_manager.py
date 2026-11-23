# Upgrade src/lead_manager.py to support Deal Tiering and Revenue Pipeline Value
import sqlite3
import csv
import os
import json
from contextlib import contextmanager
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

@contextmanager
def get_connection(db_path: str = DB_PATH):
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        try:
            yield conn
        finally:
            conn.close()
    else:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

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
                    contact_person TEXT DEFAULT '',
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
            try:
                cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS contact_person TEXT DEFAULT '';")
            except Exception:
                pass
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    contact_person TEXT DEFAULT '',
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
            if "contact_person" not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN contact_person TEXT DEFAULT ''")
            if "deal_tier" not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN deal_tier TEXT DEFAULT 'Tier C - Recurring'")
            if "estimated_deal_value" not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN estimated_deal_value INTEGER DEFAULT 50000")
        
        # Reset any previously pitched or unassigned leads to 'New' as requested
        try:
            cursor.execute("UPDATE leads SET status = 'New' WHERE status = 'Pitched' OR status IS NULL OR status = ''")
            # Purge fake generic generated emails
            cursor.execute("""
                UPDATE leads 
                SET email = '' 
                WHERE email LIKE 'procurement.%@gmail.com' 
                   OR email LIKE 'rfq.%@gmail.com' 
                   OR email = 'N/A' 
                   OR email = 'sales.desk@chemkonnect.com'
            """)
            # Purge non-business search scrapings that lack real contact info
            cursor.execute("""
                DELETE FROM leads 
                WHERE (phone IS NULL OR phone = '' OR phone LIKE '%Found via%')
                  AND (email IS NULL OR email = '' OR email = 'N/A')
                  AND (source IS NULL OR source = '' OR source NOT LIKE 'http%')
            """)
            cursor.execute("""
                DELETE FROM leads 
                WHERE LOWER(name) LIKE '%español%' 
                   OR LOWER(name) LIKE '%espanol%'
                   OR LOWER(name) LIKE '%wikipedia%'
                   OR LOWER(name) LIKE '%definition%'
                   OR LOWER(name) LIKE '%merriam%'
                   OR LOWER(name) LIKE '%dictionary%'
                   OR LOWER(name) LIKE '%microsoft support%'
                   OR LOWER(name) LIKE '%microsoft account%'
                   OR LOWER(name) LIKE '%explore types%'
                   OR LOWER(name) LIKE '%what is plywood%'
            """)
        except Exception:
            pass
        conn.commit()

class LeadManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.is_postgres = IS_POSTGRES
        init_db(self.db_path)
        self.auto_seed_if_empty()

    def auto_seed_if_empty(self):
        try:
            stats = self.get_stats()
            if stats["total_leads"] == 0 and os.path.exists(SEED_PATH):
                with open(SEED_PATH, "r", encoding="utf-8") as f:
                    seeds = json.load(f)
                count = 0
                p = q_ph()
                with get_connection(self.db_path) as conn:
                    cursor = get_cursor(conn)
                    for s in seeds:
                        tier, val = self.calculate_deal_tier(s.get("category", ""), s.get("address", ""))
                        final_tier = s.get("deal_tier") or tier
                        final_val = s.get("estimated_deal_value") if s.get("estimated_deal_value") is not None else val
                        try:
                            if IS_POSTGRES:
                                cursor.execute(f"""
                                    INSERT INTO leads (name, category, city, area, phone, email, address, source, status, pitch_draft, deal_tier, estimated_deal_value)
                                    VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                                    ON CONFLICT (name, phone) DO NOTHING
                                """, (
                                    s.get("name", "").strip(), s.get("category", "").strip(),
                                    s.get("city", "Mumbai").strip(), s.get("area", "").strip(),
                                    s.get("phone", "").strip(), s.get("email", "").strip(),
                                    s.get("address", "").strip(), s.get("source", "Seed"),
                                    "New", s.get("pitch_draft", ""),
                                    final_tier, final_val
                                ))
                            else:
                                cursor.execute(f"""
                                    INSERT INTO leads (name, category, city, area, phone, email, address, source, status, pitch_draft, deal_tier, estimated_deal_value)
                                    VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                                """, (
                                    s.get("name", "").strip(), s.get("category", "").strip(),
                                    s.get("city", "Mumbai").strip(), s.get("area", "").strip(),
                                    s.get("phone", "").strip(), s.get("email", "").strip(),
                                    s.get("address", "").strip(), s.get("source", "Seed"),
                                    "New", s.get("pitch_draft", ""),
                                    final_tier, final_val
                                ))
                            count += 1
                        except Exception:
                            pass
                    conn.commit()
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
        if any(k in combined for k in ["solvent", "acetone", "toluene", "tanker", "drum", "chemical", "jsw", "expansion joint", "tmt", "rebar", "infrastructure", "tender", "dyson", "airblade", "hand dryer", "air purifier"]):
            return "Tier A - Mega Account", 1500000  # Avg 15 Lakhs
        elif any(k in combined for k in ["gypsum", "plasterboard", "false ceiling", "plywood", "bwp", "marine ply", "fitout", "commercial interior", "fastflex", "pidilite", "fevicol", "dr fixit", "waterproofing"]):
            return "Tier B - Commercial Project", 500000  # Avg 5 Lakhs
        return "Tier C - Recurring Flow", 75000  # Avg 75k

    def add_lead(self, name: str, category: str, city: str = "Thane", 
                 area: str = "", phone: str = "", email: str = "", 
                 address: str = "", source: str = "Scraper",
                 deal_tier: Optional[str] = None, estimated_value: Optional[int] = None,
                 contact_person: str = "") -> Optional[int]:
        
        name_clean = name.strip()
        name_lower = name_clean.lower()
        # Strict quality filter: discard non-business entries
        if any(junk in name_lower for junk in [
            "wikipedia", "dictionary", "merriam", "definition", "meaning",
            "español", "espanol", "microsoft support", "microsoft account",
            "explore types", "what is ", "best 10", "top 10"
        ]):
            return None

        phone_clean = phone.strip()
        email_clean = email.strip()
        contact_person_clean = contact_person.strip()
        source_clean = source.strip()

        # Discard fabricated generic emails
        if email_clean.startswith("procurement.") and email_clean.endswith("@gmail.com"):
            email_clean = ""
        if email_clean.startswith("rfq.") and email_clean.endswith("@gmail.com"):
            email_clean = ""
        if email_clean == "sales.desk@chemkonnect.com":
            email_clean = ""

        # Must have at least one viable contact: phone, email, or a real website URL
        if not phone_clean and not email_clean and not source_clean.startswith("http"):
            return None

        tier, val = self.calculate_deal_tier(category, address)
        final_tier = deal_tier or tier
        final_val = estimated_value if estimated_value is not None else val
        p = q_ph()

        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            try:
                if IS_POSTGRES:
                    cursor.execute(f"""
                        INSERT INTO leads (name, contact_person, category, city, area, phone, email, address, source, status, deal_tier, estimated_deal_value)
                        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'New', {p}, {p})
                        ON CONFLICT (name, phone) DO UPDATE SET
                            contact_person = CASE WHEN EXCLUDED.contact_person != '' THEN EXCLUDED.contact_person ELSE leads.contact_person END,
                            email = CASE WHEN EXCLUDED.email != '' THEN EXCLUDED.email ELSE leads.email END
                        RETURNING id
                    """, (name_clean, contact_person_clean, category.strip(), city.strip(), area.strip(), phone_clean, email_clean, address.strip(), source_clean, final_tier, final_val))
                    row = cursor.fetchone()
                    conn.commit()
                    return row["id"] if row else None
                else:
                    cursor.execute(f"""
                        INSERT INTO leads (name, contact_person, category, city, area, phone, email, address, source, status, deal_tier, estimated_deal_value)
                        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'New', {p}, {p})
                    """, (name_clean, contact_person_clean, category.strip(), city.strip(), area.strip(), phone_clean, email_clean, address.strip(), source_clean, final_tier, final_val))
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
            query += f" ORDER BY id DESC, created_at DESC LIMIT {p}"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("estimated_deal_value") is not None:
                    d["estimated_deal_value"] = int(d["estimated_deal_value"])
                if d.get("created_at") is not None:
                    d["created_at"] = str(d["created_at"])
                if d.get("updated_at") is not None:
                    d["updated_at"] = str(d["updated_at"])
                if "contact_person" not in d or d["contact_person"] is None:
                    d["contact_person"] = ""
                result.append(d)
            return result

    def update_lead(self, lead_id: int, status: Optional[str] = None, pitch_draft: Optional[str] = None, 
                    deal_tier: Optional[str] = None, estimated_value: Optional[int] = None,
                    contact_person: Optional[str] = None, email: Optional[str] = None, phone: Optional[str] = None) -> bool:
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
            if contact_person is not None:
                updates.append(f"contact_person = {p}")
                params.append(contact_person.strip())
            if email is not None:
                updates.append(f"email = {p}")
                params.append(email.strip())
            if phone is not None:
                updates.append(f"phone = {p}")
                params.append(phone.strip())
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
            fieldnames = ["id", "name", "contact_person", "category", "city", "area", "phone", "email", "address", "source", "status", "deal_tier", "estimated_deal_value", "pitch_draft", "created_at", "updated_at"]
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
            if not res_total:
                total = 0
            elif isinstance(res_total, dict):
                total = int(list(res_total.values())[0] or 0)
            else:
                total = int(res_total[0] or 0)
            
            cursor.execute("SELECT sum(estimated_deal_value) FROM leads")
            res_sum = cursor.fetchone()
            if not res_sum:
                sum_val = 0.0
            elif isinstance(res_sum, dict):
                raw = list(res_sum.values())[0]
                sum_val = float(raw) if raw is not None else 0.0
            else:
                sum_val = float(res_sum[0]) if res_sum[0] is not None else 0.0
            
            cursor.execute("SELECT deal_tier, count(*), sum(estimated_deal_value) FROM leads GROUP BY deal_tier")
            rows = cursor.fetchall()
            by_tier = {}
            for r in rows:
                if isinstance(r, dict):
                    vals = list(r.values())
                    by_tier[vals[0] or "Unknown"] = {"count": int(vals[1] or 0), "value": float(vals[2] or 0)}
                else:
                    by_tier[r[0] or "Unknown"] = {"count": int(r[1] or 0), "value": float(r[2] or 0)}

            cursor.execute("SELECT status, count(*) FROM leads GROUP BY status")
            s_rows = cursor.fetchall()
            by_status = {}
            for r in s_rows:
                if isinstance(r, dict):
                    vals = list(r.values())
                    by_status[vals[0] or "Unknown"] = int(vals[1] or 0)
                else:
                    by_status[r[0] or "Unknown"] = int(r[1] or 0)

            # Convert pipeline to Crores
            pipeline_crores = round(float(sum_val) / 10000000.0, 2)
            pct_of_100_cr = round((float(sum_val) / 1000000000.0) * 100, 2)

            return {
                "total_leads": total,
                "pipeline_value_inr": int(sum_val),
                "pipeline_value_crores": pipeline_crores,
                "percent_of_100cr_goal": pct_of_100_cr,
                "by_tier": by_tier,
                "by_status": by_status
            }

if __name__ == "__main__":
    lm = LeadManager()
    print("Chemkonnect Sales Engine Database initialized. Current Stats:")
    print(lm.get_stats())