import os
import requests
import tempfile
from .base import STTAdapter

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class HuggingFaceASR(STTAdapter):
    def __init__(self):
        self.api_url = "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3"
        hf_token = os.environ.get('HF_TOKEN')
        if not hf_token:
            raise ValueError("HF_TOKEN environment variable is required")
        self.headers = {
            "Authorization": f"Bearer {hf_token}",
        }
    
    async def transcribe(self, audio_bytes: bytes) -> tuple[str, float]:
        # Write audio to temporary file for API call
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file.flush()
            
            try:
                # Read the audio file and send to HF Inference API
                with open(temp_file.name, "rb") as f:
                    data = f.read()
                
                response = requests.post(
                    self.api_url, 
                    headers={"Content-Type": "audio/flac", **self.headers}, 
                    data=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text", "").strip()
                    confidence = 0.9  # Default confidence for HF Inference API
                    return text, confidence
                else:
                    raise Exception(f"HF Inference API error {response.status_code}: {response.text}")
            
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file.name)
                except:
                    pass