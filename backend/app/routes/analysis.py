from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import OpportunityAnalysis, User
from app.schemas import OpportunityAnalysisResponse

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/recent", response_model=list[OpportunityAnalysisResponse])
async def recent_analyses(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(OpportunityAnalysis)
        .where(OpportunityAnalysis.status == "completed")
        .order_by(desc(OpportunityAnalysis.analyzed_at))
        .limit(limit)
    )
    return [OpportunityAnalysisResponse.model_validate(a) for a in result.scalars().all()]
