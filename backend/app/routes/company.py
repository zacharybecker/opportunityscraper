from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models import CompanyProfile, User
from app.schemas import (
    CompanyProfileResponse,
    CompanyProfileUpdate,
    FutureGoalItem,
    RelevancySettingsResponse,
    RelevancySettingsUpdate,
)

router = APIRouter(prefix="/company", tags=["company"])


async def get_or_create_company(db: AsyncSession) -> CompanyProfile:
    result = await db.execute(select(CompanyProfile).limit(1))
    company = result.scalar_one_or_none()
    if not company:
        company = CompanyProfile(name="My Company")
        db.add(company)
        await db.flush()
    return company


@router.get("", response_model=CompanyProfileResponse)
async def get_company(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = await get_or_create_company(db)
    return CompanyProfileResponse.model_validate(company)


@router.put("", response_model=CompanyProfileResponse)
async def update_company(
    body: CompanyProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    company = await get_or_create_company(db)
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)
    await db.flush()
    return CompanyProfileResponse.model_validate(company)


@router.get("/goals")
async def get_goals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = await get_or_create_company(db)
    return company.future_goals or []


@router.put("/goals")
async def update_goals(
    goals: list[FutureGoalItem],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    company = await get_or_create_company(db)
    company.future_goals = [g.model_dump() for g in goals]
    await db.flush()
    return company.future_goals


@router.get("/relevancy-settings", response_model=RelevancySettingsResponse)
async def get_relevancy_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = await get_or_create_company(db)
    return RelevancySettingsResponse(**(company.relevancy_settings or {}))


@router.put("/relevancy-settings", response_model=RelevancySettingsResponse)
async def update_relevancy_settings(
    body: RelevancySettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    company = await get_or_create_company(db)
    current = company.relevancy_settings or {}
    update_data = body.model_dump(exclude_unset=True)
    current.update(update_data)
    company.relevancy_settings = current
    await db.flush()
    return RelevancySettingsResponse(**company.relevancy_settings)
