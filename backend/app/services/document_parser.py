import io
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    import fitz

    text_parts = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(filename: str, content_bytes: bytes) -> str:
    """Dispatch text extraction by file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(content_bytes)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(content_bytes)
    elif ext in (".txt", ".csv", ".md"):
        return content_bytes.decode("utf-8", errors="replace")
    else:
        return content_bytes.decode("utf-8", errors="replace")


async def download_and_parse_document(url: str, filename: str) -> dict:
    """Download a document from URL and parse its text."""
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content

        parsed_text = extract_text(filename, content)
        return {
            "filename": filename,
            "parsed_text": parsed_text[:50000],  # Limit text size
            "parse_status": "completed",
        }
    except Exception as e:
        logger.error(f"Failed to download/parse {filename} from {url}: {e}")
        return {
            "filename": filename,
            "parsed_text": None,
            "parse_status": f"failed: {str(e)[:200]}",
        }
