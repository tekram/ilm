from __future__ import annotations

from typing import Iterable, List, Optional
import os
import re
import time
from urllib.parse import urlparse, urlunparse

from .config import LlmConfig


class LlmSummarizer:
    def __init__(self, provider: str) -> None:
        self.provider = provider
        self._openai = None
        self._openai_model: Optional[str] = None
        self._gemini = None
        self._gemini_model: Optional[str] = None
        self._ollama_host: Optional[str] = None
        self._ollama_model: Optional[str] = None

    @classmethod
    def from_config(cls, cfg: LlmConfig) -> "LlmSummarizer":
        inst = cls(cfg.provider)
        if cfg.provider == "openai":
            from openai import OpenAI

            inst._openai = OpenAI(api_key=cfg.openai_api_key)
            inst._openai_model = cfg.openai_model
        elif cfg.provider == "gemini":
            import google.generativeai as genai

            genai.configure(api_key=cfg.gemini_api_key)
            inst._gemini = genai.GenerativeModel(cfg.gemini_model)
            inst._gemini_model = cfg.gemini_model
        elif cfg.provider == "ollama":
            # lazily import when used
            inst._ollama_host = cfg.ollama_host or "http://localhost:11434"
            inst._ollama_model = cfg.ollama_model
        else:
            raise ValueError(f"Unsupported LLM provider: {cfg.provider}")
        return inst

    def summarize(self, title: str, transcript: str) -> str:
        chunks = _chunk_text(transcript, max_chars=8000)
        partials: List[str] = []
        for idx, chunk in enumerate(chunks):
            prompt = _build_chunk_prompt(title, idx + 1, len(chunks), chunk)
            content = self._chat(prompt)
            partials.append(content)
        if len(partials) == 1:
            return partials[0]
        merge_prompt = _build_merge_prompt(title, partials)
        return self._chat(merge_prompt)

    def generate_short_title(self, transcript: str) -> str:
        """Generate a short, descriptive title from the transcript content."""
        # Take first chunk of transcript for title generation
        sample = transcript[:2000] if len(transcript) > 2000 else transcript
        prompt = _build_title_prompt(sample)
        title = self._chat(prompt).strip()
        
        # Clean up the response - remove HTML tags, quotes, extra punctuation
        title = re.sub(r'<[^>]+>', '', title)  # Remove HTML tags
        title = title.strip('"\'').strip()
        title = re.sub(r'^(Title:|Summary:|Topic:)\s*', '', title, flags=re.IGNORECASE)  # Remove common prefixes
        title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
        
        # Limit length and ensure it's reasonable
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title if title else "Islamic Law Lesson"

    def _chat(self, user_prompt: str) -> str:
        if self.provider == "openai":
            resp = self._openai.chat.completions.create(
                model=self._openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a concise, domain-aware meeting summarizer. The lessons are in Arabic on Islamic law (fiqh). "
                            "Translate and summarize into clear English. Output ONLY clean Markdown text - no HTML tags, no DOCTYPE, no <html> tags. "
                            "Use ## for main headings, ### for subheadings, - for bullet points. Emphasize key rulings, definitions, evidences "
                            "(Qur'an and hadith with brief citations if present), differences of opinion, and practical action items."
                        ),
                    },
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""

        if self.provider == "gemini":
            # Gemini uses a single string prompt
            prompt = (
                "You are a concise, domain-aware meeting summarizer. The lessons are in Arabic on Islamic law (fiqh). "
                "Translate and summarize into clear English. Output ONLY clean Markdown text - no HTML tags, no DOCTYPE, no <html> tags. "
                "Use ## for main headings, ### for subheadings, - for bullet points. Emphasize key rulings, definitions, evidences "
                "(Qur'an and hadith with brief citations if present), differences of opinion, and practical action items.\n\n" + user_prompt
            )
            resp = self._gemini.generate_content(prompt)
            return (getattr(resp, "text", None) or "").strip()

        if self.provider == "ollama":
            import requests

            base = _normalize_ollama_host(self._ollama_host)
            url = base.rstrip("/") + "/api/chat"
            timeout_s = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))
            num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))
            payload = {
                "model": self._ollama_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a concise, domain-aware meeting summarizer. The lessons are in Arabic on Islamic law (fiqh). "
                            "Translate and summarize into clear English. Output ONLY clean Markdown text - no HTML tags, no DOCTYPE, no <html> tags. "
                            "Use ## for main headings, ### for subheadings, - for bullet points. Emphasize key rulings, definitions, evidences "
                            "(Qur'an and hadith with brief citations if present), differences of opinion, and practical action items."
                        ),
                    },
                    {"role": "user", "content": user_prompt},
                ],
                "options": {"temperature": 0.2, "num_predict": num_predict},
                "stream": False,
                "keep_alive": "5m",
            }

            last_exc = None
            for attempt in range(3):
                try:
                    resp = requests.post(url, json=payload, timeout=timeout_s)
                    resp.raise_for_status()
                    data = resp.json()
                    return (data.get("message") or {}).get("content", "")
                except requests.exceptions.ReadTimeout as e:
                    last_exc = e
                except requests.exceptions.ConnectionError as e:
                    last_exc = e
                # backoff before retry
                time.sleep(2 * (attempt + 1))
            # if we get here, retries exhausted
            raise last_exc if last_exc else RuntimeError("Unknown error calling Ollama")
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

def _normalize_ollama_host(host: Optional[str]) -> str:
    base = host or "http://127.0.0.1:11434"
    if not re.match(r"^https?://", base, re.IGNORECASE):
        base = "http://" + base
    parsed = urlparse(base)
    netloc = parsed.netloc or parsed.path
    # Replace 0.0.0.0 with loopback
    netloc = netloc.replace("0.0.0.0", "127.0.0.1")
    if ":" not in netloc:
        netloc = f"{netloc}:11434"
    return urlunparse((parsed.scheme or "http", netloc, "", "", "", ""))


def _chunk_text(text: str, max_chars: int) -> List[str]:
    text = text.replace("\r\n", "\n")
    if len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        # try to break on paragraph
        split_at = text.rfind("\n\n", start, end)
        if split_at == -1 or split_at <= start + 1000:
            split_at = text.rfind("\n", start, end)
        if split_at == -1 or split_at <= start + 1000:
            split_at = end
        chunk = text[start:split_at]
        chunks.append(chunk)
        start = split_at
    return chunks


def _build_chunk_prompt(title: str, idx: int, total: int, chunk: str) -> str:
    header = (
        f"Meeting: {title}\n"
        f"Part {idx}/{total} of an Arabic lesson transcript follows. Translate and summarize into English, emphasizing key rulings, definitions, evidences (Qur'an/hadith), differences of opinion, and practical action items."
    )
    return f"{header}\n\nTranscript:\n\n{chunk}"


def _build_merge_prompt(title: str, partials: Iterable[str]) -> str:
    bullets = "\n\n".join(partials)
    return (
        f"Meeting: {title}. Merge the following partial summaries (from Arabic lessons) into one cohesive, non-redundant English summary. "
        f"Emphasize key rulings, definitions, evidences (Qur'an/hadith), differences of opinion, and practical action items. "
        f"Use clear headings and bullet points.\n\n{bullets}"
    )


def _build_title_prompt(transcript_sample: str) -> str:
    return (
        f"Based on this Arabic Islamic law (fiqh) lesson transcript, generate a short, descriptive title in English (3-6 words max). "
        f"Focus on the main topic being discussed. Examples: 'Zakat Rules', 'Prayer Conditions', 'Marriage Laws', 'Business Ethics'. "
        f"Return ONLY the plain text title with no HTML tags, no quotes, no prefixes like 'Title:'. Just the topic words.\n\nTranscript sample:\n\n{transcript_sample}"
    )


