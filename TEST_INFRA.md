# Master 4-Tier E2E Testing Infrastructure & Quality Assurance Specification

**System**: The Ultimate High-Ticket Software Revenue Engine  
**Author**: Eng. Abdelrahman Rashad & QA Automation Track  
**Document Version**: 1.0.0  
**Test Suite Directory**: `tests/`  
**Master Test Runner**: `tests/run_all_tests.py`  

---

## 1. Testing Philosophy & Objectives

The testing architecture of the High-Ticket Software Revenue Engine adheres to zero-compromise, opaque-box, behavior-driven quality assurance. The system is designed to acquire high-value startup and remote contracts ($3,500 - $6,000/mo) and sell enterprise AI automation packages ($1,500 - $4,000/deal). Failure in data normalization, rate-limiting, SQL guardrails, or state persistence carries direct financial risk.

### Core Testing Invariants:
1. **No Facade / No Vacuous Assertions**: Every test executes genuine system code against concrete requirements and asserts deterministic invariants. `assert True` is strictly prohibited.
2. **Deterministic Isolation**: Tests run deterministically in both networked and air-gapped/offline environments by leveraging self-contained test harnesses, ephemeral file fixtures, and fallback mocks.
3. **Progressive Testability**: Each testing tier verifies functionality through clean interfaces defined in `PROJECT.md` and preserves isolation across module boundaries.
4. **Resilient Cleanup**: All temporary artifacts, databases, and cached feeds created during testing are purged cleanly upon test teardown.

---

## 2. Formal Testing Methodologies

### 2.1 Category-Partition Testing
Each subsystem's input domain is divided into distinct categories, each subdivided into mutually exclusive partitions:

| Subsystem | Parameter / Category | Partitions | Expected Handling |
|---|---|---|---|
| **Contract Hunter** | Salary / Rate String | Hourly, Monthly, Annual, Unspecified, Mixed Currencies (USD, EUR, GBP, CAD) | Normalized to monthly USD; flagged as high-ticket if $\ge \$3,500/\text{mo}$. |
| **Contract Hunter** | Tech Skills in Job | Next.js, React, Node.js, Python, AI/LLM, SQL, Full-Stack, None | Tag extracted; dynamic technical proof bullets injected into pitch. |
| **AI Agent RAG** | Document Knowledge Type | Technical Specs, Pricing, Architecture, Policies | Ingested into BM25/vector corpus; tokenized and indexed. |
| **AI Agent RAG** | SQL Query Barrier | Safe `SELECT`, Mutating `DROP`/`DELETE`/`UPDATE`, Piggybacked/Injected SQL | Safe executed; destructive queries blocked with `SecurityError`/`ValueError`. |
| **Scraper Pipeline** | Ingestion Payload | Well-formed HTML cards, Plain headings, Corrupted/truncated HTML | Extracted gracefully; invalid rows quarantined; clean rows stored. |
| **Cockpit Engine** | Deal Stage | `leads`, `pitched`, `interviewing`, `contract_sent`, `won`, `closed` | Grouped properly; stage transitions update revenue KPIs atomically. |
| **Cockpit Engine** | Deal Monthly Value | Zero (\$0), Positive (\$3,500 - \$6,000), Outlier (\$25,000+), Negative/Invalid | Validated; sanitized in pipeline calculations without `ZeroDivisionError`. |

### 2.2 Boundary Value Analysis (BVA)
Boundary Value Analysis targets edge conditions and domain limits:
- **Financial Thresholds**:
  - Exactly $\$3,499.99/\text{mo}$ -> `is_high_ticket == False`
  - Exactly $\$3,500.00/\text{mo}$ -> `is_high_ticket == True`
  - Exactly $\$6,000.00/\text{mo}$ -> `is_high_ticket == True`
  - $\$0.00/\text{mo}$ -> Handled safely without division-by-zero during conversion metrics.
- **RAG Confidence & Search**:
  - Query tokens match 0 corpus documents -> returns empty list / low confidence without index crash.
  - Query with empty string / whitespace -> returns empty retrieval without exceptions.
  - SQL query AST boundary -> multi-statement queries containing trailing comments (e.g. `SELECT 1; -- DROP TABLE`) strictly parsed and inspected.
- **Token Bucket Rate Limiting**:
  - Request within capacity -> allowed instantly.
  - Request exceeding capacity -> throttled with appropriate wait/backoff.
  - High concurrency bursts -> bucket depletion handled gracefully without state corruption.
- **Pipeline Metric Boundaries**:
  - 0 leads, 0 deals in pipeline -> Win rate = $0.0\%$, Active MRR = $\$0.00$, In-flight = $\$0.00$ (no `NaN`).
  - 100% won deals -> Win rate = $100.0\%$.

### 2.3 Pairwise (Combinatorial) Testing
Pairwise testing systematically tests combinations of independent parameters:
- `(Source: HackerNews, Currency: USD, Role: Senior Full-Stack, Persona: CTO)`
- `(Source: WeWorkRemotely, Currency: EUR, Role: Next.js + AI Developer, Persona: Founder)`
- `(Source: RemoteOK, Currency: GBP, Role: Backend Python Architect, Persona: CTO)`
- `(Source: YCombinator, Currency: CAD, Role: Microservices Engineer, Persona: Founder)`

### 2.4 Real-World Workload Simulation
Real-world workflows represent end-to-end user actions performed by Eng. Abdelrahman Rashad:
1. Ingesting multi-platform feeds -> normalization -> export to disk.
2. Synchronizing Cockpit with exported jobs -> reviewing candidate list.
3. Adding high-ticket opportunity to active pipeline.
4. Generating dual Founder/CTO pitches.
5. Moving deal through stages (`leads` -> `pitched` -> `interviewing` -> `contract_sent` -> `won`).
6. Verifying dynamic recalculation of Active MRR, In-Flight Pipeline, and Conversion Rate.
7. Simulating backend restart and validating persistence reload.

---

## 3. The 4-Tier Test Suite Hierarchy

```
tests/
├── __init__.py
├── tier1_feature_tests.py       # Tier 1: Unit & Component Feature Coverage
├── tier2_boundary_tests.py      # Tier 2: Boundary, Fault Tolerance & Security Guardrails
├── tier3_integration_tests.py   # Tier 3: Cross-Feature Data Flow & Persistence
├── tier4_e2e_scenarios.py       # Tier 4: Real-World Business Lifecycles & DOM Verification
└── run_all_tests.py             # Master Test Runner with Formatted Reporting
```

### Tier 1: Feature Coverage (`tests/tier1_feature_tests.py`)
- **Hunter**: Validates `RemoteContractHunter`, `normalizer.py`, and `pitch_generator.py`:
  - `test_salary_normalization`: Parses hourly (\$45-\$65/hr -> \$7.2k-\$10.4k/mo), annual (\$140k-\$180k -> \$11.6k-\$15k/mo), and multi-currency rates.
  - `test_high_ticket_classification`: Flags jobs above \$3,500/mo threshold.
  - `test_skills_extraction`: Extracts `next.js`, `react`, `node.js`, `python`, `ai`, `sql`.
  - `test_dual_pitch_generation`: Asserts CTO pitch emphasizes architecture and sub-100ms TTFB; Founder pitch emphasizes roadmap velocity and MVP speed.
  - `test_hunter_export`: Asserts JSON and CSV export schema compliance.
- **AI Solutions Suite**:
  - `test_rag_ingestion_and_retrieval`: Ingests documents, verifies BM25 token scoring and source citations.
  - `test_rag_prompt_augmentation`: Verifies context injection and prompt synthesis.
  - `test_scraper_anti_detection_headers`: Verifies User-Agent and Client Hints rotation.
  - `test_scraper_parsing_and_storage`: Extracts structured items from HTML and exports to JSON/CSV.
  - `test_saas_dashboard_files`: Verifies dashboard HTML existence, telemetry engine script tags, and KPI metrics.
- **Cockpit Backend API**:
  - `test_cockpit_health`: Verifies `GET /api/health` status and version.
  - `test_cockpit_opportunities`: Verifies `GET /api/opportunities` with filtering.
  - `test_cockpit_pipeline_crud`: Verifies `GET`, `POST`, and `PUT /api/pipeline`.
  - `test_cockpit_metrics`: Verifies `GET /api/metrics` calculations.
  - `test_cockpit_pitch_endpoint`: Verifies `POST /api/pitch/generate`.

### Tier 2: Boundary & Corner Cases (`tests/tier2_boundary_tests.py`)
- **Hunter Fault Tolerance**:
  - `test_network_failure_fallback`: Simulates HTTP 500 / timeout; asserts 3-tier fallback to curated database without crash.
  - `test_malformed_salary_strings`: Feeds empty strings, symbols, and garbage text; asserts clean `None` / `unspecified`.
- **RAG & SQL Security Barriers**:
  - `test_rag_empty_and_alien_query`: Tests empty string, emojis, and unindexed tokens; asserts empty list without exception.
  - `test_safe_sql_barrier_blocking`: Tests SQL injection vectors (`DROP TABLE`, `DELETE FROM`, `UPDATE`, `INSERT`, piggybacked semicolons); asserts blocked execution.
  - `test_safe_sql_barrier_read_only`: Asserts legitimate `SELECT` queries pass through.
- **Scraper Robustness**:
  - `test_scraper_broken_html`: Tests malformed/unclosed HTML; asserts error quarantine and no crash.
  - `test_token_bucket_exhaustion`: Tests rapid token depletion; asserts rate limiting enforcement.
- **Cockpit Edge Cases**:
  - `test_pipeline_zero_leads_division`: Asserts 0 deals yields `win_rate: 0.0` and no division by zero.
  - `test_pipeline_invalid_stage_rejection`: Asserts invalid stage transition returns 400/422 or error dict.
  - `test_pipeline_nonexistent_deal_update`: Asserts 404 for updating missing item.
  - `test_pitch_generator_extreme_input`: Asserts handling of 10,000+ character company notes and empty skills.

### Tier 3: Cross-Feature Integration (`tests/tier3_integration_tests.py`)
- `test_hunter_export_to_cockpit_sync`: Hunter exports `curated_high_ticket_jobs.json` -> Cockpit syncs opportunities via `/api/opportunities/sync` -> verified in `/api/opportunities`.
- `test_pipeline_mutation_to_kpi_flow`: Deal added with \$5,000/mo -> progressed to `won` -> `/api/metrics` reflects updated `active_monthly_revenue` and recalculates win rate.
- `test_state_persistence_reload`: Pipeline deals saved to disk survive server/repository reinitialization.
- `test_cross_subsystem_pitch_workflow`: Hunter opportunity skills and company feed into Cockpit pitch generator -> produced pitch references extracted skills and engineering highlights.

### Tier 4: Real-World Scenarios (`tests/tier4_e2e_scenarios.py`)
- `test_contract_acquisition_lifecycle`: Complete end-to-end workflow: Ingest jobs -> filter \$3,500-\$6,000/mo -> select Next.js + AI opportunity -> generate CTO pitch -> add to pipeline -> advance to Interview -> advance to Contract Sent (\$5,500/mo) -> mark Won -> verify \$66,000 ARR in metrics.
- `test_enterprise_solution_sale_workflow`: Package Enterprise RAG Agent and Scraper Pipeline as B2B automation deal (\$3,500/project) -> register in Cockpit pipeline -> move to Won -> verify revenue expansion.
- `test_cockpit_and_dashboard_dom_smoke`: Headless HTML/JS verification of `cockpit/index.html` and `dashboard_preview.html`: asserts Kanban columns, KPI badges, pitch modal, navigation bar, charts, and zero broken links.

---

## 4. Feature Coverage Matrix (PROJECT.md Features 1–59)

| # | Feature | Scope | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|-------|:------:|:------:|:------:|:------:|
| 1–5 | HN Algolia Discovery & Firebase Ingestion | M1 | [x] | [x] | [x] | [x] |
| 6–7 | WWR Full-Stack & Programming RSS | M1 | [x] | [x] | [x] | [x] |
| 8–9 | YC Inertia & RemoteOK Ingestion | M1 | [x] | [x] | [x] | [x] |
| 10–14 | Normalizer, Classifier, Tags & Match Score | M1 | [x] | [x] | [x] | [x] |
| 15–17 | CTO/Founder Pitches & Tech Proofs | M1 | [x] | [x] | [x] | [x] |
| 18–22 | Fallbacks, Rate Limiter, Cache & Exporters | M1 | [x] | [x] | [x] | [x] |
| 23–27 | RAG Engine, Introspector, SafeSQL, Memory | M2 | [x] | [x] | [x] | [x] |
| 28–30 | RAG Mock Backend, CLI & Test Suite | M2 | [x] | [x] | [x] | [x] |
| 31–37 | Scraper Anti-Detection, Limiter & Exporter | M2 | [x] | [x] | [x] | [x] |
| 38–42 | SaaS Dashboard App, Components & Telemetry | M2 | [x] | [x] | [x] | [x] |
| 43–50 | Cockpit REST API, Kanban, Metrics & Persistence | M3 | [x] | [x] | [x] | [x] |
| 51–55 | Master E2E Tiers 1–4 & Test Runner | M4 | [x] | [x] | [x] | [x] |
| 56–59 | System Launchers, Manifests, Docs & Audit | M5 | [x] | [x] | [x] | [x] |

---

## 5. Execution & Verification Standards

To run the complete test suite:
```powershell
python tests/run_all_tests.py
```
Expected Output:
- Formatted console output detailing each tier's test cases.
- Execution timing per tier and overall suite.
- 100% Pass rate with exit code `0`.
