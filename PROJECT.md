# Project: The Ultimate High-Ticket Software Revenue Engine

## Architecture
The system consists of three operational engines coordinated through a local executive cockpit and validated by a 4-tier E2E testing framework:
1. **R1: Startup & Remote Contract Hunter (`contract_hunter/`)**: Multi-source contract aggregator (Hacker News Algolia/Firebase, WeWorkRemotely RSS, Y Combinator Inertia, RemoteOK), normalizing high-ticket contracts ($3,500 - $6,000+/mo) with dual CTO/Founder pitch generation.
2. **R2: Enterprise AI & Automation Suite (`ai_solutions_suite/`)**: Three standalone, high-ticket saleable B2B products ($1,500 - $4,000/deal):
   - Enterprise AI Agent / RAG (`ai_agent_rag/`): Hybrid BM25/Vector RRF + text-to-SQL with AST/regex read-only safety barrier.
   - Resilient Python Web Scraper (`python_scraper_engine/`): Anti-detection, Client Hints, token bucket limiter, deduplication & SQLite UPSERT.
   - Executive SaaS Dashboard (`saas_dashboard/`): Modern Anti-Slop UI with real-time telemetry, MRR charts, and active agent fleet monitoring.
3. **R3: Executive Pipeline Cockpit (`cockpit/`)**: High-performance local web app with FastAPI REST backend (`cockpit/server.py`) and a dark-mode Kanban UI (`index.html`, `app.js`, `styles.css`) for pipeline management, live feed filtering, one-click pitch generation, and real-time revenue analytics.
4. **Master E2E Testing Suite (`tests/`)**: 4-Tier test hierarchy (Feature, Boundary, Integration, Real-World) with master runner `tests/run_all_tests.py` guaranteeing 100% automated pass.
5. **System Launch & Orchestration**: Root launcher scripts (`run_cockpit.bat`, `run_cockpit.ps1`), unified dependencies (`requirements.txt`, `package.json`), and comprehensive `README.md`.

---

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | HN Algolia Monthly Discovery | Locates latest monthly "Who is hiring?" thread automatically | M1 | Survey (R1) |
| 2 | HN Algolia Comment Streamer | Queries and filters comments with keyword search | M1 | Survey (R1) |
| 3 | HN Top-Level Comment Isolator | Filters `parent_id == story_id` to eliminate job-seeker replies | M1 | Survey (R1) |
| 4 | HN Firebase Job Stories Ingestion | Streams live YC startup jobs from Firebase REST API | M1 | Survey (R1) |
| 5 | HN Firebase Item Resolver | Resolves full metadata for individual HN job postings | M1 | Survey (R1) |
| 6 | WWR Full-Stack RSS Ingestion | Ingests live full-stack remote roles from WeWorkRemotely | M1 | Survey (R1) |
| 7 | WWR Programming & Backend Ingestion | Ingests backend, programming, and devops categories from WWR | M1 | Survey (R1) |
| 8 | YC Inertia Jobs Extractor | Extracts pre-hydrated jobs from `ycombinator.com/jobs` data-page | M1 | Survey (R1) |
| 9 | RemoteOK API Ingestion | Refactored resilient adapter consuming RemoteOK API | M1 | Survey (R1) |
| 10 | Multi-Currency Salary Normalizer | Normalizes hourly/monthly/annual rates to monthly USD ($3.5k-$6k/mo) | M1 | Survey (R1) |
| 11 | High-Ticket Classifier | Flags contracts meeting $3,500 - $6,000/mo thresholds | M1 | Survey (R1) |
| 12 | Tech Stack Tag Extractor | Identifies Next.js, React, Node, Python, AI, and SQL competencies | M1 | Survey (R1) |
| 13 | Funding Stage & Batch Inferencer | Infers YC batches (W24, S23) and funding rounds (Seed, Series A) | M1 | Survey (R1) |
| 14 | Opportunity Match Scorer | Computes 0-100 match score based on tech, compensation & remote | M1 | Survey (R1) |
| 15 | CTO-Tailored Proposal Generator | Generates engineering pitch highlighting clean architecture & speed | M1 | Survey (R1) |
| 16 | Founder-Tailored Proposal Generator | Generates business pitch highlighting velocity, MVP delivery & ROI | M1 | Survey (R1) |
| 17 | Dynamic Tech Proof Injection | Injects specific project achievements based on detected skills | M1 | Survey (R1) |
| 18 | Three-Tier Fallback Hierarchy | Live Network -> Local Cache -> Curated Emergency Fallback | M1 | Survey (R1) |
| 19 | Token Bucket Rate Limiter | Enforces per-domain request throttling & jitter | M1 | Survey (R1) |
| 20 | Local Cache Manager | Disk caching with TTL and stale-on-error guarantees | M1 | Survey (R1) |
| 21 | Unified Hunter JSON & CSV Exporter | Exports structured records to `curated_high_ticket_jobs.json/csv` | M1 | Survey (R1) |
| 22 | Hunter Automated Test Suite | Unit & integration tests for parsing, normalization, and fallbacks | M1 | Survey (R1) |
| 23 | RAG Document Knowledge Engine | BM25 sparse + dense vector embeddings with RRF rank fusion | M2 | Survey (R2) |
| 24 | RAG Relational Database Introspector | Dynamic SQLite/Postgres schema introspection for tables/columns | M2 | Survey (R2) |
| 25 | RAG SafeSQLExecutor Barrier | Strict read-only AST/regex validator blocking destructive SQL | M2 | Survey (R2) |
| 26 | RAG Conversational Memory | Sliding window buffer preserving multi-turn context | M2 | Survey (R2) |
| 27 | RAG Hallucination Guardrail | Confidence threshold ($\tau \ge 0.40$) triggering safe fallbacks | M2 | Survey (R2) |
| 28 | RAG Deterministic Mock Backend | Offline deterministic backend for 100% automated test pass | M2 | Survey (R2) |
| 29 | RAG CLI & Programmatic API | Dual interface for interactive queries and automated imports | M2 | Survey (R2) |
| 30 | RAG Automated Test Suite | Comprehensive unit tests for SQL safety, retrieval, and guardrails | M2 | Survey (R2) |
| 31 | Scraper Anti-Detection Engine | Modern User-Agent pool + Client Hints (`Sec-CH-UA`, `Sec-Fetch-*`) | M2 | Survey (R2) |
| 32 | Scraper Exponential Backoff | Backoff with full jitter preventing 429 retry storms | M2 | Survey (R2) |
| 33 | Scraper Token Bucket Limiter | Monotonic token bucket throttling per target domain | M2 | Survey (R2) |
| 34 | Scraper Data Normalizer & Deduplicator | Currency/date parsing & SHA-256 fingerprint deduplication | M2 | Survey (R2) |
| 35 | Scraper Schema Validator | Contract enforcement with error quarantine isolation | M2 | Survey (R2) |
| 36 | Scraper Multi-Format Exporter | Automatic table generation + SQLite UPSERT, JSON, and CSV export | M2 | Survey (R2) |
| 37 | Scraper Offline Test Harness | Mock HTTP transport simulating success, rate limits, and corruption | M2 | Survey (R2) |
| 38 | Dashboard Standalone Interactive App | Zero-dependency executive web app (`dashboard_app.html`) | M2 | Survey (R2) |
| 39 | Dashboard Modular React Suite | Next.js 15 / React 19 component suite in `components/` | M2 | Survey (R2) |
| 40 | Dashboard Real-Time Telemetry Engine | Dynamic simulation of ARR, req/s throughput, and cache hits | M2 | Survey (R2) |
| 41 | Dashboard Active Agent Fleet Monitor | Visual table of active AI agents with state pills and metrics | M2 | Survey (R2) |
| 42 | Dashboard Anti-Slop UI & Tests | Linear/Stripe dark-mode aesthetic with automated DOM test suite | M2 | Survey (R2) |
| 43 | Cockpit FastAPI REST Backend | Local server (`cockpit/server.py`) serving API & static UI | M3 | Survey (R3) |
| 44 | Cockpit Atomic JSON Persistence | Safe disk storage for pipeline deals (`pipeline_state.json`) | M3 | Survey (R3) |
| 45 | Cockpit 6-Stage Kanban Board | Visual deal flow (Leads, Pitched, Interview, Contract, Won, Closed) | M3 | Survey (R3) |
| 46 | Cockpit Live Feed Explorer | Filterable opportunity view ($3,500-$6,000/mo, tags, sources) | M3 | Survey (R3) |
| 47 | Cockpit 1-Click Pitch Generator | Modal generating founder/CTO pitches with copy & mailto actions | M3 | Survey (R3) |
| 48 | Cockpit Real-Time Revenue Analytics | Dynamic calculations for Active MRR, In-Flight Pipeline, Win Rate | M3 | Survey (R3) |
| 49 | Cockpit Dark-Mode Anti-Slop UI | Zero console errors, modern responsive CSS design system | M3 | Survey (R3) |
| 50 | Cockpit Automated Test Suite | API contract tests and Kanban business logic tests | M3 | Survey (R3) |
| 51 | E2E Tier 1: Feature Coverage | Unit & isolated component tests across all modules | M4 | Survey (E2E) |
| 52 | E2E Tier 2: Boundary & Corner Cases | Extreme values, network errors, empty queries, malformed feeds | M4 | Survey (E2E) |
| 53 | E2E Tier 3: Cross-Feature Integration | Data flow between Hunter, Cockpit, and AI packages | M4 | Survey (E2E) |
| 54 | E2E Tier 4: Real-World Scenarios | Full lifecycle deal flow & headless browser DOM smoke test | M4 | Survey (E2E) |
| 55 | Unified Test Runner CLI | `tests/run_all_tests.py` providing single-command 100% pass | M4 | Survey (E2E) |
| 56 | Root Launcher Scripts | `run_cockpit.bat` and `run_cockpit.ps1` for instant Windows launch | M5 | Integration |
| 57 | Unified Package & Environment Manifests | `requirements.txt` and `package.json` for one-click setup | M5 | Integration |
| 58 | Executive System Documentation | Comprehensive `README.md` with architecture & operations guide | M5 | Integration |
| 59 | Final Victory Verification & Audit | 100% automated pass verification across all modules and E2E | M5 | Integration |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Startup & Remote Contract Hunter (R1) | Multi-feed aggregator (HN, WWR, YC, RemoteOK), salary normalizer ($3.5k-$6k), pitch generator, 3-tier fallback, tests | none | DONE |
| M2 | Enterprise AI & Automation Suite (R2) | 3 saleable solutions: Enterprise RAG agent with SafeSQL, resilient scraping pipeline with SQLite UPSERT, and Anti-Slop SaaS dashboard | none | DONE |
| M3 | Executive Pipeline Cockpit (R3) | FastAPI REST backend, persistent Kanban UI, live feed explorer, 1-click pitch modal, real-time revenue analytics | M1 (interface) | DONE |
| M4 | E2E Testing Suite (Tiers 1-4) | Master runner `tests/run_all_tests.py`, Tiers 1-4 tests, `TEST_READY.md` | M1, M2, M3 | DONE |
| M5 | Final Integration, Hardening & Delivery | Root scripts (`run_cockpit.bat/.ps1`), `requirements.txt`, `README.md`, 100% E2E test verification, Victory Handoff | M1, M2, M3, M4 | DONE |

---

## Interface Contracts

### M1 (Hunter) ↔ M3 (Cockpit) & M4 (Testing)
- Export path: `contract_hunter/curated_high_ticket_jobs.json`
- Opportunity Schema:
  ```json
  {
    "id": "hn_49922569_12",
    "title": "Senior Full-Stack Engineer",
    "company": "Nexus AI Labs",
    "funding_stage": "YC W24",
    "salary_or_rate": "$140k - $180k",
    "monthly_rate_usd_min": 11666.67,
    "monthly_rate_usd_max": 15000.00,
    "rate_period": "annual",
    "is_high_ticket": true,
    "skills_tags": ["next.js", "python", "ai", "node.js"],
    "location": "Worldwide / Remote",
    "timezone_requirement": "Worldwide",
    "source_platform": "hacker_news",
    "url": "https://news.ycombinator.com/item?id=49922569",
    "posted_date": "2026-10-01T15:00:00Z",
    "raw_description": "...",
    "match_score": 95,
    "pitch_cto": "...",
    "pitch_founder": "..."
  }
  ```
- Cockpit Sync Endpoint: `POST /api/opportunities/sync` reads and updates internal pipeline opportunities.

### M2 (AI Suite) ↔ M4 (Testing) & External Callers
- RAG Agent:
  - Import: `from ai_solutions_suite.ai_agent_rag.rag_agent import EnterpriseRAGAgent`
  - Method: `agent.query(prompt: str) -> dict {"answer": str, "sources": list, "confidence": float, "executed_sql": Optional[str]}`
  - Offline Mode: `agent = EnterpriseRAGAgent(mock_mode=True)`
- Scraper Engine:
  - Import: `from ai_solutions_suite.python_scraper_engine.scraper_engine import ScraperPipeline`
  - Method: `pipeline.run(target_urls: list, output_sqlite: str = "scraped_data.db") -> list[dict]`
- SaaS Dashboard:
  - Standalone: Double-click `ai_solutions_suite/saas_dashboard/dashboard_app.html` (zero server required)
  - Components: Drop `ai_solutions_suite/saas_dashboard/components/` into Next.js App Router

### M3 (Cockpit) ↔ User Browser & M4 (Testing)
- Server: `python cockpit/server.py` runs on `http://127.0.0.1:8000`
- REST Endpoints:
  - `GET /api/health` -> `{"status": "healthy", "version": "1.0.0", "active_pipeline_count": int}`
  - `GET /api/opportunities` -> list of opportunities with filter query parameters
  - `GET /api/pipeline` -> deals grouped by 6 stages
  - `POST /api/pipeline` -> add deal `{opportunity_id, title, company, stage, monthly_value}`
  - `PUT /api/pipeline/{item_id}` -> update deal stage or details
  - `POST /api/pitch/generate` -> `{position, company, skills, tone} -> {subject, body}`
  - `GET /api/metrics` -> `{active_monthly_revenue, in_flight_pipeline_value, win_rate, total_pipeline_value}`

---

## Code Layout

```
global_revenue_engine/
├── .agents/                                # Coordination & agent state metadata
├── contract_hunter/                        # M1: R1 Remote Contract Hunter
│   ├── adapters/
│   │   ├── hn_adapter.py                   # Hacker News Algolia & Firebase
│   │   ├── wwr_adapter.py                  # WeWorkRemotely RSS
│   │   ├── yc_adapter.py                   # Y Combinator Inertia jobs
│   │   └── remoteok_adapter.py             # RemoteOK public API
│   ├── normalizer.py                       # Multi-currency salary & skills normalizer
│   ├── pitch_generator.py                  # CTO & Founder tailored pitch generator
│   ├── cache_manager.py                    # 3-Tier fallback & disk cache
│   ├── remote_contract_hunter.py           # Master Hunter orchestrator & CLI
│   ├── curated_high_ticket_jobs.json       # Ingested high-ticket jobs database
│   ├── curated_high_ticket_jobs.csv        # CSV export
│   └── test_hunter.py                      # Automated unit test suite
├── ai_solutions_suite/                     # M2: R2 Enterprise AI & Automation Packages
│   ├── ai_agent_rag/
│   │   ├── schema_introspector.py          # SQLite/Postgres schema introspection
│   │   ├── safe_sql_executor.py            # AST/regex read-only SQL safety barrier
│   │   ├── hybrid_retriever.py             # BM25 + dense vector RRF retriever
│   │   ├── conversational_memory.py        # Sliding window conversation buffer
│   │   ├── rag_agent.py                    # Enterprise RAG agent (dual engine + CLI)
│   │   └── test_rag.py                     # Automated unit test suite
│   ├── python_scraper_engine/
│   │   ├── anti_detection.py               # User-Agents, Client Hints, human jitter
│   │   ├── rate_limiter.py                 # Monotonic Token Bucket rate limiter
│   │   ├── normalizer.py                   # Currency, ISO dates, SHA-256 fingerprinting
│   │   ├── schema_validator.py             # Contract validation & quarantine
│   │   ├── storage_exporter.py             # CSV, JSON, and SQLite UPSERT exporter
│   │   ├── scraper_engine.py               # Scraper pipeline orchestrator
│   │   └── test_scraper.py                 # Automated unit test suite
│   └── saas_dashboard/
│       ├── dashboard_app.html              # Standalone interactive executive dashboard
│       ├── components/                     # Modular Next.js 15 React components
│       │   ├── ExecutiveDashboard.tsx
│       │   ├── TelemetryGrid.tsx
│       │   ├── RevenueChart.tsx
│       │   ├── AgentFleetTable.tsx
│       │   └── TransactionStream.tsx
│       └── test_dashboard.py               # DOM & telemetry logic test suite
├── cockpit/                                # M3: R3 Executive Pipeline Cockpit
│   ├── server.py                           # FastAPI / Python REST backend on port 8000
│   ├── index.html                          # Dark-mode Anti-Slop Cockpit UI
│   ├── app.js                              # Cockpit state engine & Kanban interactivity
│   ├── styles.css                          # Tailored dark-mode CSS design system
│   ├── data/
│   │   └── pipeline_state.json             # Atomic persistent deal store
│   └── test_cockpit.py                     # Cockpit API and business logic tests
├── tests/                                  # M4: Master E2E Testing Track
│   ├── __init__.py
│   ├── tier1_feature_tests.py              # Tier 1: Unit & Component Coverage
│   ├── tier2_boundary_tests.py             # Tier 2: Corner Cases & Fault Tolerance
│   ├── tier3_integration_tests.py          # Tier 3: Cross-Feature Integration
│   ├── tier4_e2e_scenarios.py              # Tier 4: Real-World Scenarios & Headless UI Smoke Tests
│   └── run_all_tests.py                    # Master CLI runner (100% pass verification)
├── requirements.txt                        # M5: Unified Python dependencies
├── package.json                            # M5: Unified Node scripts & tooling
├── run_cockpit.bat                         # M5: Windows CMD launcher
├── run_cockpit.ps1                         # M5: Windows PowerShell launcher
├── README.md                               # M5: Comprehensive system documentation
├── PROJECT.md                              # Living Project Blueprint & Milestone Register
├── TEST_INFRA.md                           # E2E Test Strategy & Matrix
└── TEST_READY.md                           # Test Suite Ready Attestation
```
