import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


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
    meetings_dir: str
    templates_dir: str


def load_config() -> AppConfig:
    zoom = ZoomConfig(
        access_token=os.getenv("ZOOM_ACCESS_TOKEN", ""),
        host_email=os.getenv("ZOOM_HOST_EMAIL"),
    )

    llm = LlmConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
    )

    local = LocalConfig(
        directory=os.getenv("LOCAL_TRANSCRIPTS_DIR"),
    )

    docs_dir = os.path.join(os.getcwd(), "docs")
    meetings_dir = os.path.join(docs_dir, "meetings")
    templates_dir = os.path.join(os.getcwd(), "templates")

    return AppConfig(
        zoom=zoom,
        llm=llm,
        local=local,
        docs_dir=docs_dir,
        meetings_dir=meetings_dir,
        templates_dir=templates_dir,
    )


