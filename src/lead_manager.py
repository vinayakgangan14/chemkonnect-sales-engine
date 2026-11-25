# Upgrade src/lead_manager.py to support Deal Tiering and Revenue Pipeline Value
import sqlite3
import csv
import os
import json
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional, Any

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
            DATABASE_URL = os.environ.get("DATABASE_URL")
        except Exception:
            pass

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
                cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_pitched_at TIMESTAMP;")
            except Exception:
                pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outreach_history (
                    id SERIAL PRIMARY KEY,
                    lead_id INTEGER,
                    recipient_name TEXT DEFAULT '',
                    recipient_email TEXT NOT NULL,
                    sender_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT DEFAULT 'Sent',
                    error_message TEXT DEFAULT '',
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_outreach_lead_id ON outreach_history(lead_id);
                CREATE INDEX IF NOT EXISTS idx_outreach_sent_at ON outreach_history(sent_at DESC);
            """)
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
                    last_pitched_at TIMESTAMP,
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
            if "last_pitched_at" not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN last_pitched_at TIMESTAMP")
            if "deal_tier" not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN deal_tier TEXT DEFAULT 'Tier C - Recurring'")
            if "estimated_deal_value" not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN estimated_deal_value INTEGER DEFAULT 50000")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outreach_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER,
                    recipient_name TEXT DEFAULT '',
                    recipient_email TEXT NOT NULL,
                    sender_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT DEFAULT 'Sent',
                    error_message TEXT DEFAULT '',
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_outreach_lead_id ON outreach_history(lead_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_outreach_sent_at ON outreach_history(sent_at DESC)")
        
        # Ensure unassigned leads have status 'New'
        try:
            cursor.execute("UPDATE leads SET status = 'New' WHERE status IS NULL OR status = ''")
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
            # Enforce 7-Day Rolling Window: delete records older than 7 days
            # And purge all synthetic/duplicate inquiry records
            if IS_POSTGRES:
                cursor.execute("""
                    DELETE FROM leads 
                    WHERE created_at < NOW() - INTERVAL '7 days'
                       OR email LIKE 'rfq.%@gmail.com' 
                       OR email LIKE 'procurement.%@gmail.com' 
                       OR name LIKE '%Inquiry #%'
                       OR name LIKE '%(Inquiry%'
                       OR source LIKE '%Pan-India Live RFQ Stream%'
                       OR LOWER(category) LIKE '%solvent%'
                       OR LOWER(category) LIKE '%chemical%'
                       OR LOWER(category) LIKE '%acetone%'
                       OR LOWER(category) LIKE '%toluene%'
                       OR LOWER(category) LIKE '%paint%'
                       OR LOWER(category) LIKE '%resin%'
                       OR LOWER(category) LIKE '%pharma%'
                       OR LOWER(category) LIKE '%intermediate%';
                """)
            else:
                cursor.execute("""
                    DELETE FROM leads 
                    WHERE created_at < datetime('now', '-7 days')
                       OR email LIKE 'rfq.%@gmail.com' 
                       OR email LIKE 'procurement.%@gmail.com' 
                       OR name LIKE '%Inquiry #%'
                       OR name LIKE '%(Inquiry%'
                       OR source LIKE '%Pan-India Live RFQ Stream%'
                       OR LOWER(category) LIKE '%solvent%'
                       OR LOWER(category) LIKE '%chemical%'
                       OR LOWER(category) LIKE '%acetone%'
                       OR LOWER(category) LIKE '%toluene%'
                       OR LOWER(category) LIKE '%paint%'
                       OR LOWER(category) LIKE '%resin%'
                       OR LOWER(category) LIKE '%pharma%'
                       OR LOWER(category) LIKE '%intermediate%';
                """)

            # Backfill last_pitched_at for any previously pitched leads
            if IS_POSTGRES:
                cursor.execute("""
                    UPDATE leads l
                    SET last_pitched_at = sub.max_sent
                    FROM (
                        SELECT lead_id, MAX(sent_at) as max_sent
                        FROM outreach_history
                        WHERE status = 'Sent' AND lead_id IS NOT NULL
                        GROUP BY lead_id
                    ) sub
                    WHERE l.id = sub.lead_id AND l.last_pitched_at IS NULL;
                """)
            else:
                cursor.execute("""
                    UPDATE leads
                    SET last_pitched_at = (SELECT MAX(sent_at) FROM outreach_history WHERE lead_id = leads.id AND status = 'Sent')
                    WHERE id IN (SELECT lead_id FROM outreach_history WHERE status = 'Sent' AND lead_id IS NOT NULL)
                      AND last_pitched_at IS NULL;
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
        - Tier A (Mega Accounts > ₹10 Lakhs): Dyson Commercial Systems, Turnkey Fitout Giants, High-Rise Projects, JSW Expansion Joints
        - Tier B (Commercial Projects ₹2L - ₹10L): Gypsum Plasterboard Projects, Plywood Truckloads, Dr Fixit Fastflex
        - Tier C (Recurring Flow < ₹2L): Fevicol Retail, Carpentry Packs, Routine Maintenance
        """
        combined = f"{category} {query_text}".lower()
        if any(k in combined for k in ["dyson", "airblade", "hand dryer", "air purifier", "jsw", "expansion joint", "movement joint", "infrastructure", "turnkey", "fitout giant", "tower", "high-rise", "nearing possession"]):
            return "Tier A - Mega Account", 1500000  # Avg 15 Lakhs
        elif any(k in combined for k in ["gypsum", "plasterboard", "false ceiling", "plywood", "bwp", "marine ply", "fitout", "commercial interior", "fastflex", "pidilite", "fevicol", "dr fixit", "waterproofing"]):
            return "Tier B - Commercial Project", 500000  # Avg 5 Lakhs
        return "Tier C - Recurring Flow", 75000  # Avg 75k

    def add_lead(self, name: str, category: str, city: str = "Thane", 
                 area: str = "", phone: str = "", email: str = "", 
                 address: str = "", source: str = "Scraper",
                 deal_tier: Optional[str] = None, estimated_value: Optional[int] = None,
                 contact_person: str = "", created_at: Optional[str] = None) -> Optional[int]:
        
        name_clean = name.strip()
        name_lower = name_clean.lower()
        # Strict quality filter: discard non-business entries
        if any(junk in name_lower for junk in [
            "wikipedia", "dictionary", "merriam", "definition", "meaning",
            "español", "espanol", "microsoft support", "microsoft account",
            "explore types", "what is ", "best 10", "top 10"
        ]):
            return None

        # Filter out disallowed products (strictly 5 allowed: Gypsum, Plywood, Pidilite, Dyson, Expansion joints)
        cat_lower = category.lower()
        if any(disallowed in cat_lower for disallowed in ["solvent", "acetone", "toluene", "chemical", "tanker", "paint", "resin", "intermediate", "pharma api"]):
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
                    if created_at:
                        cursor.execute(f"""
                            INSERT INTO leads (name, contact_person, category, city, area, phone, email, address, source, status, deal_tier, estimated_deal_value, created_at)
                            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'New', {p}, {p}, {p})
                            ON CONFLICT (name, phone) DO UPDATE SET
                                contact_person = CASE WHEN EXCLUDED.contact_person != '' THEN EXCLUDED.contact_person ELSE leads.contact_person END,
                                email = CASE WHEN EXCLUDED.email != '' THEN EXCLUDED.email ELSE leads.email END,
                                created_at = EXCLUDED.created_at
                            RETURNING id
                        """, (name_clean, contact_person_clean, category.strip(), city.strip(), area.strip(), phone_clean, email_clean, address.strip(), source_clean, final_tier, final_val, created_at))
                    else:
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
                    if created_at:
                        cursor.execute(f"""
                            INSERT INTO leads (name, contact_person, category, city, area, phone, email, address, source, status, deal_tier, estimated_deal_value, created_at)
                            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'New', {p}, {p}, {p})
                        """, (name_clean, contact_person_clean, category.strip(), city.strip(), area.strip(), phone_clean, email_clean, address.strip(), source_clean, final_tier, final_val, created_at))
                    else:
                        cursor.execute(f"""
                            INSERT INTO leads (name, contact_person, category, city, area, phone, email, address, source, status, deal_tier, estimated_deal_value)
                            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'New', {p}, {p})
                        """, (name_clean, contact_person_clean, category.strip(), city.strip(), area.strip(), phone_clean, email_clean, address.strip(), source_clean, final_tier, final_val))
                    conn.commit()
                    return cursor.lastrowid
            except Exception:
                if not IS_POSTGRES and created_at:
                    try:
                        cursor.execute("UPDATE leads SET created_at = ? WHERE name = ? AND phone = ?", (created_at, name_clean, phone_clean))
                        conn.commit()
                    except Exception:
                        pass
                return None

    @staticmethod
    def compute_lead_age(created_at) -> Dict[str, Any]:
        """
        Calculates exact age write-up for lead (e.g. 'Today (2 hours old)', '1 day old', '2 days old', '7 days old').
        """
        if not created_at:
            return {"days_old": 0, "age_label": "Today"}
        
        dt = None
        if isinstance(created_at, datetime):
            dt = created_at
        elif isinstance(created_at, str):
            clean_str = created_at.split("+")[0].strip()
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(clean_str, fmt)
                    break
                except ValueError:
                    pass
        
        if not dt:
            return {"days_old": 0, "age_label": "Today"}
            
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
            
        now = datetime.utcnow()
        diff = now - dt
        total_seconds = max(0, diff.total_seconds())
        days = int(total_seconds // 86400)
        hours = int((total_seconds % 86400) // 3600)
        
        if days == 0:
            if hours < 1:
                label = "Today (Just now)"
            elif hours == 1:
                label = "Today (1 hour old)"
            else:
                label = f"Today ({hours} hours old)"
        elif days == 1:
            label = "1 day old"
        else:
            label = f"{days} days old"
            
        return {"days_old": days, "age_label": label}

    def purge_leads_older_than(self, days: int = 7) -> int:
        """
        Enforces strict rolling window: deletes any leads older than `days` days,
        and purges synthetic/duplicate inquiry entries.
        """
        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            if self.is_postgres:
                cursor.execute(f"""
                    DELETE FROM leads 
                    WHERE created_at < NOW() - INTERVAL '{days} days'
                       OR email LIKE 'rfq.%@gmail.com' 
                       OR email LIKE 'procurement.%@gmail.com' 
                       OR name LIKE '%Inquiry #%'
                       OR name LIKE '%(Inquiry%'
                       OR source LIKE '%Pan-India Live RFQ Stream%'
                """)
            else:
                cursor.execute(f"""
                    DELETE FROM leads 
                    WHERE created_at < datetime('now', '-{days} days')
                       OR email LIKE 'rfq.%@gmail.com' 
                       OR email LIKE 'procurement.%@gmail.com' 
                       OR name LIKE '%Inquiry #%'
                       OR name LIKE '%(Inquiry%'
                       OR source LIKE '%Pan-India Live RFQ Stream%'
                """)
            count = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
            conn.commit()
            return count

    def get_leads(self, category: Optional[str] = None, status: Optional[str] = None, 
                  deal_tier: Optional[str] = None, max_days_old: Optional[int] = 7, 
                  limit: int = 1000) -> List[Dict[str, Any]]:
        p = q_ph()
        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            query = "SELECT * FROM leads WHERE 1=1"
            params = []
            if max_days_old is not None:
                if IS_POSTGRES:
                    query += f" AND created_at >= NOW() - INTERVAL '{max_days_old} days'"
                else:
                    query += f" AND created_at >= datetime('now', '-{max_days_old} days')"
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
                if d.get("last_pitched_at") is not None:
                    d["last_pitched_at"] = str(d["last_pitched_at"])
                else:
                    d["last_pitched_at"] = ""

                # 48-hour follow-up calculation
                if d["last_pitched_at"]:
                    try:
                        lp_clean = d["last_pitched_at"].split("+")[0].strip()
                        lp_dt = None
                        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                            try:
                                lp_dt = datetime.strptime(lp_clean, fmt)
                                break
                            except ValueError:
                                pass
                        if lp_dt:
                            elapsed_hours = (datetime.utcnow() - lp_dt).total_seconds() / 3600.0
                            rem_hours = max(0.0, 48.0 - elapsed_hours)
                            d["followup_remaining_hours"] = round(rem_hours, 1)
                            d["followup_due"] = elapsed_hours >= 48.0
                        else:
                            d["followup_remaining_hours"] = None
                            d["followup_due"] = False
                    except Exception:
                        d["followup_remaining_hours"] = None
                        d["followup_due"] = False
                else:
                    d["followup_remaining_hours"] = None
                    d["followup_due"] = False

                if "contact_person" not in d or d["contact_person"] is None:
                    d["contact_person"] = ""
                age_info = self.compute_lead_age(d.get("created_at"))
                d["age_label"] = age_info["age_label"]
                d["days_old"] = age_info["days_old"]
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

    def record_outreach(self, lead_id: Optional[int], recipient_name: str, 
                        recipient_email: str, sender_email: str, subject: str, 
                        body: str, status: str = "Sent", error_message: str = "") -> int:
        """
        Records an outreach event into outreach_history.
        If status is 'Sent' and lead_id is provided, automatically updates lead status to 'Pitched'.
        """
        p = q_ph()
        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            if IS_POSTGRES:
                cursor.execute(f"""
                    INSERT INTO outreach_history (lead_id, recipient_name, recipient_email, sender_email, subject, body, status, error_message)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                    RETURNING id
                """, (lead_id, (recipient_name or "").strip(), recipient_email.strip(), sender_email.strip(), subject.strip(), body.strip(), status, error_message))
                row = cursor.fetchone()
                outreach_id = row["id"] if row else 0
            else:
                cursor.execute(f"""
                    INSERT INTO outreach_history (lead_id, recipient_name, recipient_email, sender_email, subject, body, status, error_message)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                """, (lead_id, (recipient_name or "").strip(), recipient_email.strip(), sender_email.strip(), subject.strip(), body.strip(), status, error_message))
                outreach_id = cursor.lastrowid
            
            # If successfully sent, update lead status to 'Pitched' and record last_pitched_at
            if status == "Sent" and lead_id:
                if IS_POSTGRES:
                    cursor.execute(f"UPDATE leads SET status = 'Pitched', last_pitched_at = CURRENT_TIMESTAMP, updated_at = {p} WHERE id = {p}", (datetime.now().isoformat(), lead_id))
                else:
                    cursor.execute(f"UPDATE leads SET status = 'Pitched', last_pitched_at = datetime('now'), updated_at = {p} WHERE id = {p}", (datetime.now().isoformat(), lead_id))
            
            conn.commit()
            return outreach_id

    def get_outreach_history(self, lead_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves sent outreach logs, joined with lead names and categories.
        """
        p = q_ph()
        with get_connection(self.db_path) as conn:
            cursor = get_cursor(conn)
            if lead_id:
                query = f"""
                    SELECT o.*, l.name as lead_name, l.category as lead_category 
                    FROM outreach_history o
                    LEFT JOIN leads l ON o.lead_id = l.id
                    WHERE o.lead_id = {p}
                    ORDER BY o.id DESC, o.sent_at DESC
                    LIMIT {p}
                """
                cursor.execute(query, (lead_id, limit))
            else:
                query = f"""
                    SELECT o.*, l.name as lead_name, l.category as lead_category 
                    FROM outreach_history o
                    LEFT JOIN leads l ON o.lead_id = l.id
                    ORDER BY o.id DESC, o.sent_at DESC
                    LIMIT {p}
                """
                cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                if d.get("sent_at") is not None:
                    d["sent_at"] = str(d["sent_at"])
                results.append(d)
            return results

if __name__ == "__main__":
    lm = LeadManager()
    print("Chemkonnect Sales Engine Database initialized. Current Stats:")
    print(lm.get_stats())