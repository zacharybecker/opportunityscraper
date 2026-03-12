import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import KnowledgeDocument, User
from app.services.document_parser import extract_text
from app.services.file_storage import save_upload, get_file_path, delete_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form("general"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Save file
    relative_path = await save_upload(file, "knowledge")

    # Parse text
    file_bytes = get_file_path(relative_path).read_bytes()
    extracted_text = ""
    try:
        extracted_text = extract_text(file.filename or "file", file_bytes)
    except Exception as e:
        logger.warning(f"Failed to extract text from {file.filename}: {e}")

    # Determine doc type from extension
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else "text"
    doc_type = ext if ext in ("pdf", "docx", "doc", "txt", "csv", "md") else "text"

    doc = KnowledgeDocument(
        title=title or file.filename or "Untitled",
        doc_type=doc_type,
        file_path=relative_path,
        original_filename=file.filename,
        extracted_text=extracted_text[:100000],
        category=category,
        uploaded_by=user.id,
    )
    db.add(doc)
    await db.flush()

    return _serialize(doc)


@router.get("/documents")
async def list_documents(
    category: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(KnowledgeDocument).order_by(desc(KnowledgeDocument.created_at))

    if category:
        query = query.where(KnowledgeDocument.category == category)
    if search:
        ts_query = func.plainto_tsquery('english', search)
        query = query.where(
            KnowledgeDocument.search_vector.op('@@')(ts_query)
        )

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [_serialize(d) for d in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize(doc, include_text=True)


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.file_path:
        delete_file(doc.file_path)
    await db.delete(doc)
    return {"status": "deleted"}


class UrlDocumentRequest(BaseModel):
    url: str
    title: str = ""
    category: str = "general"


@router.post("/documents/url")
async def add_url_document(
    body: UrlDocumentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(body.url)
            resp.raise_for_status()
            content = resp.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    extracted_text = ""
    try:
        # Try to extract text based on content type
        content_type = resp.headers.get("content-type", "")
        if "pdf" in content_type:
            extracted_text = extract_text("document.pdf", content)
        elif "html" in content_type:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            extracted_text = soup.get_text(separator="\n", strip=True)
        else:
            extracted_text = content.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"Failed to extract text from URL: {e}")

    doc = KnowledgeDocument(
        title=body.title or body.url,
        doc_type="url",
        url=body.url,
        extracted_text=extracted_text[:100000],
        category=body.category,
        uploaded_by=user.id,
    )
    db.add(doc)
    await db.flush()
    return _serialize(doc)


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc or not doc.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    filepath = get_file_path(doc.file_path)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(filepath),
        filename=doc.original_filename or "download",
        media_type="application/octet-stream",
    )


def _serialize(doc: KnowledgeDocument, include_text: bool = False) -> dict:
    result = {
        "id": str(doc.id),
        "title": doc.title,
        "doc_type": doc.doc_type,
        "original_filename": doc.original_filename,
        "url": doc.url,
        "category": doc.category,
        "has_text": bool(doc.extracted_text),
        "text_length": len(doc.extracted_text) if doc.extracted_text else 0,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }
    if include_text:
        result["extracted_text"] = doc.extracted_text
    return result
