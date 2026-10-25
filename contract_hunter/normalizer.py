"""
Contract Hunter Opportunity Schema & Normalization Engine
=========================================================
Authoritative schema definition, multi-currency salary normalization,
tech stack tag extraction, funding stage inference, and match scoring.
"""

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any


CURRENCY_RATES: Dict[str, float] = {
    "USD": 1.0,
    "$": 1.0,
    "EUR": 1.08,
    "€": 1.08,
    "GBP": 1.28,
    "£": 1.28,
    "CAD": 0.74,
    "AUD": 0.65,
}

CORE_SKILLS_PATTERNS: Dict[str, List[str]] = {
    "next.js": [r"\bnext\.?js\b", r"\bnext\s*1[345]\b"],
    "react": [r"\breact(\.?js)?\b"],
    "node.js": [r"\bnode(\.?js)?\b", r"\bexpress(\.?js)?\b", r"\bnest(\.?js)?\b"],
    "python": [r"\bpython3?\b", r"\bfastapi\b", r"\bdjango\b", r"\bflask\b"],
    "ai": [r"\bai\b", r"\bllm\b", r"\brag\b", r"\bopenai\b", r"\blangchain\b", r"\bagentic\b", r"\bdeep learning\b", r"\bmachine learning\b"],
    "sql": [r"\bsql\b", r"\bpostgresql\b", r"\bpostgres\b", r"\bmysql\b", r"\bsqlite\b"],
    "full stack": [r"\bfull[- ]?stack\b"],
    "typescript": [r"\btypescript\b", r"\bts\b"],
}

SENIOR_TITLES = [
    "senior", "sr", "lead", "staff", "principal", "architect", 
    "head", "director", "vp", "chief", "founding"
]


@dataclass
class ContractOpportunity:
    id: str                                  # Globally unique: f"{source}_{platform_id}"
    title: str                               # Role title, e.g. "Senior Full-Stack Engineer"
    company: str                             # Company name, e.g. "Nexus AI Labs"
    funding_stage: str                       # e.g. "YC W24", "Series A", "Seed", "Bootstrapped"
    salary_or_rate: str                      # Raw text, e.g. "$140k - $180k" or "$45 - $65 / hr"
    monthly_rate_usd_min: Optional[float]    # Normalized monthly min in USD ($3,500+)
    monthly_rate_usd_max: Optional[float]    # Normalized monthly max in USD ($6,000+)
    rate_period: str                         # "hourly", "daily", "monthly", "annual", "unspecified"
    is_high_ticket: bool                     # True if monthly rate >= 3500 or annual >= 42000
    skills_tags: List[str]                   # ["next.js", "python", "ai", "node.js"]
    location: str                            # "Worldwide", "EMEA", "Remote (US)"
    timezone_requirement: str                # "Worldwide", "US Overlap", "EMEA Overlap"
    source_platform: str                     # "hacker_news", "weworkremotely", "ycombinator", "wellfound", "remoteok"
    url: str                                 # Direct application or discussion URL
    posted_date: str                         # ISO 8601 UTC timestamp
    raw_description: str                     # Cleaned text description
    match_score: int                         # 0 to 100 based on technical and financial alignment
    pitch_cto: str                           # Pre-generated proposal for CTO / VP of Eng
    pitch_founder: str                       # Pre-generated proposal for Founder / CEO
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation matching PROJECT.md interface contract."""
        data = asdict(self)
        # Ensure round numbers or floats formatted cleanly
        if data["monthly_rate_usd_min"] is not None:
            data["monthly_rate_usd_min"] = round(data["monthly_rate_usd_min"], 2)
        if data["monthly_rate_usd_max"] is not None:
            data["monthly_rate_usd_max"] = round(data["monthly_rate_usd_max"], 2)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContractOpportunity":
        """Reconstruct ContractOpportunity from dict."""
        clean_data = dict(data)
        return cls(**clean_data)


def parse_salary(text: str) -> Tuple[Optional[float], Optional[float], str, str]:
    """
    Parse compensation strings across currencies into normalized monthly USD rates.
    Strict Precedence Order:
      1. Hourly (/hr, /hour, per hour) -> monthly = hourly * 160
      2. Daily (/day, per day)          -> monthly = daily * 20
      3. Monthly (/mo, /month, per month) -> monthly = monthly_val
      4. Annual (/yr, /year, k, $X-$Y)  -> monthly = annual / 12

    Returns:
      (monthly_min_usd, monthly_max_usd, rate_period, raw_matched_string)
    """
    if not text:
        return None, None, "unspecified", "Unspecified"

    # Detect currency
    currency = "USD"
    rate_factor = 1.0
    for sym, factor in CURRENCY_RATES.items():
        if sym in text.upper():
            currency = sym
            rate_factor = factor
            break

    # Helper to clean and convert numerical tokens
    def token_to_num(val_str: str) -> float:
        val_str = val_str.strip().replace(",", "").replace("$", "").replace("€", "").replace("£", "")
        multiplier = 1.0
        if val_str.lower().endswith("k"):
            multiplier = 1000.0
            val_str = val_str[:-1]
        elif val_str.lower().endswith("m"):
            multiplier = 1000000.0
            val_str = val_str[:-1]
        try:
            return float(val_str) * multiplier
        except ValueError:
            return 0.0

    # 1. Hourly Pattern: e.g. "$45 - $65 / hr", "$50/hour", "$45-65 an hour", "$50/h"
    hourly_regex = re.compile(
        r"([$€£]?\s*\d+(?:\.\d+)?(?:\s*k)?)\s*(?:-|to)?\s*([$€£]?\s*\d+(?:\.\d+)?(?:\s*k)?)"
        r"?\s*(?:/|\bper\b|\ban\b)?\s*(?:hr|hour|hourly|h)\b",
        re.IGNORECASE
    )
    m = hourly_regex.search(text)
    if m:
        low_raw = m.group(1)
        high_raw = m.group(2) or low_raw
        low = token_to_num(low_raw) * rate_factor * 160.0
        high = token_to_num(high_raw) * rate_factor * 160.0
        if low > high:
            low, high = high, low
        return round(low, 2), round(high, 2), "hourly", m.group(0).strip()

    # 2. Daily Pattern: e.g. "£400 - £600 / day", "$500 per day"
    daily_regex = re.compile(
        r"([$€£]?\s*\d+(?:\.\d+)?(?:\s*k)?)\s*(?:-|to)?\s*([$€£]?\s*\d+(?:\.\d+)?(?:\s*k)?)"
        r"?\s*(?:/|\bper\b)?\s*(?:day|daily)\b",
        re.IGNORECASE
    )
    m = daily_regex.search(text)
    if m:
        low_raw = m.group(1)
        high_raw = m.group(2) or low_raw
        low = token_to_num(low_raw) * rate_factor * 20.0
        high = token_to_num(high_raw) * rate_factor * 20.0
        if low > high:
            low, high = high, low
        return round(low, 2), round(high, 2), "daily", m.group(0).strip()

    # 3. Monthly Pattern: e.g. "$3,500 - $5,500 / mo", "$4000/month", "€3500-€5000 pm"
    monthly_regex = re.compile(
        r"([$€£]?\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*k)?)\s*(?:-|to)?\s*([$€£]?\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*k)?)"
        r"?\s*(?:/|\bper\b)?\s*(?:mo|month|monthly|pm)\b",
        re.IGNORECASE
    )
    m = monthly_regex.search(text)
    if m:
        low_raw = m.group(1)
        high_raw = m.group(2) or low_raw
        low = token_to_num(low_raw) * rate_factor
        high = token_to_num(high_raw) * rate_factor
        if low > high:
            low, high = high, low
        return round(low, 2), round(high, 2), "monthly", m.group(0).strip()

    # 4a. Annual Range Pattern with k: e.g. "$140k - $180k", "$140 - $180k", "140K-180K", "€70k-€90k"
    annual_range_regex = re.compile(
        r"([$€£]?\s*\d+(?:,\d{3})*(?:\.\d+)?\s*[kK]?)\s*(?:-|to)\s*([$€£]?\s*\d+(?:,\d{3})*(?:\.\d+)?\s*[kK])"
        r"(?:\s*(?:/|\bper\b)?\s*(?:yr|year|annually|annual))?",
        re.IGNORECASE
    )
    m = annual_range_regex.search(text)
    if m:
        low_raw = m.group(1)
        high_raw = m.group(2)
        low_annual = token_to_num(low_raw)
        high_annual = token_to_num(high_raw)
        # If numbers are small without k (e.g. 140 - 180k), scale low
        if low_annual < 1000 and high_annual >= 1000:
            low_annual *= 1000
        low = (low_annual * rate_factor) / 12.0
        high = (high_annual * rate_factor) / 12.0
        if low > high:
            low, high = high, low
        return round(low, 2), round(high, 2), "annual", m.group(0).strip()

    # 4b. Annual Single Pattern with k: e.g. "$140k", "$120k / year", "€90k", "£100k"
    annual_single_regex = re.compile(
        r"([$€£]?\s*\d+(?:,\d{3})*(?:\.\d+)?\s*[kK])"
        r"(?:\s*(?:/|\bper\b)?\s*(?:yr|year|annually|annual))?",
        re.IGNORECASE
    )
    m = annual_single_regex.search(text)
    if m:
        raw = m.group(1)
        val_annual = token_to_num(raw)
        val = (val_annual * rate_factor) / 12.0
        return round(val, 2), round(val, 2), "annual", m.group(0).strip()

    # Full annual numbers: e.g. "$120000 - $150000" or "$130,000 / yr"
    annual_large_regex = re.compile(
        r"([$€£]?\s*\d{2,3},\d{3}(?:\.\d+)?)\s*(?:-|to)?\s*([$€£]?\s*\d{2,3},\d{3}(?:\.\d+)?)?"
        r"(?:\s*(?:/|\bper\b)?\s*(?:yr|year|annually|annual))?",
        re.IGNORECASE
    )
    m = annual_large_regex.search(text)
    if m:
        low_raw = m.group(1)
        high_raw = m.group(2) or low_raw
        low = (token_to_num(low_raw) * rate_factor) / 12.0
        high = (token_to_num(high_raw) * rate_factor) / 12.0
        if low > high:
            low, high = high, low
        return round(low, 2), round(high, 2), "annual", m.group(0).strip()

    return None, None, "unspecified", "Unspecified"


def is_high_ticket_opportunity(
    monthly_min: Optional[float], 
    monthly_max: Optional[float], 
    title: str = "",
    raw_text: str = ""
) -> bool:
    """
    Determine if an opportunity meets high-ticket criteria ($3,500 - $6,000+/mo).
    If compensation is unspecified, senior roles qualify by default.
    """
    if monthly_max is not None and monthly_max >= 3500.0:
        return True
    if monthly_min is not None and monthly_min >= 3500.0:
        return True

    # If salary unspecified, check for Senior/Lead/Architect roles
    combined = f"{title} {raw_text}".lower()
    if any(keyword in combined for keyword in SENIOR_TITLES):
        return True

    return False


def extract_skills(text: str, existing_tags: Optional[List[str]] = None) -> List[str]:
    """
    Identify target skill tags from text and existing tags.
    Target competencies: next.js, react, node.js, python, ai, sql, full stack, typescript.
    """
    matched = set()
    if existing_tags:
        for t in existing_tags:
            tag_lower = t.lower().strip()
            for skill, patterns in CORE_SKILLS_PATTERNS.items():
                if any(re.search(pat, tag_lower) for pat in patterns):
                    matched.add(skill)

    text_lower = text.lower()
    for skill, patterns in CORE_SKILLS_PATTERNS.items():
        if any(re.search(pat, text_lower) for pat in patterns):
            matched.add(skill)

    # Deterministic sorting
    ordered = [s for s in ["next.js", "react", "node.js", "python", "ai", "sql", "full stack", "typescript"] if s in matched]
    return ordered


def infer_funding_stage(company: str, text: str) -> str:
    """
    Infer startup funding stage or YC cohort from company name, batch codes, or text.
    """
    combined = f"{company} {text}"
    
    # 1. YC Batch regex: e.g. YC W24, YC S23, (W24), (S21)
    yc_match = re.search(r"\b(?:YC\s*)?([WSF]\d{2})\b", combined, re.IGNORECASE)
    if yc_match:
        return f"YC {yc_match.group(1).upper()}"

    # 2. General Funding Rounds
    if re.search(r"\bseries\s+b\b", combined, re.IGNORECASE):
        return "Series B"
    if re.search(r"\bseries\s+a\b", combined, re.IGNORECASE):
        return "Series A"
    if re.search(r"\bpre-?seed\b", combined, re.IGNORECASE):
        return "Pre-Seed"
    if re.search(r"\bseed\b", combined, re.IGNORECASE):
        return "Seed"
    if re.search(r"\bbootstrapped\b", combined, re.IGNORECASE):
        return "Bootstrapped"
    if re.search(r"\bgrowth\b|\bseries\s+[c-z]\b", combined, re.IGNORECASE):
        return "Growth / Scaleup"
    if re.search(r"\bpublic\b|\benterprise\b", combined, re.IGNORECASE):
        return "Enterprise / Public"

    return "Startup / Private"


def compute_match_score(
    skills: List[str], 
    monthly_max: Optional[float], 
    is_high_ticket: bool,
    location: str, 
    timezone: str
) -> int:
    """
    Calculate an opportunity match score from 0 to 100 points:
      - Core Tech Stack Alignment (up to 45 pts):
          * Next.js / React: +15
          * Python / AI: +15
          * Node.js / Full-Stack: +15
      - High-Ticket Compensation (up to 30 pts):
          * Monthly rate >= $5,000: +30
          * Monthly rate $3,500 - $4,999: +20
          * Unspecified senior high-ticket: +15
          * Other: +5
      - Remote & Timezone Flexibility (up to 25 pts):
          * Worldwide / Anywhere / Remote: +25
          * EMEA / US Overlap: +20
          * Strict regional (non-remote): +5
    """
    score = 0

    # 1. Tech Stack (max 45)
    if "next.js" in skills or "react" in skills:
        score += 15
    if "python" in skills or "ai" in skills:
        score += 15
    if "node.js" in skills or "full stack" in skills:
        score += 15

    # 2. Compensation (max 30)
    if monthly_max is not None:
        if monthly_max >= 5000.0:
            score += 30
        elif monthly_max >= 3500.0:
            score += 20
        else:
            score += 10
    elif is_high_ticket:
        score += 15
    else:
        score += 5

    # 3. Location & Remote (max 25)
    loc_tz = f"{location} {timezone}".lower()
    if any(k in loc_tz for k in ["worldwide", "anywhere", "global"]):
        score += 25
    elif any(k in loc_tz for k in ["remote", "emea", "us overlap", "flexible"]):
        score += 20
    else:
        score += 10

    return min(100, max(0, score))
