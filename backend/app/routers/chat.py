"""Chat & QA endpoints - query meeting content via natural language."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.config import get_settings, Settings
from app.models.schemas import ChatRequest, ChatResponse
from app.services.summarization import answer_question
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def get_vector_store(settings: Settings = Depends(get_settings)):
    return VectorStore(persist_dir=settings.chroma_persist_dir)


@router.post("/question", response_model=ChatResponse)
async def ask_question(
    req: ChatRequest,
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Ask a question about past meetings."""
    # 1. Retrieve relevant context from vector DB
    filters = req.filters or {}
    search_results = vector_store.search(
        req.question,
        n_results=5,
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
    )

    if not search_results:
        return ChatResponse(
            answer="没有找到相关的会议记录。",
            sources=[],
        )

    # 2. Build context from retrieved meetings
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

    # 3. Generate answer
    answer = answer_question(
        req.question,
        context,
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    return ChatResponse(answer=answer, sources=sources)


@router.websocket("/stream")
async def chat_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming Q&A responses."""
    await websocket.accept()
    settings = get_settings()
    vector_store = VectorStore(persist_dir=settings.chroma_persist_dir)

    try:
        while True:
            data = await websocket.receive_json()
            question = data.get("question", "")

            if not question:
                await websocket.send_json({"type": "error", "message": "Empty question"})
                continue

            # Retrieve context
            search_results = vector_store.search(question, n_results=5)
            context = "\n\n".join(
                r["text"] for r in search_results
            ) if search_results else "没有找到相关会议记录。"

            # Stream answer tokens
            from openai import OpenAI
            client = OpenAI(api_key=settings.llm_api_key)
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个会议内容助手。根据会议记录回答问题。"},
                    {"role": "user", "content": f"会议记录：{context}\n\n问题：{question}"},
                ],
                stream=True,
                temperature=0.3,
            )

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    await websocket.send_json({
                        "type": "token",
                        "content": delta.content,
                    })

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
