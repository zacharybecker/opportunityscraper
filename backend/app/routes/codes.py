import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models import NAICSCode, PSCCode, User
from app.schemas import NAICSCodeResponse, PSCCodeResponse

router = APIRouter(prefix="/codes", tags=["codes"])


@router.get("/naics", response_model=list[NAICSCodeResponse])
async def search_naics(
    search: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(NAICSCode)
    if search:
        query = query.where(
            or_(
                NAICSCode.code.ilike(f"%{search}%"),
                NAICSCode.title.ilike(f"%{search}%"),
            )
        )
    query = query.limit(50)
    result = await db.execute(query)
    return [NAICSCodeResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/psc", response_model=list[PSCCodeResponse])
async def search_psc(
    search: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(PSCCode)
    if search:
        query = query.where(
            or_(
                PSCCode.code.ilike(f"%{search}%"),
                PSCCode.description.ilike(f"%{search}%"),
            )
        )
    query = query.limit(50)
    result = await db.execute(query)
    return [PSCCodeResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/import")
async def import_codes(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    naics_count = 0
    psc_count = 0

    for row in reader:
        if "naics_code" in row or "code" in row:
            code = row.get("naics_code") or row.get("code", "")
            title = row.get("title", "")
            description = row.get("description", "")

            if len(code) <= 6 and title:
                # Check if it looks like a NAICS code (2-6 digits)
                if code.isdigit():
                    existing = await db.execute(select(NAICSCode).where(NAICSCode.code == code))
                    if not existing.scalar_one_or_none():
                        db.add(NAICSCode(code=code, title=title, description=description))
                        naics_count += 1
                else:
                    # Treat as PSC
                    existing = await db.execute(select(PSCCode).where(PSCCode.code == code))
                    if not existing.scalar_one_or_none():
                        db.add(PSCCode(code=code, description=title or description))
                        psc_count += 1

    await db.flush()
    return {"naics_imported": naics_count, "psc_imported": psc_count}
