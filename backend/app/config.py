from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "VoxMind"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # LLM
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # Whisper
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # Storage
    upload_dir: str = "./uploads"
    chroma_persist_dir: str = "./chromadb"
    max_file_size_mb: int = 500

    # IM Push (Feishu / Webhook)
    feishu_webhook_url: str = ""
    auto_push_meetings: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
