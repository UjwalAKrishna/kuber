import pytest
import asyncio
import json
import base64
from httpx import AsyncClient
from main import app
from utils.caching import voice_cache


@pytest.fixture
def sample_audio_bytes():
    """Create sample audio bytes for testing."""
    # Simple WAV header + minimal data
    wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    return wav_header + b"\x00" * 100


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_providers_endpoint():
    """Test providers listing endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/providers")
        assert response.status_code == 200
        data = response.json()
        
        assert "stt_providers" in data
        assert "llm_providers" in data
        assert "tts_providers" in data
        assert "current_config" in data
        
        assert "whisper" in data["stt_providers"]
        assert "hf_local" in data["llm_providers"]
        assert "coqui" in data["tts_providers"]


@pytest.mark.asyncio
async def test_config_endpoint():
    """Test configuration endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "providers" in data
        assert "server" in data
        assert "nudge" in data


@pytest.mark.asyncio
async def test_cache_endpoints():
    """Test cache management endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test cache stats
        response = await client.get("/v1/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        
        # Test cache clear
        response = await client.post("/v1/cache/clear")
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Test cache cleanup
        response = await client.post("/v1/cache/cleanup")
        assert response.status_code == 200
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_voice_query_invalid_audio():
    """Test voice query with invalid audio."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with non-audio file
        files = {"audio": ("test.txt", b"not audio data", "text/plain")}
        response = await client.post("/v1/voice/query", files=files)
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == True
        assert "Invalid audio file format" in data["message"]


@pytest.mark.asyncio
async def test_voice_query_empty_audio():
    """Test voice query with empty audio."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with empty audio file
        files = {"audio": ("test.wav", b"", "audio/wav")}
        response = await client.post("/v1/voice/query", files=files)
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == True
        assert "Empty audio file" in data["message"]


@pytest.fixture(autouse=True)
async def cleanup_cache():
    """Clean up cache after each test."""
    yield
    voice_cache.clear()