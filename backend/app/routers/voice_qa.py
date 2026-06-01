"""Voice Q&A endpoint - recording pen asks questions by voice."""

import os
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from typing import Optional

from app.config import get_settings, Settings
from app.models.schemas import ChatResponse
from app.services.transcription import transcribe
from app.services.summarization import answer_question
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ask", tags=["voice_qa"])


def get_vector_store(settings: Settings = Depends(get_settings)):
    return VectorStore(persist_dir=settings.chroma_persist_dir)


@router.post("/voice", response_model=ChatResponse)
async def ask_by_voice(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Recording pen sends a voice question, gets back an answer.

    Flow: voice → Whisper ASR → vector search → LLM answer → return text
    """
    # Save audio
    ext = Path(file.filename).suffix.lower()
    if ext not in (".wav", ".mp3", ".m4a", ".ogg"):
        raise HTTPException(400, f"Unsupported format: {ext}")

    ask_id = f"ask_{uuid.uuid4().hex[:12]}"
    upload_dir = Path(settings.upload_dir) / "_questions"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{ask_id}{ext}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"Saved voice question: {file_path} ({len(content)/1024:.1f} KB)")

    # 1. ASR → text
    try:
        result = transcribe(
            str(file_path),
            model_size=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    except Exception as e:
        logger.error(f"ASR failed: {e}")
        raise HTTPException(500, f"语音识别失败: {e}")

    question = result["full_text"].strip()
    if not question:
        raise HTTPException(400, "未能识别到有效语音内容，请重试")

    logger.info(f"Voice question: {question}")

    # 2. Vector search
    search_results = vector_store.search(question, n_results=5)

    if not search_results:
        return ChatResponse(
            answer="没有找到相关的会议记录。",
            sources=[],
        )

    # 3. Build context
    context_parts = []
    sources = []
    seen = set()
    for r in search_results:
        mid = r["id"]
        if mid not in seen:
            seen.add(mid)
            context_parts.append(f"[会议 {mid}]: {r['text']}")
            meta = r.get("metadata", {})
            sources.append({
                "id": mid,
                "title": meta.get("title", "Untitled"),
                "relevance": round(1 - r["score"], 3) if r["score"] else 0,
            })

    context = "\n\n".join(context_parts)

    # 4. LLM answer
    answer = answer_question(
        question,
        context,
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    # Cleanup temp question audio
    try:
        os.remove(file_path)
    except OSError:
        pass

    return ChatResponse(answer=answer, sources=sources)


@router.get("/direct")
async def ask_by_text(
    q: str = Query(..., description="Question text"),
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Recording pen sends a text question (for devices with basic TTS/input).

    Simpler than voice endpoint - no ASR needed, lower latency.
    """
    if not q.strip():
        raise HTTPException(400, "Question cannot be empty")

    search_results = vector_store.search(q, n_results=5)

    if not search_results:
        return ChatResponse(answer="没有找到相关的会议记录。", sources=[])

    context_parts = []
    sources = []
    seen = set()
    for r in search_results:
        mid = r["id"]
        if mid not in seen:
            seen.add(mid)
            context_parts.append(f"[会议 {mid}]: {r['text']}")
            meta = r.get("metadata", {})
            sources.append({
                "id": mid,
                "title": meta.get("title", "Untitled"),
                "relevance": round(1 - r["score"], 3) if r["score"] else 0,
            })

    context = "\n\n".join(context_parts)
    answer = answer_question(
        q, context,
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    return ChatResponse(answer=answer, sources=sources)
