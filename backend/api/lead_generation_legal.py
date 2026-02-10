"""
Legal Lead Generation System for AgriTech
GDPR-compliant, ethical customer acquisition

IMPORTANT: This system uses LEGAL methods only:
- Public data from business directories
- Opt-in newsletter signups
- LinkedIn public profiles (with consent)
- Google Business listings
- Public website contact forms

NO scraping of private social media data!
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
import sqlite3
import hashlib

logger = logging.getLogger('lead-generation')


class LeadGenerationSystem:
    """
    GDPR-compliant lead management system

    Legal basis for data collection:
    - Legitimate interest (B2B marketing)
    - Explicit consent (newsletter signups)
    - Contractual necessity (client relationships)
    """

    def __init__(self, db_path: str = "backend/data/agritech.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create GDPR-compliant leads database"""
        with sqlite3.connect(self.db_path) as conn:
            # Leads table (potential customers)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Contact information (encrypted if email)
                    company_name TEXT,
                    contact_name TEXT,
                    phone TEXT,
                    email_hash TEXT,  -- Hashed email (GDPR compliance)
                    location TEXT,

                    -- Source tracking (how we found them)
                    source TEXT,  -- "linkedin", "google_business", "referral", "website"
                    source_url TEXT,
                    found_date TEXT DEFAULT (date('now')),

                    -- Lead qualification
                    interest_level TEXT,  -- "high", "medium", "low"
                    farm_type TEXT,  -- "vertical_farm", "rooftop", "greenhouse", "hobby"
                    estimated_size_m2 INTEGER,
                    tech_savvy INTEGER,  -- 1-5 rating

                    -- Status
                    status TEXT DEFAULT 'new',  -- "new", "contacted", "qualified", "converted", "rejected"
                    last_contact_date TEXT,
                    next_followup_date TEXT,

                    -- GDPR compliance
                    consent_given INTEGER DEFAULT 0,  -- 0 = no consent, 1 = consent
                    consent_date TEXT,
                    consent_method TEXT,  -- "website_form", "email_reply", "phone_call"
                    data_processing_agreement INTEGER DEFAULT 0,

                    -- Notes
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # Lead interactions (activity log)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lead_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER NOT NULL,
                    interaction_type TEXT,  -- "call", "email", "meeting", "demo"
                    interaction_date TEXT DEFAULT (datetime('now')),
                    notes TEXT,
                    outcome TEXT,
                    next_action TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads(id)
                )
            """)

            # Public sources index (legal data sources)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS legal_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT,  -- "google_business", "linkedin_company", "public_website"
                    source_name TEXT,
                    source_url TEXT,
                    last_checked TEXT DEFAULT (date('now')),
                    leads_found INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1
                )
            """)

            conn.commit()

    # ── Legal Lead Collection Methods ─────────────────────────────

    def add_lead_from_public_source(self, company_name: str, source: str,
                                     source_url: str, location: str = "Porto",
                                     **kwargs) -> int:
        """
        Add lead from LEGAL public source

        Legal sources:
        - Google Business listings (public)
        - LinkedIn company pages (public info only)
        - Public websites with contact forms
        - Business directories
        - Trade shows / events

        Args:
            company_name: Business name (public)
            source: Where you found them
            source_url: Original source URL
            location: City/region
            **kwargs: Additional public information
        """

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO leads (
                    company_name, source, source_url, location,
                    interest_level, status, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                company_name,
                source,
                source_url,
                location,
                kwargs.get('interest_level', 'low'),
                'new',
                f"Found via {source}. No consent yet - first contact needed."
            ))

            lead_id = cursor.lastrowid
            conn.commit()

            logger.info(f"New lead added: {company_name} (ID: {lead_id})")
            return lead_id

    def add_lead_with_consent(self, company_name: str, contact_name: str,
                             email: str, phone: str, consent_method: str) -> int:
        """
        Add lead who gave explicit consent (GDPR compliant)

        Consent methods:
        - "website_form" - Filled out contact form
        - "email_reply" - Replied to cold email with interest
        - "phone_call" - Gave consent on phone
        - "event" - Met at trade show, gave business card
        """

        # Hash email for GDPR compliance
        email_hash = hashlib.sha256(email.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO leads (
                    company_name, contact_name, phone, email_hash,
                    source, consent_given, consent_date, consent_method,
                    status
                )
                VALUES (?, ?, ?, ?, ?, 1, date('now'), ?, 'qualified')
            """, (
                company_name, contact_name, phone, email_hash,
                consent_method, consent_method
            ))

            lead_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Lead with consent added: {company_name} (ID: {lead_id})")
            return lead_id

    def record_interaction(self, lead_id: int, interaction_type: str,
                          notes: str, outcome: str = None) -> int:
        """Record contact attempt or meeting"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO lead_interactions (
                    lead_id, interaction_type, notes, outcome
                )
                VALUES (?, ?, ?, ?)
            """, (lead_id, interaction_type, notes, outcome))

            # Update lead last_contact_date
            conn.execute("""
                UPDATE leads
                SET last_contact_date = datetime('now')
                WHERE id = ?
            """, (lead_id,))

            conn.commit()
            return cursor.lastrowid

    def get_leads_for_followup(self, location: str = None) -> List[Dict[str, Any]]:
        """Get leads needing follow-up"""

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT * FROM leads
                WHERE status IN ('new', 'contacted')
                  AND (next_followup_date IS NULL OR next_followup_date <= date('now'))
            """

            params = []
            if location:
                query += " AND location = ?"
                params.append(location)

            query += " ORDER BY interest_level DESC, found_date ASC LIMIT 20"

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # ── GDPR Compliance ───────────────────────────────────────────

    def request_data_deletion(self, lead_id: int, reason: str):
        """GDPR Right to be Forgotten"""

        with sqlite3.connect(self.db_path) as conn:
            # Anonymize personal data
            conn.execute("""
                UPDATE leads
                SET contact_name = 'DELETED',
                    phone = 'DELETED',
                    email_hash = 'DELETED',
                    notes = 'Data deleted per GDPR request: ' || ?,
                    status = 'rejected'
                WHERE id = ?
            """, (reason, lead_id))

            conn.commit()
            logger.info(f"Lead {lead_id} data deleted per GDPR request")

    def export_lead_data(self, lead_id: int) -> Dict[str, Any]:
        """GDPR Right to Data Portability"""

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            lead = conn.execute(
                "SELECT * FROM leads WHERE id = ?", (lead_id,)
            ).fetchone()

            interactions = conn.execute("""
                SELECT * FROM lead_interactions WHERE lead_id = ?
                ORDER BY interaction_date DESC
            """, (lead_id,)).fetchall()

            return {
                "lead": dict(lead) if lead else None,
                "interactions": [dict(i) for i in interactions],
                "export_date": datetime.now().isoformat(),
            }


# ── LEGAL Lead Sources (Porto/Portugal) ──────────────────────────

LEGAL_SOURCES_PORTO = {
    "google_business": [
        # Search these on Google Maps (public listings):
        "vertical farms near Porto",
        "hydroponics Porto",
        "urban farms Portugal",
        "rooftop gardens Porto",
        "organic farms Porto",
    ],

    "linkedin_companies": [
        # LinkedIn company search (public pages only):
        "hydroponics Portugal",
        "vertical farming Portugal",
        "agtech Portugal",
        "smart farming Portugal",
    ],

    "public_directories": [
        "https://www.infoportugal.pt/",  # Portuguese business directory
        "https://www.pme.pt/",  # SME directory
    ],

    "events": [
        "FoodTech Porto events",
        "Smart Cities Porto",
        "Startup Porto Demo Day",
    ],

    "websites": [
        # Public websites with contact forms:
        "Associação Portuguesa de Agricultura Vertical",
        "Porto startups in agtech",
    ]
}


# ── Smart Targeting (Porto Market) ────────────────────────────────

def identify_target_profiles_porto() -> Dict[str, Any]:
    """
    Target customer profiles for Porto market
    (Based on public demographics, no scraping needed)
    """

    return {
        "primary_targets": [
            {
                "profile": "Tech Startups (Vertical Farms)",
                "location": "Porto Innovation District",
                "size": "50-200m²",
                "budget": "€10,000-50,000",
                "tech_level": 5,
                "pain_point": "Need monitoring system for investor demos",
                "approach": "LinkedIn InMail + cold email (B2B legal)",
            },
            {
                "profile": "Rooftop Restaurants",
                "location": "Ribeira, Foz do Douro",
                "size": "20-50m²",
                "budget": "€3,000-10,000",
                "tech_level": 3,
                "pain_point": "Want fresh herbs on-site for customers",
                "approach": "In-person visit + free sample herbs",
            },
            {
                "profile": "University Research (FEUP, U.Porto)",
                "location": "University campus",
                "size": "100-500m²",
                "budget": "EU research grants",
                "tech_level": 5,
                "pain_point": "Need data logging for research papers",
                "approach": "Email professors, offer free monitoring",
            },
            {
                "profile": "Wealthy Hobbyists",
                "location": "Boavista, Foz",
                "size": "10-30m²",
                "budget": "€2,000-5,000",
                "tech_level": 4,
                "pain_point": "Want automated home system",
                "approach": "Facebook ads + website landing page",
            },
        ],

        "secondary_targets": [
            "Organic produce stores (want local suppliers)",
            "High-end grocery stores (Mercado do Bolhão vendors)",
            "Co-working spaces (rooftop gardens)",
            "Hotels (fresh herbs for restaurants)",
        ]
    }


# Global instance
lead_system = LeadGenerationSystem()
