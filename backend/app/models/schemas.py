from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AudioUploadResponse(BaseModel):
    id: str
    status: str = "queued"
    estimated_time_sec: int = 0


class SpeakerSegment(BaseModel):
    start: float
    end: float
    speaker: str
    text: str


class Summary(BaseModel):
    topics: List[str] = []
    key_points: List[str] = []
    action_items: List[dict] = []
    full_text: str = ""


class AudioDetail(BaseModel):
    id: str
    title: str
    duration_sec: float
    recorded_at: Optional[str] = None
    status: str
    transcript: Optional[str] = None
    summary: Optional[Summary] = None
    speakers: List[str] = []
    segments: List[SpeakerSegment] = []


class SearchResult(BaseModel):
    id: str
    title: str
    relevance_score: float
    summary_snippet: str
    recorded_at: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    filters: Optional[dict] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict] = []


class DeviceRegisterRequest(BaseModel):
    device_id: str
    name: str


class DeviceRegisterResponse(BaseModel):
    device_key: str
    api_endpoint: str
