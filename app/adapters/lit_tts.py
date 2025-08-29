import os
import requests
import io
import base64
from .base import TTSAdapter
from config import config

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LitTTS(TTSAdapter):
    def __init__(self):
        self.api_url = config.lit_tts.api_url
    
    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio using LIT TTS API."""
        try:
            payload = {
                "text": text,
                "voice": "af_sarah"
            }
            
            response = requests.post(
                self.api_url, 
                headers={'Content-Type': 'application/json'}, 
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check if the request was successful
                if result.get("success", False):
                    # Extract audio data
                    audio_data = result.get("audio_data", "")
                    if audio_data:
                        # If audio is base64 encoded
                        if isinstance(audio_data, str):
                            audio_bytes = base64.b64decode(audio_data)
                            return audio_bytes
                        else:
                            return audio_data
                    else:
                        raise Exception("No audio data in successful response")
                else:
                    # Handle error response
                    error_msg = result.get("error", "Unknown error from LIT TTS API")
                    raise Exception(f"LIT TTS API error: {error_msg}")
            else:
                raise Exception(f"LIT TTS API error {response.status_code}: {response.text}")
        
        except Exception as e:
            raise Exception(f"TTS synthesis failed: {str(e)}")