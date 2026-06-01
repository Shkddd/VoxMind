"""Vector store service using ChromaDB for semantic search."""

import logging
import uuid
from typing import List, Optional

logger = logging.getLogger(__name__)


class VectorStore:
    """Wrapper around ChromaDB for meeting record vectors."""

    def __init__(self, persist_dir: str = "./chromadb"):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        try:
            return self.client.get_collection("meetings")
        except Exception:
            return self.client.create_collection("meetings")

    def add_meeting(self, meeting_id: str, transcript: str,
                    summary_text: str, metadata: Optional[dict] = None):
        """Store meeting content as vectors."""
        if metadata is None:
            metadata = {}
        metadata["meeting_id"] = meeting_id

        # Store both transcript and summary as separate chunks
        texts = []
        ids = []
        metadatas = []

        # Transcript as one chunk (or could be split into segments)
        texts.append(transcript)
        ids.append(f"{meeting_id}_transcript")
        metadatas.append({**metadata, "type": "transcript"})

        # Summary as another chunk
        texts.append(summary_text)
        ids.append(f"{meeting_id}_summary")
        metadatas.append({**metadata, "type": "summary"})

        self.collection.add(
            documents=texts,
            ids=ids,
            metadatas=metadatas,
        )
        logger.info(f"Stored meeting {meeting_id} in vector DB")

    def search(self, query: str, n_results: int = 5,
               date_from: Optional[str] = None,
               date_to: Optional[str] = None) -> List[dict]:
        """Semantic search over meetings."""
        where_filter = {}
        if date_from or date_to:
            conds = {}
            if date_from:
                conds["$gte"] = date_from
            if date_to:
                conds["$lte"] = date_to
            where_filter["recorded_at"] = conds

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None,
        )

        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "id": results["metadatas"][0][i].get("meeting_id", ""),
                "text": results["documents"][0][i][:300],
                "score": results["distances"][0][i] if results.get("distances") else 0,
                "metadata": results["metadatas"][0][i],
            })

        return items

    def get_meeting_context(self, meeting_id: str) -> str:
        """Retrieve all stored context for a meeting."""
        results = self.collection.get(
            ids=[f"{meeting_id}_transcript", f"{meeting_id}_summary"],
        )
        texts = results.get("documents", []) or []
        return "\n\n".join(texts)

    def get_all_meetings(self, limit: int = 50) -> List[dict]:
        """List all meetings with metadata."""
        results = self.collection.get(limit=limit)
        meetings = {}
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i]
            mid = meta.get("meeting_id", "")
            if mid not in meetings:
                meetings[mid] = {
                    "id": mid,
                    "title": meta.get("title", "Untitled"),
                    "recorded_at": meta.get("recorded_at", ""),
                    "snippet": results["documents"][i][:200] if results["documents"] else "",
                }
        return list(meetings.values())
