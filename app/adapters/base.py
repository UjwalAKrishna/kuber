from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    function_call: Optional[Dict[str, Any]] = None
    confidence: float = 1.0


class STTAdapter(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> tuple[str, float]:
        """Transcribe audio bytes to text with confidence score."""
        pass
    
    async def stream_transcribe(self, chunks: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Optional streaming transcription."""
        raise NotImplementedError("Streaming transcription not implemented")


class LLMAdapter(ABC):
    @abstractmethod
    async def generate(self, prompt: str, functions: Optional[List[dict]] = None) -> LLMResult:
        """Generate text response with optional function calling support."""
        pass


class TTSAdapter(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio bytes (WAV format)."""
        pass
    
    async def stream_synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Optional streaming synthesis."""
        raise NotImplementedError("Streaming synthesis not implemented")