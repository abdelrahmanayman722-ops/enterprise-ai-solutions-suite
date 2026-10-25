"""
Executive Pipeline Cockpit - FastAPI REST Server
Milestone 3 (R3) for The Ultimate High-Ticket Software Revenue Engine
Author: Eng. Abdelrahman Rashad
Port: 8000
"""

import csv
import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Constants & Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PIPELINE_FILE = DATA_DIR / "pipeline_state.json"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities_cache.json"
HUNTER_EXPORT_FILE = BASE_DIR.parent / "contract_hunter" / "curated_high_ticket_jobs.json"

SERVER_START_TIME = time.time()
VALID_STAGES = ["leads", "pitched", "interviewing", "contract_sent", "won", "closed"]

app = FastAPI(
    title="Executive Pipeline Cockpit API",
    description="Local executive command center for high-ticket contract pipeline and revenue tracking",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class DealCreate(BaseModel):
    opportunity_id: Optional[str] = None
    title: str = Field(..., min_length=2, description="Contract or Role Title")
    company: str = Field(..., min_length=1, description="Target Company Name")
    stage: str = Field("leads", description="One of: leads, pitched, interviewing, contract_sent, won, closed")
    monthly_value: float = Field(..., ge=0.0, description="Monthly contract value in USD ($3,500 - $6,000+)")
    source: Optional[str] = Field("Manual", description="Source platform (RemoteOK, HN, YC, etc.)")
    skills: Optional[List[str]] = Field(default_factory=list, description="Associated tech skills tags")
    contact_name: Optional[str] = Field("", description="Key contact or hiring manager name")
    contact_email: Optional[str] = Field("", description="Contact email address")
    notes: Optional[str] = Field("", description="Strategic notes, interview dates, or proposal details")


class DealUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    stage: Optional[str] = None
    monthly_value: Optional[float] = Field(None, ge=0.0)
    source: Optional[str] = None
    skills: Optional[List[str]] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class PitchRequest(BaseModel):
    position: str = Field(..., description="Role title")
    company: str = Field(..., description="Company name")
    skills: Optional[List[str]] = Field(default_factory=list, description="Key tech stack items")
    tone: str = Field("founder", description="Pitch persona: 'founder', 'cto', or 'freelance'")
    custom_notes: Optional[str] = Field("", description="Additional value props or context")
    contact_name: Optional[str] = Field("", description="Specific recipient name")


# ---------------------------------------------------------------------------
# Atomic Persistence Engine
# ---------------------------------------------------------------------------

def atomic_save_json(filepath: Path, payload: Any) -> None:
    """Atomically writes JSON payload to disk to prevent corrupted states."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    temp_file = filepath.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, filepath)


def load_pipeline_data() -> Dict[str, Any]:
    """Loads pipeline state from JSON file or initializes default high-ticket state."""
    if PIPELINE_FILE.exists():
        try:
            with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "deals" in data:
                    return data
        except Exception:
            pass

    default_state = {
        "version": "1.0.0",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "deals": [
            {
                "id": "deal-won-01",
                "opportunity_id": "opp-hyperflow-01",
                "title": "Fractional CTO & AI Pipeline Lead",
                "company": "HyperFlow Systems",
                "stage": "won",
                "monthly_value": 6000.0,
                "source": "Y Combinator",
                "skills": ["next.js", "python", "ai", "node.js"],
                "contact_name": "Marcus Vance (Founder & CEO)",
                "contact_email": "marcus@hyperflow.ai",
                "notes": "Signed $6,000/mo 6-month retainer for architectural direction and autonomous AI agent deployment.",
                "created_at": "2026-10-01T10:00:00Z",
                "updated_at": "2026-10-08T15:30:00Z",
            },
            {
                "id": "deal-won-02",
                "opportunity_id": "opp-apex-02",
                "title": "Enterprise RAG & Data Automation Retainer",
                "company": "Apex Venture Studio",
                "stage": "won",
                "monthly_value": 4000.0,
                "source": "WeWorkRemotely",
                "skills": ["python", "rag", "sql", "automation"],
                "contact_name": "Elena Rostova (Head of Product)",
                "contact_email": "elena@apexventures.io",
                "notes": "Active contract at $4,000/mo. Maintaining enterprise RAG agent with SafeSQL barrier and resilient data scraping pipeline.",
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-12T17:00:00Z",
            },
            {
                "id": "deal-contract-01",
                "opportunity_id": "opp-scalegrid-03",
                "title": "Enterprise Next.js SaaS Modernization",
                "company": "ScaleGrid Corp",
                "stage": "contract_sent",
                "monthly_value": 5800.0,
                "source": "Hacker News",
                "skills": ["next.js", "react", "node.js", "redis"],
                "contact_name": "David Sterling (VP Engineering)",
                "contact_email": "d.sterling@scalegrid.com",
                "notes": "MSA and SOW sent on Oct 21. Standard 6-month engagement at $5,800/mo for full Next.js 15 App Router migration.",
                "created_at": "2026-10-10T14:00:00Z",
                "updated_at": "2026-10-21T11:20:00Z",
            },
            {
                "id": "deal-interview-01",
                "opportunity_id": "opp-ddg-04",
                "title": "Senior Backend & Microservices Architect",
                "company": "DuckDuckGo",
                "stage": "interviewing",
                "monthly_value": 5500.0,
                "source": "RemoteOK",
                "skills": ["node.js", "python", "high-concurrency", "redis"],
                "contact_name": "Sarah Lin (Engineering Lead)",
                "contact_email": "slin@duckduckgo.com",
                "notes": "Passed technical design interview. Final round scheduled with Director of Platform Architecture.",
                "created_at": "2026-10-12T09:15:00Z",
                "updated_at": "2026-10-22T16:45:00Z",
            },
            {
                "id": "deal-interview-02",
                "opportunity_id": "opp-pavlov-05",
                "title": "Full-Stack Solutions Architect",
                "company": "Pavlov Tech",
                "stage": "interviewing",
                "monthly_value": 4500.0,
                "source": "Wellfound",
                "skills": ["next.js", "react", "python", "fastapi"],
                "contact_name": "Alex Pavlov (Co-Founder)",
                "contact_email": "alex@pavlovtech.eu",
                "notes": "Completed initial intro call. Pitch resonated strongly with their Q4 roadmap. Code sample review underway.",
                "created_at": "2026-10-14T08:30:00Z",
                "updated_at": "2026-10-20T13:10:00Z",
            },
            {
                "id": "deal-pitched-01",
                "opportunity_id": "opp-proxify-06",
                "title": "Senior Fullstack Developer (React/Node)",
                "company": "Proxify AB",
                "stage": "pitched",
                "monthly_value": 5200.0,
                "source": "Direct",
                "skills": ["react", "node.js", "clean-architecture", "sql"],
                "contact_name": "Henrik Lindqvist (Talent Partner)",
                "contact_email": "henrik@proxify.io",
                "notes": "Pitched via specialized European CTO letter. Highlighted European timezone alignment (Egypt GMT+3) and 10+ verified enterprise repos.",
                "created_at": "2026-10-18T11:00:00Z",
                "updated_at": "2026-10-18T11:15:00Z",
            },
            {
                "id": "deal-pitched-02",
                "opportunity_id": "opp-yuno-07",
                "title": "Lead AI Engineer - Agentic Systems",
                "company": "Yuno",
                "stage": "pitched",
                "monthly_value": 5000.0,
                "source": "RemoteOK",
                "skills": ["python", "ai", "agents", "langchain"],
                "contact_name": "Talent Acquisition Team",
                "contact_email": "hiring@yuno.payments",
                "notes": "Submitted founder pitch with dynamic tech proofs from our Enterprise RAG suite.",
                "created_at": "2026-10-19T14:40:00Z",
                "updated_at": "2026-10-19T14:45:00Z",
            },
            {
                "id": "deal-lead-01",
                "opportunity_id": "opp-sanctuary-08",
                "title": "Head of Technology & AI Integration",
                "company": "Sanctuary Computer",
                "stage": "leads",
                "monthly_value": 6000.0,
                "source": "RemoteOK",
                "skills": ["full stack", "python", "next.js", "ai"],
                "contact_name": "Hugh Francis (Partner)",
                "contact_email": "hello@sanctuary.computer",
                "notes": "Identified in fresh scrape. Top tier YC/studio client with urgent need for technical leadership.",
                "created_at": "2026-10-23T06:00:00Z",
                "updated_at": "2026-10-23T06:00:00Z",
            },
            {
                "id": "deal-lead-02",
                "opportunity_id": "opp-nexus-09",
                "title": "Full-Stack AI Solutions Developer",
                "company": "Nexus AI Labs",
                "stage": "leads",
                "monthly_value": 4800.0,
                "source": "Hacker News",
                "skills": ["next.js", "python", "ai", "react"],
                "contact_name": "Founding Team",
                "contact_email": "eng@nexusailabs.com",
                "notes": "YC W24 AI startup expanding their frontend and agent infrastructure. $4,800/mo contract opportunity.",
                "created_at": "2026-10-23T07:15:00Z",
                "updated_at": "2026-10-23T07:15:00Z",
            },
            {
                "id": "deal-closed-01",
                "opportunity_id": "opp-oldtech-10",
                "title": "Legacy Maintenance Contractor",
                "company": "Legacy Systems Corp",
                "stage": "closed",
                "monthly_value": 2500.0,
                "source": "Upwork",
                "skills": ["php", "wordpress"],
                "contact_name": "Recruiter",
                "contact_email": "info@legacy.com",
                "notes": "Declined by Abdelrahman: rate ($2,500/mo) fell below our $3,500/mo high-ticket policy, and stack does not align with core high-value expertise.",
                "created_at": "2026-10-02T10:00:00Z",
                "updated_at": "2026-10-03T16:00:00Z",
            },
        ],
    }
    atomic_save_json(PIPELINE_FILE, default_state)
    return default_state


def get_curated_opportunities() -> List[Dict[str, Any]]:
    """Loads opportunities from Hunter export or cached fallback."""
    opportunities: List[Dict[str, Any]] = []

    # Priority 1: Hunter Export JSON
    if HUNTER_EXPORT_FILE.exists():
        try:
            with open(HUNTER_EXPORT_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, list):
                    for idx, item in enumerate(raw):
                        skills = item.get("skills_tags") or item.get("matched_skills") or []
                        min_sal = item.get("monthly_rate_usd_min") or 4000.0
                        max_sal = item.get("monthly_rate_usd_max") or 6000.0
                        opp_id = item.get("id") or f"opp-hunter-{idx+1:03d}"
                        opportunities.append({
                            "id": opp_id,
                            "title": item.get("title", "High-Ticket Software Contract"),
                            "company": item.get("company", "Fast-Growing Startup"),
                            "location": item.get("location", "Remote (Worldwide)"),
                            "monthly_rate_usd_min": float(min_sal),
                            "monthly_rate_usd_max": float(max_sal),
                            "salary_or_rate": item.get("salary_or_rate") or f"${int(min_sal):,} - ${int(max_sal):,}/mo",
                            "skills_tags": skills,
                            "source_platform": item.get("source_platform") or "contract_hunter",
                            "url": item.get("url") or "https://remoteok.com",
                            "match_score": item.get("match_score", 92),
                            "pitch_cto": item.get("pitch_cto") or item.get("pitch") or "",
                            "pitch_founder": item.get("pitch_founder") or item.get("pitch") or "",
                            "posted_date": item.get("posted_date") or item.get("fetched_at") or datetime.now(timezone.utc).isoformat(),
                            "is_high_ticket": True,
                        })
        except Exception:
            pass

    # Priority 2: Cache if hunter file was empty or missing
    if not opportunities and OPPORTUNITIES_FILE.exists():
        try:
            with open(OPPORTUNITIES_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if isinstance(cached, list) and len(cached) > 0:
                    return cached
        except Exception:
            pass

    # Priority 3: Built-in High-Ticket Benchmark Catalog
    if not opportunities:
        opportunities = [
            {
                "id": "opp-ddg-01",
                "title": "Senior Backend & Microservices Architect",
                "company": "DuckDuckGo",
                "location": "Worldwide / Remote",
                "monthly_rate_usd_min": 5000.0,
                "monthly_rate_usd_max": 6500.0,
                "salary_or_rate": "$5,000 - $6,500/mo ($120k-$160k)",
                "skills_tags": ["node.js", "python", "high-concurrency", "redis"],
                "source_platform": "RemoteOK",
                "url": "https://remoteok.com/remote-jobs/remote-senior-backend-engineer-duckduckgo-1137551",
                "match_score": 96,
                "pitch_cto": "Architecting resilient microservices with sub-30ms TTFB and automated data pipelines.",
                "pitch_founder": "Accelerating your roadmap with battle-tested Full-Stack execution and zero bloat.",
                "posted_date": "2026-10-23T08:00:00Z",
                "is_high_ticket": True,
            },
            {
                "id": "opp-nexus-02",
                "title": "Full-Stack AI Solutions Developer",
                "company": "Nexus AI Labs",
                "location": "Remote (EMEA / Worldwide)",
                "monthly_rate_usd_min": 4500.0,
                "monthly_rate_usd_max": 6000.0,
                "salary_or_rate": "$4,500 - $6,000/mo ($45-$65/hr)",
                "skills_tags": ["next.js", "react", "python", "ai"],
                "source_platform": "Hacker News",
                "url": "https://news.ycombinator.com/item?id=49922569",
                "match_score": 98,
                "pitch_cto": "Delivering Next.js 15 App Router frontends wired directly to hybrid RAG pipelines with AST SQL barriers.",
                "pitch_founder": "Transforming your AI models into a polished, high-converting SaaS product in under 3 weeks.",
                "posted_date": "2026-10-23T07:30:00Z",
                "is_high_ticket": True,
            },
            {
                "id": "opp-proxify-03",
                "title": "Senior Fullstack Developer (React/Node)",
                "company": "Proxify AB",
                "location": "Full-Time Remote (Europe / EMEA)",
                "monthly_rate_usd_min": 5000.0,
                "monthly_rate_usd_max": 5800.0,
                "salary_or_rate": "€4,800 - €5,500/mo ($5.2k - $5.8k)",
                "skills_tags": ["react", "node.js", "sql", "clean-architecture"],
                "source_platform": "Direct",
                "url": "https://career.proxify.io",
                "match_score": 94,
                "pitch_cto": "Deep Clean Architecture mastery with typed contracts, unit test discipline, and zero technical debt.",
                "pitch_founder": "Dependable senior velocity in your exact timezone with daily async Loom demos.",
                "posted_date": "2026-10-22T14:00:00Z",
                "is_high_ticket": True,
            },
            {
                "id": "opp-sanctuary-04",
                "title": "Head of Technology & AI Integration",
                "company": "Sanctuary Computer",
                "location": "Remote (US / Worldwide)",
                "monthly_rate_usd_min": 5500.0,
                "monthly_rate_usd_max": 6500.0,
                "salary_or_rate": "$5,500 - $6,500/mo",
                "skills_tags": ["full stack", "python", "next.js", "ai"],
                "source_platform": "RemoteOK",
                "url": "https://remoteok.com/remote-jobs/remote-head-of-technology-sanctuary-computer-1137537",
                "match_score": 97,
                "pitch_cto": "Executive technical leadership combining modern frontend speed with enterprise automation infrastructure.",
                "pitch_founder": "Turning high-complexity product requirements into fast, revenue-generating software deliverables.",
                "posted_date": "2026-10-23T06:15:00Z",
                "is_high_ticket": True,
            },
            {
                "id": "opp-yuno-05",
                "title": "Lead AI Engineer - Agentic Systems",
                "company": "Yuno",
                "location": "Remote (Worldwide)",
                "monthly_rate_usd_min": 4800.0,
                "monthly_rate_usd_max": 6000.0,
                "salary_or_rate": "$4,800 - $6,000/mo",
                "skills_tags": ["python", "ai", "node.js", "rag"],
                "source_platform": "RemoteOK",
                "url": "https://remoteok.com/remote-jobs/remote-technical-account-manager-yuno-1137540",
                "match_score": 93,
                "pitch_cto": "Deploying production-grade cyclical AI agents with deterministic verification loops.",
                "pitch_founder": "Slashing operational costs with intelligent document comprehension and autonomous task flows.",
                "posted_date": "2026-10-23T05:00:00Z",
                "is_high_ticket": True,
            },
            {
                "id": "opp-scalegrid-06",
                "title": "Enterprise Next.js SaaS Modernization",
                "company": "ScaleGrid Corp",
                "location": "Remote (US / EMEA)",
                "monthly_rate_usd_min": 5200.0,
                "monthly_rate_usd_max": 6000.0,
                "salary_or_rate": "$5,200 - $6,000/mo",
                "skills_tags": ["next.js", "react", "node.js", "redis"],
                "source_platform": "Hacker News",
                "url": "https://news.ycombinator.com",
                "match_score": 95,
                "pitch_cto": "Next.js 15 App Router migration expert, eliminating waterfall requests and maximizing Core Web Vitals.",
                "pitch_founder": "Accelerating frontend conversions with modern, lightning-fast UI and zero downtime rollout.",
                "posted_date": "2026-10-21T18:00:00Z",
                "is_high_ticket": True,
            },
        ]

    # Save to local cache
    atomic_save_json(OPPORTUNITIES_FILE, opportunities)
    return opportunities


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    """Health check endpoint providing uptime and active deals metrics."""
    data = load_pipeline_data()
    deals = data.get("deals", [])
    active_mrr = sum(d["monthly_value"] for d in deals if d.get("stage") == "won")
    return {
        "status": "healthy",
        "version": "1.0.0",
        "active_pipeline_count": len(deals),
        "active_mrr": active_mrr,
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/opportunities")
def get_opportunities(
    min_salary: Optional[float] = Query(3500.0, description="Minimum monthly rate in USD"),
    max_salary: Optional[float] = Query(None, description="Maximum monthly rate in USD"),
    tags: Optional[str] = Query(None, description="Comma-separated skills (e.g. 'next.js,python')"),
    source: Optional[str] = Query(None, description="Source platform name"),
    search: Optional[str] = Query(None, description="Search keyword in title, company or skills"),
) -> List[Dict[str, Any]]:
    """Returns curated startup contracts and opportunities with filtering."""
    all_opps = get_curated_opportunities()
    results = []

    filter_tags = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []

    for opp in all_opps:
        # 1. Salary filter: max rate or min rate should satisfy min_salary
        opp_min = opp.get("monthly_rate_usd_min", 4000.0)
        opp_max = opp.get("monthly_rate_usd_max", opp_min)

        if min_salary is not None and opp_max < min_salary:
            continue
        if max_salary is not None and opp_min > max_salary:
            continue

        # 2. Source filter
        if source:
            opp_source = opp.get("source_platform", "").lower()
            if source.lower() not in opp_source:
                continue

        # 3. Tags filter
        opp_skills = [s.lower() for s in opp.get("skills_tags", [])]
        if filter_tags:
            if not any(any(ft in skill for skill in opp_skills) for ft in filter_tags):
                continue

        # 4. Search query
        if search:
            query = search.lower()
            text_corpus = f"{opp.get('title', '')} {opp.get('company', '')} {' '.join(opp_skills)} {opp.get('pitch_cto', '')}".lower()
            if query not in text_corpus:
                continue

        results.append(opp)

    return results


@app.post("/api/opportunities/sync")
def sync_opportunities() -> Dict[str, Any]:
    """Syncs opportunities from contract_hunter output into Cockpit store."""
    before_count = len(get_curated_opportunities())
    # Force re-read
    synced = get_curated_opportunities()
    new_added = max(0, len(synced) - before_count)
    return {
        "status": "synced",
        "count": len(synced),
        "new_added": new_added,
        "source_file": str(HUNTER_EXPORT_FILE.name),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/pipeline")
def get_pipeline() -> Dict[str, Any]:
    """Returns all pipeline deals grouped by the 6 standard Kanban stages."""
    data = load_pipeline_data()
    deals = data.get("deals", [])

    grouped: Dict[str, List[Dict[str, Any]]] = {stage: [] for stage in VALID_STAGES}
    for deal in deals:
        stage = deal.get("stage", "leads")
        if stage in grouped:
            grouped[stage].append(deal)
        else:
            grouped["leads"].append(deal)

    return {
        "stages": grouped,
        "deals": deals,
        "total": len(deals),
        # Direct top-level access for backward/alternative compatibility
        "leads": grouped["leads"],
        "pitched": grouped["pitched"],
        "interviewing": grouped["interviewing"],
        "contract_sent": grouped["contract_sent"],
        "won": grouped["won"],
        "closed": grouped["closed"],
    }


@app.post("/api/pipeline", status_code=status.HTTP_201_CREATED)
def create_deal(payload: DealCreate) -> Dict[str, Any]:
    """Creates a new deal in the executive pipeline with atomic persistence."""
    stage = payload.stage.strip().lower()
    if stage not in VALID_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage '{payload.stage}'. Must be one of: {', '.join(VALID_STAGES)}",
        )

    data = load_pipeline_data()
    new_id = f"deal-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    new_deal = {
        "id": new_id,
        "opportunity_id": payload.opportunity_id or f"opp-{uuid.uuid4().hex[:6]}",
        "title": payload.title.strip(),
        "company": payload.company.strip(),
        "stage": stage,
        "monthly_value": float(payload.monthly_value),
        "source": payload.source or "Manual",
        "skills": payload.skills or [],
        "contact_name": payload.contact_name or "",
        "contact_email": payload.contact_email or "",
        "notes": payload.notes or "",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    data["deals"].append(new_deal)
    data["updated_at"] = now_iso
    atomic_save_json(PIPELINE_FILE, data)

    return new_deal


@app.get("/api/pipeline/{item_id}")
def get_deal(item_id: str) -> Dict[str, Any]:
    """Retrieves a single deal by its identifier."""
    data = load_pipeline_data()
    for deal in data.get("deals", []):
        if deal.get("id") == item_id:
            return deal
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal '{item_id}' not found")


@app.put("/api/pipeline/{item_id}")
def update_deal(item_id: str, payload: DealUpdate) -> Dict[str, Any]:
    """Updates an existing deal stage, monthly value, notes, or contact info."""
    data = load_pipeline_data()
    deal_found = None

    for deal in data.get("deals", []):
        if deal.get("id") == item_id:
            deal_found = deal
            break

    if not deal_found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal '{item_id}' not found")

    if payload.stage is not None:
        stage = payload.stage.strip().lower()
        if stage not in VALID_STAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stage '{payload.stage}'. Must be one of: {', '.join(VALID_STAGES)}",
            )
        deal_found["stage"] = stage

    if payload.title is not None:
        deal_found["title"] = payload.title.strip()
    if payload.company is not None:
        deal_found["company"] = payload.company.strip()
    if payload.monthly_value is not None:
        deal_found["monthly_value"] = float(payload.monthly_value)
    if payload.source is not None:
        deal_found["source"] = payload.source
    if payload.skills is not None:
        deal_found["skills"] = payload.skills
    if payload.contact_name is not None:
        deal_found["contact_name"] = payload.contact_name
    if payload.contact_email is not None:
        deal_found["contact_email"] = payload.contact_email
    if payload.notes is not None:
        deal_found["notes"] = payload.notes

    now_iso = datetime.now(timezone.utc).isoformat()
    deal_found["updated_at"] = now_iso
    data["updated_at"] = now_iso
    atomic_save_json(PIPELINE_FILE, data)

    return deal_found


@app.delete("/api/pipeline/{item_id}")
def delete_deal(item_id: str) -> Dict[str, Any]:
    """Deletes or archives a deal from the pipeline."""
    data = load_pipeline_data()
    initial_len = len(data.get("deals", []))
    data["deals"] = [d for d in data.get("deals", []) if d.get("id") != item_id]

    if len(data["deals"]) == initial_len:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal '{item_id}' not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    data["updated_at"] = now_iso
    atomic_save_json(PIPELINE_FILE, data)

    return {"status": "deleted", "id": item_id, "timestamp": now_iso}


@app.post("/api/pitch/generate")
def generate_pitch(req: PitchRequest) -> Dict[str, Any]:
    """Generates an executive, highly targeted pitch for CTOs, Founders, or Freelance clients."""
    tone = req.tone.lower().strip()
    skills_list = [s.strip() for s in req.skills if s.strip()]
    skills_str = ", ".join(skills_list) if skills_list else "Full-Stack, Next.js, Python, and AI Automation"
    recipient = req.contact_name.strip() if req.contact_name else f"{req.company} Team"

    if tone == "cto":
        subject = f"Technical Architecture & High-Concurrency Execution: {req.position} ({req.company})"
        body = (
            f"Hi {recipient},\n\n"
            f"I noticed your opening for {req.position}. As a Senior Full-Stack Engineer and Solutions Architect "
            f"with production mastery across {skills_str}, I engineer clean, resilient architectures with sub-30ms API latency "
            f"and zero technical bloat.\n\n"
            f"Recent verified production deliverables:\n"
            f"• Next.js 15 App Router & React 19 dashboards with sub-100ms TTFB and 95+ Core Web Vitals.\n"
            f"• High-throughput Node.js & Python backend services with Redis caching handling thousands of req/sec.\n"
            f"• Enterprise RAG & AI Agent pipelines with strict SafeSQL read-only barriers and automated test coverage.\n\n"
            f"{f'Note on context: {req.custom_notes.strip()}' + chr(10) + chr(10) if req.custom_notes else ''}"
            f"I work seamlessly with European and US time zones (Egypt GMT+3), maintaining daily async Git workflows and clean PRs. "
            f"Are you open to a brief 10-minute technical sync this week to explore how I can support your roadmap?\n\n"
            f"Best regards,\n"
            f"Eng. Abdelrahman Rashad\n"
            f"Senior Full-Stack & Solutions Architect"
        )
    elif tone == "founder":
        subject = f"Accelerating {req.company}'s Velocity: {req.position} (Eng. Abdelrahman Rashad)"
        body = (
            f"Hi {recipient},\n\n"
            f"Congrats on {req.company}'s momentum! I saw you are looking for {req.position}.\n\n"
            f"Founders hire me when they need immediate senior firepower to turn product specs into revenue-generating "
            f"software without the overhead of lengthy ramp-ups. With deep expertise across {skills_str}, I specialize in:\n"
            f"1. Rapid MVP-to-Scale Delivery: Shipping robust Next.js and Python features in days, not months.\n"
            f"2. Practical AI & Automation: Deploying intelligent data scrapers, autonomous agents, and RAG pipelines that cut operating costs.\n"
            f"3. High-Velocity Ownership: Async video demos every 24-48 hours so you always see working software.\n\n"
            f"{f'Strategic Context: {req.custom_notes.strip()}' + chr(10) + chr(10) if req.custom_notes else ''}"
            f"I can step in on a flexible contract/retainer ($3.5k - $6k/mo) starting this week. "
            f"Let's jump on a quick 10-minute discovery call to discuss your biggest engineering bottleneck.\n\n"
            f"Best regards,\n"
            f"Eng. Abdelrahman Rashad\n"
            f"Full-Stack & AI Solutions Engineer"
        )
    else:  # freelance / contract
        subject = f"Senior Contract Availability: {req.position} - Immediate Kickoff ({req.company})"
        body = (
            f"Hi {recipient},\n\n"
            f"I am writing to apply for the {req.position} contract role at {req.company}. "
            f"As an independent Senior Full-Stack Engineer with specialized capability in {skills_str}, "
            f"I provide turnkey software engineering and technical leadership on a high-impact monthly retainer.\n\n"
            f"Key advantages I bring from Day 1:\n"
            f"• Zero onboarding latency: Ready to commit verified code to your repository within 24 hours.\n"
            f"• Production-grade standard: Automated tests, strict type safety, and clean CI/CD discipline.\n"
            f"• Timezone flexibility: Full overlap with European and US business hours.\n\n"
            f"{f'Additional notes: {req.custom_notes.strip()}' + chr(10) + chr(10) if req.custom_notes else ''}"
            f"Let me know if you have 10 minutes for an introductory chat.\n\n"
            f"Best regards,\n"
            f"Eng. Abdelrahman Rashad\n"
            f"Independent Senior Software Contractor"
        )

    return {
        "subject": subject,
        "body": body,
        "char_count": len(body),
        "tone": tone,
        "position": req.position,
        "company": req.company,
    }


@app.get("/api/metrics")
def get_metrics() -> Dict[str, Any]:
    """Computes real-time revenue KPIs and conversion rates."""
    data = load_pipeline_data()
    deals = data.get("deals", [])

    stage_breakdown = {stage: {"count": 0, "subtotal_value": 0.0} for stage in VALID_STAGES}

    active_mrr = 0.0
    in_flight_value = 0.0
    total_pipeline_value = 0.0

    won_count = 0
    closed_count = 0

    for deal in deals:
        stage = deal.get("stage", "leads")
        val = float(deal.get("monthly_value", 0.0))

        if stage in stage_breakdown:
            stage_breakdown[stage]["count"] += 1
            stage_breakdown[stage]["subtotal_value"] += val
        else:
            stage_breakdown["leads"]["count"] += 1
            stage_breakdown["leads"]["subtotal_value"] += val

        total_pipeline_value += val

        if stage == "won":
            active_mrr += val
            won_count += 1
        elif stage in ("interviewing", "contract_sent"):
            in_flight_value += val
        elif stage == "closed":
            closed_count += 1

    # Win rate formula: won / (won + closed) if closed exists, else won / total
    decision_total = won_count + closed_count
    if decision_total > 0:
        win_rate = round((won_count / decision_total) * 100.0, 1)
    elif len(deals) > 0:
        win_rate = round((won_count / len(deals)) * 100.0, 1)
    else:
        win_rate = 0.0

    return {
        "active_monthly_revenue": active_mrr,
        "annual_recurring_revenue": active_mrr * 12.0,
        "in_flight_pipeline_value": in_flight_value,
        "total_pipeline_value": total_pipeline_value,
        "win_rate": win_rate,
        "total_deals": len(deals),
        "won_count": won_count,
        "closed_count": closed_count,
        "stage_breakdown": stage_breakdown,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/export")
def export_pipeline(format: str = Query("json", description="Export format: 'json' or 'csv'")) -> Response:
    """Exports entire pipeline state in JSON or CSV format."""
    data = load_pipeline_data()
    deals = data.get("deals", [])

    if format.lower() == "csv":
        output = io.StringIO()
        fieldnames = [
            "id",
            "title",
            "company",
            "stage",
            "monthly_value",
            "source",
            "skills",
            "contact_name",
            "contact_email",
            "notes",
            "created_at",
            "updated_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for deal in deals:
            row = {
                "id": deal.get("id", ""),
                "title": deal.get("title", ""),
                "company": deal.get("company", ""),
                "stage": deal.get("stage", ""),
                "monthly_value": deal.get("monthly_value", 0.0),
                "source": deal.get("source", ""),
                "skills": "; ".join(deal.get("skills", [])),
                "contact_name": deal.get("contact_name", ""),
                "contact_email": deal.get("contact_email", ""),
                "notes": deal.get("notes", "").replace("\n", " "),
                "created_at": deal.get("created_at", ""),
                "updated_at": deal.get("updated_at", ""),
            }
            writer.writerow(row)

        return PlainTextResponse(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="pipeline_export.csv"'},
        )

    # JSON export
    return Response(
        content=json.dumps(data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="pipeline_export.json"'},
    )


# ---------------------------------------------------------------------------
# Static File & UI Serving
# ---------------------------------------------------------------------------

@app.get("/")
def serve_index() -> FileResponse:
    """Serves the Cockpit Executive Web UI."""
    index_path = BASE_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path, media_type="text/html")


@app.get("/styles.css")
def serve_styles() -> FileResponse:
    """Serves custom styles.css."""
    css_path = BASE_DIR / "styles.css"
    if not css_path.exists():
        raise HTTPException(status_code=404, detail="styles.css not found")
    return FileResponse(css_path, media_type="text/css")


@app.get("/app.js")
def serve_app_js() -> FileResponse:
    """Serves client-side engine app.js."""
    js_path = BASE_DIR / "app.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="app.js not found")
    return FileResponse(js_path, media_type="application/javascript")


# Mount entire cockpit directory for other assets if needed
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Starts the Uvicorn server."""
    print(f"[*] Starting Global Revenue Engine Cockpit on http://{host}:{port}")
    uvicorn.run("cockpit.server:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    run_server(host=host, port=port)
