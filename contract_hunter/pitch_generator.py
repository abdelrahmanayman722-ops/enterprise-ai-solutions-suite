"""
High-Ticket Pitch & Proposal Generator Engine
=============================================
Dual CTO and Founder high-converting pitch generator tailored for Eng. Abdelrahman Rashad.
Injects dynamic technical proofs, delivery models, and async communication guarantees.
"""

from typing import List, Optional, Tuple


def _format_skills_list(skills: List[str]) -> str:
    """Format skills list for natural prose."""
    if not skills:
        return "Modern Full-Stack Architecture, Node.js, Next.js, and Python"
    formatted = [s.title() if s != "next.js" and s != "node.js" else s for s in skills]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", and {formatted[-1]}"


def _get_dynamic_proof_bullets(skills: List[str]) -> List[str]:
    """Select dynamic portfolio bullet points matching detected skills."""
    skills_lower = [s.lower() for s in skills]
    bullets = []

    # 1. Frontend / Next.js
    if any(s in skills_lower for s in ["next.js", "react"]):
        bullets.append(
            "• Next.js 15 & React 19: Built responsive, accessible dashboards delivering "
            "sub-100ms TTFB and 95+ Core Web Vitals with zero client-side bloat."
        )

    # 2. Node / Backend / Microservices
    if any(s in skills_lower for s in ["node.js", "full stack"]):
        bullets.append(
            "• Node.js & Microservices: Designed high-concurrency RESTful APIs with Redis caching, "
            "handling thousands of req/sec with 100% automated test coverage."
        )

    # 3. Python / AI / Pipelines
    if any(s in skills_lower for s in ["python", "ai"]):
        bullets.append(
            "• Python & AI Pipelines: Engineered autonomous RAG agents and resilient data extraction "
            "pipelines with stealth anti-bot bypass and self-healing scrapers."
        )

    # 4. SQL / Data
    if "sql" in skills_lower and len(bullets) < 3:
        bullets.append(
            "• Database Architecture: Optimized PostgreSQL queries, schema indexing, and transactional "
            "integrity for high-throughput relational workloads."
        )

    # Fallback bullets if fewer than 3
    if len(bullets) < 2:
        bullets.append(
            "• Full-Stack Ownership: End-to-end delivery from responsive Next.js interfaces to robust "
            "backend microservices and cloud deployment."
        )
    if len(bullets) < 3:
        bullets.append(
            "• Automated Quality Assurance: Comprehensive unit, integration, and E2E test suites "
            "ensuring zero regression deployments."
        )

    return bullets[:3]


def generate_cto_pitch(
    position: str, 
    company: str, 
    skills: List[str]
) -> str:
    """
    Generate engineering-focused proposal for CTO / VP of Engineering.
    Emphasizes clean architecture, test coverage, sub-100ms TTFB, and microservices velocity.
    """
    clean_position = position.strip() or "Senior Full-Stack Engineer"
    clean_company = company.strip() or "Your Team"
    matched_str = _format_skills_list(skills)
    bullets = _get_dynamic_proof_bullets(skills)
    bullets_text = "\n".join(bullets)

    pitch = (
        f"Subject: Application: {clean_position} - Clean Architecture & Production Velocity ({clean_company})\n\n"
        f"Hi {clean_company} Engineering Team,\n\n"
        f"I noticed your opening for {clean_position}. As a Senior Full-Stack Engineer and Solutions Architect "
        f"with deep production mastery across {matched_str}, I specialize in architecting modular, enterprise-grade applications "
        f"with zero architectural debt.\n\n"
        f"Recent highlights from my production portfolio:\n"
        f"{bullets_text}\n\n"
        f"I work seamlessly across worldwide time zones with daily asynchronous video demos and clean Git workflows. "
        f"I would love to hop on a brief 10-minute technical chat to discuss how I can accelerate your engineering roadmap.\n\n"
        f"Best regards,\n"
        f"Eng. Abdelrahman Rashad\n"
        f"Senior Full-Stack & Solutions Architect"
    )
    return pitch


def generate_founder_pitch(
    position: str, 
    company: str, 
    skills: List[str],
    company_one_liner: Optional[str] = None
) -> str:
    """
    Generate business-focused proposal for Founder / CEO.
    Emphasizes roadmap velocity, MVP speed, low burn rate, and dedicated retainer value.
    """
    clean_position = position.strip() or "Senior Full-Stack Engineer"
    clean_company = company.strip() or "Your Startup"
    one_liner = f" {company_one_liner.strip()}" if company_one_liner else f" {clean_company}"
    matched_str = _format_skills_list(skills)
    bullets = _get_dynamic_proof_bullets(skills)
    bullets_text = "\n".join(bullets)

    pitch = (
        f"Subject: Accelerating {clean_company}'s Product Roadmap: Senior Full-Stack & AI Execution\n\n"
        f"Hi {clean_company} Leadership Team,\n\n"
        f"Congratulations on your momentum with{one_liner}. I saw your search for a {clean_position}.\n\n"
        f"At early and growth stages, shipping reliable features quickly without bloated agency costs or managerial overhead is vital. "
        f"As a Senior Full-Stack Engineer and Solutions Architect specializing in {matched_str}, I help founders transform product specs "
        f"into production-grade software in days rather than months.\n\n"
        f"What I bring to your roadmap:\n"
        f"• Rapid Feature Shipping: Full-stack ownership from Next.js 15 interactive UIs down to robust PostgreSQL/Node/Python backends.\n"
        f"• Enterprise Reliability: Self-directed execution with automated test suites—eliminating regressions before they hit staging.\n"
        f"• Autonomous Communication: Daily async progress demos, transparent deliverables, and zero timezone friction.\n\n"
        f"Whether on a dedicated monthly retainer ($3,500 - $6,000/mo) or a focused build sprint, I can step in immediately to help you hit your milestones faster.\n\n"
        f"Are you open to a brief 10-minute chat this week to explore if we're a great fit?\n\n"
        f"Best regards,\n"
        f"Eng. Abdelrahman Rashad\n"
        f"Senior Full-Stack & Solutions Architect"
    )
    return pitch


def generate_dual_pitches(
    position: str, 
    company: str, 
    skills: List[str], 
    company_one_liner: Optional[str] = None
) -> Tuple[str, str]:
    """Generate both CTO and Founder pitches simultaneously."""
    cto_pitch = generate_cto_pitch(position, company, skills)
    founder_pitch = generate_founder_pitch(position, company, skills, company_one_liner)
    return cto_pitch, founder_pitch
