from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.db import get_db
from app.models import (
    CompanyProfile,
    Opportunity,
    OpportunityAnalysis,
    Proposal,
    ProposalComment,
    ProposalTemplate,
    ProposalVersion,
    User,
)

router = APIRouter(prefix="/proposals", tags=["proposals"])


# --- Proposal CRUD ---

class ProposalCreate(BaseModel):
    opportunity_id: str | None = None
    title: str
    template_id: str | None = None


class ProposalUpdate(BaseModel):
    title: str | None = None
    status: str | None = None


@router.get("")
async def list_proposals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Proposal)
        .options(joinedload(Proposal.opportunity))
        .order_by(desc(Proposal.updated_at))
    )
    proposals = result.unique().scalars().all()
    return [_serialize_proposal(p) for p in proposals]


@router.post("")
async def create_proposal(
    body: ProposalCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    proposal = Proposal(
        opportunity_id=body.opportunity_id,
        title=body.title,
        template_id=body.template_id,
        status="draft",
        created_by=user.id,
    )
    db.add(proposal)
    await db.flush()

    # Create initial version
    version = ProposalVersion(
        proposal_id=proposal.id,
        version_number=1,
        content={"type": "doc", "content": []},
        sections=[],
        change_summary="Initial version",
        created_by=user.id,
    )
    db.add(version)
    await db.flush()

    return _serialize_proposal(proposal)


@router.get("/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Proposal)
        .options(
            joinedload(Proposal.opportunity),
            joinedload(Proposal.versions),
            joinedload(Proposal.comments),
        )
        .where(Proposal.id == proposal_id)
    )
    proposal = result.unique().scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _serialize_proposal(proposal, include_details=True)


@router.put("/{proposal_id}")
async def update_proposal(
    proposal_id: str,
    body: ProposalUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(proposal, key, value)
    await db.flush()
    return _serialize_proposal(proposal)


@router.delete("/{proposal_id}")
async def delete_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    await db.delete(proposal)
    return {"status": "deleted"}


# --- Versions ---

class VersionCreate(BaseModel):
    content: dict
    sections: list[dict] = []
    change_summary: str = ""


@router.get("/{proposal_id}/versions")
async def list_versions(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProposalVersion)
        .where(ProposalVersion.proposal_id == proposal_id)
        .order_by(desc(ProposalVersion.version_number))
    )
    versions = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "change_summary": v.change_summary,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.post("/{proposal_id}/versions")
async def create_version(
    proposal_id: str,
    body: VersionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Get max version number
    result = await db.execute(
        select(func.max(ProposalVersion.version_number))
        .where(ProposalVersion.proposal_id == proposal_id)
    )
    max_ver = result.scalar() or 0

    version = ProposalVersion(
        proposal_id=proposal_id,
        version_number=max_ver + 1,
        content=body.content,
        sections=body.sections,
        change_summary=body.change_summary,
        created_by=user.id,
    )
    db.add(version)
    await db.flush()

    return {
        "id": str(version.id),
        "version_number": version.version_number,
        "change_summary": version.change_summary,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@router.get("/{proposal_id}/versions/{version_id}")
async def get_version(
    proposal_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProposalVersion).where(
            ProposalVersion.id == version_id,
            ProposalVersion.proposal_id == proposal_id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return {
        "id": str(version.id),
        "version_number": version.version_number,
        "content": version.content,
        "sections": version.sections,
        "change_summary": version.change_summary,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


# --- Comments ---

class CommentCreate(BaseModel):
    content: str
    section_key: str | None = None


@router.get("/{proposal_id}/comments")
async def list_comments(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProposalComment)
        .where(ProposalComment.proposal_id == proposal_id)
        .order_by(ProposalComment.created_at)
    )
    comments = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "user_id": str(c.user_id),
            "content": c.content,
            "section_key": c.section_key,
            "resolved": c.resolved,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]


@router.post("/{proposal_id}/comments")
async def add_comment(
    proposal_id: str,
    body: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = ProposalComment(
        proposal_id=proposal_id,
        user_id=user.id,
        content=body.content,
        section_key=body.section_key,
    )
    db.add(comment)
    await db.flush()
    return {
        "id": str(comment.id),
        "user_id": str(comment.user_id),
        "content": comment.content,
        "section_key": comment.section_key,
        "resolved": comment.resolved,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@router.delete("/{proposal_id}/comments/{comment_id}")
async def delete_comment(
    proposal_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProposalComment).where(
            ProposalComment.id == comment_id,
            ProposalComment.proposal_id == proposal_id,
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    await db.delete(comment)
    return {"status": "deleted"}


# --- Templates ---

class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    sections: list[dict] = []


@router.get("/templates/list")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(ProposalTemplate).order_by(ProposalTemplate.name))
    templates = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "sections": t.sections,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in templates
    ]


@router.post("/templates")
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = ProposalTemplate(
        name=body.name,
        description=body.description,
        sections=body.sections,
        created_by=user.id,
    )
    db.add(template)
    await db.flush()
    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "sections": template.sections,
    }


# --- AI Operations ---

class AIGenerateRequest(BaseModel):
    section_title: str
    section_description: str = ""


class AIRewriteRequest(BaseModel):
    text: str
    instruction: str


class AIExpandRequest(BaseModel):
    text: str


class AIComplianceRequest(BaseModel):
    text: str


@router.post("/{proposal_id}/ai/generate-section")
async def ai_generate_section(
    proposal_id: str,
    body: AIGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Proposal).options(joinedload(Proposal.opportunity)).where(Proposal.id == proposal_id)
    )
    proposal = result.unique().scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Build context
    from app.ai.analyzer import build_company_context, build_opportunity_context
    company_result = await db.execute(select(CompanyProfile).limit(1))
    company = company_result.scalar_one_or_none()
    company_ctx = build_company_context(company) if company else ""
    opp_ctx = build_opportunity_context(proposal.opportunity) if proposal.opportunity else ""

    from app.ai.proposal import generate_section
    content = await generate_section(
        body.section_title, body.section_description, opp_ctx, company_ctx
    )
    return {"content": content}


@router.post("/{proposal_id}/ai/rewrite")
async def ai_rewrite(
    proposal_id: str,
    body: AIRewriteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.ai.proposal import rewrite_text
    content = await rewrite_text(body.text, body.instruction)
    return {"content": content}


@router.post("/{proposal_id}/ai/expand")
async def ai_expand(
    proposal_id: str,
    body: AIExpandRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.ai.proposal import expand_text
    content = await expand_text(body.text)
    return {"content": content}


@router.post("/{proposal_id}/ai/compliance")
async def ai_compliance(
    proposal_id: str,
    body: AIComplianceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Proposal).options(joinedload(Proposal.opportunity)).where(Proposal.id == proposal_id)
    )
    proposal = result.unique().scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    from app.ai.analyzer import build_opportunity_context
    opp_ctx = build_opportunity_context(proposal.opportunity) if proposal.opportunity else ""

    from app.ai.proposal import add_compliance_language
    content = await add_compliance_language(body.text, opp_ctx)
    return {"content": content}


def _serialize_proposal(p: Proposal, include_details: bool = False) -> dict:
    result = {
        "id": str(p.id),
        "opportunity_id": str(p.opportunity_id) if p.opportunity_id else None,
        "title": p.title,
        "status": p.status,
        "template_id": str(p.template_id) if p.template_id else None,
        "created_by": str(p.created_by) if p.created_by else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
    if p.opportunity:
        result["opportunity_title"] = p.opportunity.title
    if include_details:
        result["versions"] = [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "content": v.content,
                "sections": v.sections,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in sorted(p.versions, key=lambda x: x.version_number, reverse=True)
        ] if p.versions else []
        result["comments"] = [
            {
                "id": str(c.id),
                "user_id": str(c.user_id),
                "content": c.content,
                "section_key": c.section_key,
                "resolved": c.resolved,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in p.comments
        ] if p.comments else []
    return result
