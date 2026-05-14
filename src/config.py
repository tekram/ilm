import os
from dataclasses import dataclass
from typing import Dict, List
from dotenv import load_dotenv


load_dotenv()


@dataclass
class MeetingTypeConfig:
    """Configuration for a specific meeting type"""
    name: str
    display_name: str
    description: str
    source_dir: str  # relative to recordings/
    output_dir: str  # relative to docs/
    topics: List[str] = None  # optional topic filters


@dataclass
class ZoomConfig:
    access_token: str
    host_email: str | None


@dataclass
class LlmConfig:
    provider: str
    # OpenAI
    openai_api_key: str | None
    openai_model: str
    # Gemini
    gemini_api_key: str | None
    gemini_model: str
    # Ollama
    ollama_model: str
    ollama_host: str | None


@dataclass
class LocalConfig:
    directory: str | None


@dataclass
class AppConfig:
    zoom: ZoomConfig
    llm: LlmConfig
    local: LocalConfig
    docs_dir: str
    meetings_dir: str  # legacy - kept for compatibility
    templates_dir: str
    meeting_types: Dict[str, MeetingTypeConfig]


def load_config() -> AppConfig:
    zoom = ZoomConfig(
        access_token=os.getenv("ZOOM_ACCESS_TOKEN", ""),
        host_email=os.getenv("ZOOM_HOST_EMAIL"),
    )

    llm = LlmConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "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"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
    )

    local = LocalConfig(
        directory=os.getenv("LOCAL_TRANSCRIPTS_DIR"),
    )

    docs_dir = os.path.join(os.getcwd(), "docs")
    meetings_dir = os.path.join(docs_dir, "meetings")  # legacy
    templates_dir = os.path.join(os.getcwd(), "templates")
    
    # Define meeting types
    meeting_types = {
        "tuhfa-al-muhtaaj": MeetingTypeConfig(
            name="tuhfa-al-muhtaaj",
            display_name="Tuhfa Al-Muhtaaj",
            description="Islamic jurisprudence lessons from Tuhfa Al-Muhtaaj",
            source_dir="tuhfa-al-muhtaaj",
            output_dir="tuhfa-al-muhtaaj"
        ),
        "manthoma": MeetingTypeConfig(
            name="manthoma",
            display_name="Manthoma",
            description="Manthoma lessons",
            source_dir="manthoma", 
            output_dir="manthoma"
        ),
        "majma-al-fatawa-bilhind": MeetingTypeConfig(
            name="majma-al-fatawa-bilhind",
            display_name="Majma Al-Fatawa Bilhind",
            description="Majma Al-Fatawa Bilhind sessions",
            source_dir="majma-al-fatawa-bilhind",
            output_dir="majma-al-fatawa-bilhind"
        )
    }

    return AppConfig(
        zoom=zoom,
        llm=llm,
        local=local,
        docs_dir=docs_dir,
        meetings_dir=meetings_dir,
        templates_dir=templates_dir,
        meeting_types=meeting_types,
    )


