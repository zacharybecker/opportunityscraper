import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.ai.client import chat_completion
from app.db import async_session
from app.models import CompanyProfile, Opportunity, OpportunityAnalysis, PipelineEntry

logger = logging.getLogger(__name__)

PROMPT_VERSION = "1.0"


def build_company_context(company: CompanyProfile) -> str:
    """Build a context string from company profile."""
    parts = [f"Company: {company.name}"]
    if company.description:
        parts.append(f"Description: {company.description}")
    if company.capabilities:
        caps = ", ".join(c.get("name", "") for c in company.capabilities)
        parts.append(f"Capabilities: {caps}")
    if company.naics_codes:
        parts.append(f"NAICS Codes: {', '.join(company.naics_codes)}")
    if company.small_business_types:
        parts.append(f"Small Business Types: {', '.join(company.small_business_types)}")
    if company.certifications:
        certs = ", ".join(c.get("type", "") for c in company.certifications)
        parts.append(f"Certifications: {certs}")
    if company.past_performance:
        perf = "; ".join(
            f"{p.get('name', '')} ({p.get('agency', '')})"
            for p in company.past_performance[:5]
        )
        parts.append(f"Past Performance: {perf}")
    if company.future_goals:
        goals = "; ".join(
            g.get("title", "") for g in company.future_goals if g.get("active")
        )
        if goals:
            parts.append(f"Future Goals: {goals}")
    return "\n".join(parts)


def build_opportunity_context(opp: Opportunity) -> str:
    """Build a context string from opportunity."""
    parts = [f"Title: {opp.title}"]
    if opp.agency:
        parts.append(f"Agency: {opp.agency}")
    if opp.description:
        desc = opp.description[:3000]
        parts.append(f"Description: {desc}")
    if opp.naics_code:
        parts.append(f"NAICS: {opp.naics_code}")
    if opp.classification_code:
        parts.append(f"PSC: {opp.classification_code}")
    if opp.set_aside_type:
        parts.append(f"Set-Aside: {opp.set_aside_type}")
    if opp.notice_type:
        parts.append(f"Notice Type: {opp.notice_type}")
    if opp.place_of_performance_state:
        parts.append(f"State: {opp.place_of_performance_state}")

    # Include parsed document text
    if opp.documents:
        for doc in opp.documents:
            if isinstance(doc, dict) and doc.get("parsed_text"):
                parts.append(f"Document ({doc.get('filename', 'unknown')}): {doc['parsed_text'][:2000]}")
    return "\n".join(parts)


async def analyze_opportunity(opp: Opportunity, company: CompanyProfile) -> dict:
    """Run the 4-step AI analysis pipeline on an opportunity."""
    company_ctx = build_company_context(company)
    opp_ctx = build_opportunity_context(opp)
    total_tokens = 0
    settings = company.relevancy_settings or {}
    threshold = settings.get("min_relevancy_threshold", 30)

    # Step 1: Relevancy Score
    step1_result = await chat_completion(
        messages=[
            {"role": "system", "content": "You are an expert government contracting analyst. Evaluate the relevancy of a procurement opportunity to a company. Return ONLY valid JSON."},
            {"role": "user", "content": f"""Evaluate how relevant this opportunity is to the company.

{company_ctx}

OPPORTUNITY:
{opp_ctx}

Return JSON: {{"score": <0-100>, "label": "<high|medium|low|none>", "explanation": "<2-3 sentences>"}}

Scoring guide:
- 80-100 (high): Strong match in capabilities, NAICS, and set-aside
- 50-79 (medium): Partial match, some capabilities align
- 20-49 (low): Weak match, few relevant capabilities
- 0-19 (none): Not relevant"""},
        ],
        response_format={"type": "json_object"},
    )
    total_tokens += step1_result["tokens_used"]

    try:
        relevancy = json.loads(step1_result["content"])
    except json.JSONDecodeError:
        relevancy = {"score": 0, "label": "none", "explanation": "Failed to parse AI response"}

    score = relevancy.get("score", 0)

    # If below threshold, save minimal result and stop
    if score < threshold:
        return {
            "relevancy_score": score,
            "relevancy_label": relevancy.get("label", "none"),
            "relevancy_explanation": relevancy.get("explanation", ""),
            "capability_matches": [],
            "requirements_met": [],
            "gaps": [],
            "implementation_needs": [],
            "future_goal_matches": [],
            "ai_model": step1_result["model"],
            "tokens_used": total_tokens,
        }

    # Step 2: Capability Matching
    step2_result = await chat_completion(
        messages=[
            {"role": "system", "content": "You are an expert government contracting analyst. Match company capabilities to opportunity requirements. Return ONLY valid JSON."},
            {"role": "user", "content": f"""{company_ctx}

OPPORTUNITY:
{opp_ctx}

Identify capability matches and requirements. Return JSON:
{{
  "capability_matches": [{{"capability": "<name>", "match_strength": "<strong|moderate|weak>", "explanation": "<why>"}}],
  "requirements_met": [{{"requirement": "<what>", "how_met": "<how>", "confidence": <0.0-1.0>}}]
}}"""},
        ],
        response_format={"type": "json_object"},
    )
    total_tokens += step2_result["tokens_used"]

    try:
        capabilities = json.loads(step2_result["content"])
    except json.JSONDecodeError:
        capabilities = {"capability_matches": [], "requirements_met": []}

    # Step 3: Gap Analysis
    step3_result = await chat_completion(
        messages=[
            {"role": "system", "content": "You are an expert government contracting analyst. Identify gaps and implementation needs. Return ONLY valid JSON."},
            {"role": "user", "content": f"""{company_ctx}

OPPORTUNITY:
{opp_ctx}

Identify gaps between company capabilities and opportunity requirements, plus what would be needed to pursue. Return JSON:
{{
  "gaps": [{{"description": "<gap>", "severity": "<critical|moderate|minor>", "recommendation": "<how to address>"}}],
  "implementation_needs": [{{"need": "<what>", "effort_estimate": "<low|medium|high>", "description": "<details>"}}]
}}"""},
        ],
        response_format={"type": "json_object"},
    )
    total_tokens += step3_result["tokens_used"]

    try:
        gaps = json.loads(step3_result["content"])
    except json.JSONDecodeError:
        gaps = {"gaps": [], "implementation_needs": []}

    # Step 4: Future Goals Alignment
    step4_result = await chat_completion(
        messages=[
            {"role": "system", "content": "You are an expert government contracting analyst. Evaluate alignment with company growth goals. Return ONLY valid JSON."},
            {"role": "user", "content": f"""{company_ctx}

OPPORTUNITY:
{opp_ctx}

Evaluate how this opportunity aligns with the company's future goals. Return JSON:
{{
  "future_goal_matches": [{{"goal_title": "<goal>", "match_description": "<how it aligns>", "growth_opportunity": "<potential benefit>"}}]
}}"""},
        ],
        response_format={"type": "json_object"},
    )
    total_tokens += step4_result["tokens_used"]

    try:
        goals = json.loads(step4_result["content"])
    except json.JSONDecodeError:
        goals = {"future_goal_matches": []}

    return {
        "relevancy_score": score,
        "relevancy_label": relevancy.get("label", "none"),
        "relevancy_explanation": relevancy.get("explanation", ""),
        "capability_matches": capabilities.get("capability_matches", []),
        "requirements_met": capabilities.get("requirements_met", []),
        "gaps": gaps.get("gaps", []),
        "implementation_needs": gaps.get("implementation_needs", []),
        "future_goal_matches": goals.get("future_goal_matches", []),
        "ai_model": step1_result["model"],
        "tokens_used": total_tokens,
    }


async def run_analysis_task(opportunity_id: str):
    """Background task to run analysis on an opportunity."""
    async with async_session() as db:
        try:
            # Get opportunity
            result = await db.execute(
                select(Opportunity).where(Opportunity.id == opportunity_id)
            )
            opp = result.scalar_one_or_none()
            if not opp:
                logger.error(f"Opportunity {opportunity_id} not found")
                return

            # Get company
            company_result = await db.execute(select(CompanyProfile).limit(1))
            company = company_result.scalar_one_or_none()
            if not company:
                logger.error("No company profile found")
                return

            # Get or create analysis
            analysis_result = await db.execute(
                select(OpportunityAnalysis).where(
                    OpportunityAnalysis.opportunity_id == opportunity_id
                )
            )
            analysis = analysis_result.scalar_one_or_none()
            if not analysis:
                analysis = OpportunityAnalysis(
                    opportunity_id=opp.id,
                    company_id=company.id,
                    status="running",
                )
                db.add(analysis)
            else:
                analysis.status = "running"
            await db.commit()

            # Run analysis
            results = await analyze_opportunity(opp, company)

            # Update analysis record
            analysis.relevancy_score = results["relevancy_score"]
            analysis.relevancy_label = results["relevancy_label"]
            analysis.relevancy_explanation = results["relevancy_explanation"]
            analysis.capability_matches = results["capability_matches"]
            analysis.requirements_met = results["requirements_met"]
            analysis.gaps = results["gaps"]
            analysis.implementation_needs = results["implementation_needs"]
            analysis.future_goal_matches = results["future_goal_matches"]
            analysis.ai_model = results["ai_model"]
            analysis.prompt_version = PROMPT_VERSION
            analysis.tokens_used = results["tokens_used"]
            analysis.status = "completed"
            analysis.analyzed_at = datetime.now(timezone.utc)

            # Auto-add to pipeline if configured
            settings = company.relevancy_settings or {}
            if settings.get("auto_pipeline") and results["relevancy_score"] >= settings.get("min_relevancy_threshold", 30):
                existing_pipeline = await db.execute(
                    select(PipelineEntry).where(PipelineEntry.opportunity_id == opp.id)
                )
                if not existing_pipeline.scalar_one_or_none():
                    pipeline_entry = PipelineEntry(
                        opportunity_id=opp.id,
                        stage="found",
                        priority=min(10, max(1, int(results["relevancy_score"] / 10))),
                        history=[{
                            "from": None,
                            "to": "found",
                            "by": "system",
                            "notes": f"Auto-added (relevancy: {results['relevancy_score']})",
                            "at": datetime.now(timezone.utc).isoformat(),
                        }],
                    )
                    db.add(pipeline_entry)

            await db.commit()
            logger.info(f"Analysis completed for {opportunity_id}: score={results['relevancy_score']}")

        except Exception as e:
            logger.error(f"Analysis failed for {opportunity_id}: {e}")
            async with async_session() as err_db:
                result = await err_db.execute(
                    select(OpportunityAnalysis).where(
                        OpportunityAnalysis.opportunity_id == opportunity_id
                    )
                )
                analysis = result.scalar_one_or_none()
                if analysis:
                    analysis.status = "failed"
                    analysis.error_message = str(e)
                    await err_db.commit()
