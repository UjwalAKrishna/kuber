import os
import requests
import base64
from .base import STTAdapter
from config import config

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LitSTT(STTAdapter):
    def __init__(self):
        self.api_url = config.lit_stt.api_url
    
    async def transcribe(self, audio_bytes: bytes) -> tuple[str, float]:
        try:
            # Convert audio bytes to base64
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Prepare payload
            payload = {
                "audio_data": audio_b64,
                "format": "wav",
                "language": "en",
                "task": "transcribe"
            }
            
            # Send POST request to LIT STT API
            response = requests.post(self.api_url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    text = result.get("transcription", "").strip()
                    confidence = result.get("confidence", 0.9)
                    return text, confidence
                else:
                    raise Exception("LIT STT API returned success=False")
            else:
                raise Exception(f"LIT STT API error {response.status_code}: {response.text}")
        
        except Exception as e:
            raise Exception(f"STT transcription failed: {str(e)}")