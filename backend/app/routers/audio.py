"""Audio upload and retrieval endpoints."""

import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from typing import Optional

from app.config import get_settings, Settings
from app.models.schemas import AudioUploadResponse, AudioDetail, Summary, SpeakerSegment
from app.services.transcription import transcribe
from app.services.summarization import summarize
from app.services.vector_store import VectorStore
from app.services.im_push import auto_push_meeting

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audio", tags=["audio"])


def get_vector_store(settings: Settings = Depends(get_settings)):
    return VectorStore(persist_dir=settings.chroma_persist_dir)


@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    recorded_at: Optional[str] = Form(None),
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Upload audio from recording device."""
    # Validate file
    ext = Path(file.filename).suffix.lower()
    if ext not in (".wav", ".mp3", ".m4a", ".ogg", ".aac", ".m4a"):
        raise HTTPException(400, f"Unsupported format: {ext}")

    # Save file
    rec_id = f"rec_{uuid.uuid4().hex[:12]}"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{rec_id}{ext}"

    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.max_file_size_mb:
        raise HTTPException(413, f"File too large ({file_size_mb:.1f} MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"Saved {file_path} ({file_size_mb:.1f} MB)")

    # Estimate processing time
    est_time = int(file_size_mb * 10)  # rough: ~10s per MB for whisper

    # Queue async processing (in production: celery/redis queue)
    _process_audio_background(rec_id, str(file_path), title or file.filename,
                              recorded_at, settings, vector_store)

    return AudioUploadResponse(id=rec_id, status="processing", estimated_time_sec=est_time)


def _process_audio_background(rec_id: str, file_path: str, title: str,
                               recorded_at: Optional[str], settings, vector_store):
    """Process audio in background: transcribe → summarize → vectorize."""
    import threading

    def process():
        try:
            logger.info(f"Processing {rec_id}...")

            # 1. Transcribe
            result = transcribe(
                file_path,
                model_size=settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )

            # 2. Summarize
            summary_data = summarize(
                result["full_text"],
                provider=settings.llm_provider,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
            )

            # 3. Store in vector DB
            metadata = {
                "title": title,
                "recorded_at": recorded_at or datetime.utcnow().isoformat(),
                "duration": result.get("duration", 0),
            }
            vector_store.add_meeting(
                rec_id, result["full_text"],
                summary_data.get("full_text", ""),
                metadata,
            )

            # 4. Save result metadata (in production: use DB)
            _save_result(rec_id, {
                "status": "completed",
                "title": title,
                "transcript": result["full_text"],
                "segments": result["segments"],
                "summary": summary_data,
                "recorded_at": recorded_at,
                "duration": result.get("duration", 0),
            })

            # 5. Auto-push to Feishu / IM if configured
            if settings.auto_push_meetings and settings.feishu_webhook_url:
                auto_push_meeting(
                    settings.feishu_webhook_url,
                    rec_id, title, summary_data,
                    result.get("duration", 0),
                )

            logger.info(f"Completed processing {rec_id}")

        except Exception as e:
            logger.error(f"Failed processing {rec_id}: {e}")
            _save_result(rec_id, {"status": "failed", "error": str(e)})

    threading.Thread(target=process, daemon=True).start()


# In-memory store for results (in production: use PostgreSQL/Redis)
_results_store = {}


def _save_result(rec_id: str, data: dict):
    _results_store[rec_id] = data


@router.get("/{rec_id}", response_model=AudioDetail)
async def get_audio(rec_id: str, vector_store: VectorStore = Depends(get_vector_store)):
    """Get audio record details."""
    data = _results_store.get(rec_id)
    if not data:
        # Check vector store
        context = vector_store.get_meeting_context(rec_id)
        if context:
            return AudioDetail(
                id=rec_id,
                title="Unknown",
                duration_sec=0,
                status="completed",
            )
        raise HTTPException(404, "Recording not found")

    return AudioDetail(
        id=rec_id,
        title=data.get("title", "Untitled"),
        duration_sec=data.get("duration", 0),
        recorded_at=data.get("recorded_at"),
        status=data.get("status", "unknown"),
        transcript=data.get("transcript"),
        summary=Summary(**data["summary"]) if data.get("summary") else None,
        segments=[SpeakerSegment(**s) for s in data.get("segments", [])],
    )


@router.get("/{rec_id}/summary")
async def get_summary(rec_id: str):
    """Get meeting summary for a recording."""
    data = _results_store.get(rec_id)
    if not data or "summary" not in data:
        raise HTTPException(404, "Summary not available")
    return data["summary"]


@router.get("/search")
async def search_audio(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Semantic search over meeting records."""
    results = vector_store.search(q, n_results=limit, date_from=date_from, date_to=date_to)

    # Deduplicate by meeting_id
    seen = set()
    items = []
    for r in results:
        mid = r["id"]
        if mid not in seen:
            seen.add(mid)
            meta = r.get("metadata", {})
            items.append({
                "id": mid,
                "title": meta.get("title", "Untitled"),
                "relevance_score": round(1 - r["score"], 4) if r["score"] else 0,
                "summary_snippet": r["text"][:200],
                "recorded_at": meta.get("recorded_at"),
            })

    return {"results": items, "total": len(items)}
