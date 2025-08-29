import os
import requests
import io
import numpy as np
import wave
from .base import TTSAdapter

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class HuggingFaceTTS(TTSAdapter):
    def __init__(self):
        self.api_url = "https://router.huggingface.co/fal-ai/fal-ai/kokoro/american-english"
        hf_token = os.environ.get('HF_TOKEN')
        if not hf_token:
            raise ValueError("HF_TOKEN environment variable is required")
        self.headers = {
            "Authorization": f"Bearer {hf_token}",
        }

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio using HuggingFace Inference API."""
        try:
            payload = {"text": text}
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                audio_data = result.get("audio")
                sampling_rate = result.get("sampling_rate", 22050)
                
                if audio_data:
                    # Convert audio data to bytes (assuming it's a numpy array or list)
                    if isinstance(audio_data, list):
                        audio_array = np.array(audio_data, dtype=np.float32)
                    elif isinstance(audio_data, dict):
                        # Handle case where audio_data might be a dict with nested data
                        raise Exception(f"Unexpected audio data format: {type(audio_data)}. Expected list or array.")
                    else:
                        audio_array = np.array(audio_data, dtype=np.float32)
                    
                    # Convert to WAV format bytes
                    return self._array_to_wav_bytes(audio_array, sampling_rate)
                else:
                    raise Exception("No audio data received from API")
            else:
                raise Exception(f"HF Inference API error {response.status_code}: {response.text}")
        
        except Exception as e:
            raise Exception(f"TTS synthesis failed: {str(e)}")
    
    def _array_to_wav_bytes(self, audio_array: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy array to WAV bytes."""
        # Normalize audio to 16-bit range
        if audio_array.dtype != np.int16:
            audio_array = (audio_array * 32767).astype(np.int16)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_array.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.read()