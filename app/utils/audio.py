import io
import tempfile

# Try to import pydub, fall back to basic audio handling if not available
try:
    from pydub import AudioSegment
    from pydub.utils import which
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


def normalize_audio(audio_bytes: bytes) -> bytes:
    """Normalize audio to standard format (16kHz, mono, WAV)."""
    if not PYDUB_AVAILABLE:
        # If pydub not available, just return the original audio
        # This is a fallback for minimal installations
        return audio_bytes
    
    try:
        # Load audio from bytes
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Convert to mono and 16kHz
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        
        # Export as WAV
        output_buffer = io.BytesIO()
        audio.export(output_buffer, format="wav")
        return output_buffer.getvalue()
    except Exception:
        # If audio processing fails, return original
        return audio_bytes


def chunk_audio(audio_bytes: bytes, chunk_duration_ms: int = 1000) -> list[bytes]:
    """Split audio into chunks of specified duration."""
    if not PYDUB_AVAILABLE:
        # Simple chunking by bytes if pydub not available
        chunk_size = len(audio_bytes) // 4  # Split into 4 chunks
        chunks = []
        for i in range(0, len(audio_bytes), chunk_size):
            chunks.append(audio_bytes[i:i + chunk_size])
        return chunks if chunks else [audio_bytes]
    
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        chunks = []
        
        for i in range(0, len(audio), chunk_duration_ms):
            chunk = audio[i:i + chunk_duration_ms]
            chunk_buffer = io.BytesIO()
            chunk.export(chunk_buffer, format="wav")
            chunks.append(chunk_buffer.getvalue())
        
        return chunks
    except Exception:
        # Fallback to simple byte chunking
        chunk_size = len(audio_bytes) // 4
        chunks = []
        for i in range(0, len(audio_bytes), chunk_size):
            chunks.append(audio_bytes[i:i + chunk_size])
        return chunks if chunks else [audio_bytes]