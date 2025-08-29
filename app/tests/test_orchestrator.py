import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from orchestrator import VoiceOrchestrator
from adapters.base import STTAdapter, LLMAdapter, TTSAdapter, LLMResult


class MockSTTAdapter(STTAdapter):
    async def transcribe(self, audio_bytes: bytes) -> tuple[str, float]:
        return "Hello, how can I help you?", 0.95


class MockLLMAdapter(LLMAdapter):
    async def generate(self, prompt: str, functions=None) -> LLMResult:
        if "gold" in prompt.lower():
            return LLMResult(
                text="I can help you with gold investments.",
                function_call={"name": "suggest_gold_investment", "arguments": {}}
            )
        return LLMResult(text="I'm here to help you with your questions.")


class MockTTSAdapter(TTSAdapter):
    async def synthesize(self, text: str) -> bytes:
        # Return dummy WAV header + some data
        return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 20


@pytest.fixture
def mock_orchestrator():
    orchestrator = VoiceOrchestrator()
    orchestrator.stt_adapter = MockSTTAdapter()
    orchestrator.llm_adapter = MockLLMAdapter()
    orchestrator.tts_adapter = MockTTSAdapter()
    return orchestrator


@pytest.mark.asyncio
async def test_process_voice_query_basic(mock_orchestrator):
    """Test basic voice query processing."""
    # Dummy audio bytes
    audio_bytes = b"fake_audio_data"
    
    result = await mock_orchestrator.process_voice_query(audio_bytes)
    
    assert "request_id" in result
    assert result["transcript"] == "Hello, how can I help you?"
    assert result["llm_text"] == "I'm here to help you with your questions."
    assert "audio_b64" in result
    assert "timings" in result
    assert "stt_ms" in result["timings"]
    assert "llm_ms" in result["timings"]
    assert "tts_ms" in result["timings"]
    assert "total_ms" in result["timings"]


@pytest.mark.asyncio
async def test_process_voice_query_with_gold_nudge(mock_orchestrator):
    """Test voice query with gold investment nudge."""
    # Mock the LLM to return gold-related response
    mock_orchestrator.llm_adapter = MockLLMAdapter()
    
    # Create audio that will trigger gold response
    audio_bytes = b"fake_audio_data"
    
    # Mock the STT to return gold-related transcript
    async def mock_transcribe(audio_bytes):
        return "Tell me about gold investments", 0.95
    
    mock_orchestrator.stt_adapter.transcribe = mock_transcribe
    
    result = await mock_orchestrator.process_voice_query(
        audio_bytes, 
        session_id="test_session"
    )
    
    assert "gold" in result["llm_text"].lower()
    # Should include nudge message
    assert "digital gold on Simplify" in result["llm_text"]


@pytest.mark.asyncio
async def test_process_voice_query_timings(mock_orchestrator):
    """Test that timing measurements are reasonable."""
    audio_bytes = b"fake_audio_data"
    
    result = await mock_orchestrator.process_voice_query(audio_bytes)
    
    timings = result["timings"]
    
    # All timings should be positive
    assert timings["stt_ms"] >= 0
    assert timings["llm_ms"] >= 0
    assert timings["tts_ms"] >= 0
    assert timings["total_ms"] >= 0
    
    # Total should be at least the sum of components (allowing for small overhead)
    component_sum = timings["stt_ms"] + timings["llm_ms"] + timings["tts_ms"]
    assert timings["total_ms"] >= component_sum * 0.9  # Allow 10% overhead


@pytest.mark.asyncio
async def test_process_voice_query_with_session_id(mock_orchestrator):
    """Test voice query with session ID."""
    audio_bytes = b"fake_audio_data"
    session_id = "test_session_123"
    
    result = await mock_orchestrator.process_voice_query(
        audio_bytes, 
        session_id=session_id
    )
    
    assert session_id in result["request_id"]