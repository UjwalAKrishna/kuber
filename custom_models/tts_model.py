#!/usr/bin/env python3
"""
Custom TTS Model using Official Kokoro Package with FastAPI
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
import base64
import tempfile
import os
import numpy as np
import soundfile as sf
import torch
import asyncio
import json
import uvicorn
from pydantic import BaseModel
from typing import Optional

# Import Kokoro at the top
try:
    from kokoro import KPipeline
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    print("⚠️  Kokoro not available. Install with: pip install kokoro>=0.9.4")

# Pydantic models for request/response
class TTSRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0
    format: str = "wav"

class TTSResponse(BaseModel):
    success: bool
    audio_data: str = ""
    sample_rate: int = 24000
    duration: float = 0.0
    text: str = ""
    voice: str = ""
    format: str = "wav"
    error: Optional[str] = None

class KokoroTTSService:
    def __init__(self):
        """Initialize the TTS service."""
        print("🚀 Setting up Official Kokoro TTS service...")
        
        if not KOKORO_AVAILABLE:
            raise ImportError("Kokoro library required. Install with: pip install kokoro>=0.9.4 soundfile")
        
        # Set device
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🔧 Using device: {self.device}")
        
        try:
            # Initialize Kokoro pipeline
            self.pipeline = KPipeline(lang_code='a')
            
            # Move to GPU if available
            if torch.cuda.is_available() and hasattr(self.pipeline, 'to'):
                self.pipeline = self.pipeline.to(self.device)
                print(f"✅ Kokoro pipeline moved to {self.device}")
            else:
                print("✅ Kokoro pipeline initialized on CPU")
            
            # Available voices from official Kokoro
            self.available_voices = [
                "af_bella", "af_nicole", "af_sarah", "af_sky", "af_heart",
                "am_adam", "am_michael", "bf_emma", "bf_isabella", 
                "bm_george", "bm_lewis"
            ]
            
            # Create voices dictionary for compatibility
            self.voices = {voice: voice for voice in self.available_voices}
            
            print(f"✅ Available voices: {self.available_voices}")
            
            # TTS settings
            self.sample_rate = 24000  # Kokoro native sample rate
            self.max_text_length = 1000
            self.default_voice = "af_heart"
            
            print("✅ Kokoro TTS setup completed successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize Kokoro: {e}")
            raise e
    
    def synthesize_speech(self, text: str, voice: str = None, speed: float = 1.0):
        """Generate speech using official Kokoro pipeline."""
        try:
            if not voice:
                voice = self.default_voice
            
            # Validate voice
            if voice not in self.available_voices:
                print(f"⚠️  Voice '{voice}' not found, using default '{self.default_voice}'")
                voice = self.default_voice
            
            # Validate text length
            if len(text) > self.max_text_length:
                raise ValueError(f"Text too long. Maximum {self.max_text_length} characters allowed")
            
            print(f"🔊 Kokoro TTS: '{text[:50]}...' with voice '{voice}'")
            
            # Use official Kokoro pipeline exactly like the example
            generator = self.pipeline(text, voice=voice)
            
            # Collect audio chunks exactly like official example
            audio_chunks = []
            for i, (gs, ps, audio) in enumerate(generator):
                print(f"📦 Chunk {i}: gs={gs}, ps={ps}, samples={len(audio)}")
                audio_chunks.append(audio)
            
            # Combine all chunks
            if audio_chunks:
                final_audio = np.concatenate(audio_chunks)
                print(f"✅ Generated {len(final_audio)} samples at 24kHz")
            else:
                raise Exception("No audio generated")
            
            # Convert to WAV and encode
            audio_bytes = self._audio_to_wav_bytes(final_audio, self.sample_rate)
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            return TTSResponse(
                success=True,
                audio_data=audio_b64,
                sample_rate=self.sample_rate,
                duration=len(final_audio) / self.sample_rate,
                text=text,
                voice=voice,
                format="wav"
            )
            
        except Exception as e:
            print(f"❌ Kokoro failed: {e}")
            return TTSResponse(
                success=False,
                error=str(e),
                text=text,
                voice=voice
            )
    
    async def synthesize_speech_streaming(self, text: str, voice: str = None):
        """Generate speech with streaming chunks using official Kokoro pipeline."""
        try:
            if not voice:
                voice = self.default_voice
            
            # Validate voice
            if voice not in self.available_voices:
                print(f"⚠️  Voice '{voice}' not found, using default '{self.default_voice}'")
                voice = self.default_voice
            
            # Validate text length
            if len(text) > self.max_text_length:
                raise ValueError(f"Text too long. Maximum {self.max_text_length} characters allowed")
            
            print(f"🔊 Streaming Kokoro TTS: '{text[:50]}...' with voice '{voice}'")
            
            # Use official Kokoro pipeline
            generator = self.pipeline(text, voice=voice)
            
            # Stream audio chunks as they are generated
            audio_chunks = []
            chunk_count = 0
            
            for i, (gs, ps, audio) in enumerate(generator):
                print(f"📦 Streaming chunk {i}: gs={gs}, ps={ps}, samples={len(audio)}")
                audio_chunks.append(audio)
                chunk_count += 1
                
                # Convert chunk to WAV and encode
                chunk_wav = self._audio_to_wav_bytes(audio, self.sample_rate)
                chunk_b64 = base64.b64encode(chunk_wav).decode('utf-8')
                
                # Yield individual audio chunk
                yield {
                    "type": "audio_chunk",
                    "audio_data": chunk_b64,
                    "chunk_index": i,
                    "samples": len(audio),
                    "duration": len(audio) / self.sample_rate,
                    "gs": gs,
                    "ps": ps,
                    "format": "wav"
                }
                
                # Small delay for streaming effect
                await asyncio.sleep(0.05)
            
            # Combine all chunks for final result
            if audio_chunks:
                final_audio = np.concatenate(audio_chunks)
                print(f"✅ Streaming complete: {len(final_audio)} samples at 24kHz")
                
                # Convert final audio to WAV
                final_wav = self._audio_to_wav_bytes(final_audio, self.sample_rate)
                final_b64 = base64.b64encode(final_wav).decode('utf-8')
                
                # Yield final complete audio
                yield {
                    "type": "complete",
                    "audio_data": final_b64,
                    "sample_rate": self.sample_rate,
                    "duration": len(final_audio) / self.sample_rate,
                    "text": text,
                    "voice": voice,
                    "total_chunks": chunk_count,
                    "total_samples": len(final_audio),
                    "format": "wav"
                }
            else:
                yield {
                    "type": "error",
                    "error": "No audio chunks generated"
                }
                
        except Exception as e:
            print(f"❌ Streaming Kokoro failed: {e}")
            yield {
                "type": "error",
                "error": f"TTS streaming failed: {str(e)}"
            }
    
    
    def _audio_to_wav_bytes(self, audio_array, sample_rate):
        """Convert audio array to WAV bytes."""
        try:
            # Ensure we have valid audio data
            if len(audio_array) == 0:
                print("⚠️  Empty audio in WAV conversion, generating test tone")
                audio_array = np.sin(2 * np.pi * 440 * np.linspace(0, 1, sample_rate)) * 0.3
            
            # Ensure audio is in valid range
            if np.abs(audio_array).max() > 1.0:
                audio_array = audio_array / np.abs(audio_array).max()
            
            print(f"🎵 Converting to WAV: {len(audio_array)} samples, range [{audio_array.min():.3f}, {audio_array.max():.3f}]")
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                # Write WAV file
                sf.write(temp_file.name, audio_array, sample_rate, subtype='PCM_16')
                
                # Read back as bytes
                with open(temp_file.name, 'rb') as f:
                    wav_bytes = f.read()
                
                # Clean up
                os.unlink(temp_file.name)
                
                print(f"✅ WAV file created: {len(wav_bytes)} bytes")
                return wav_bytes
                
        except Exception as e:
            print(f"❌ WAV conversion failed: {e}")
            raise ValueError(f"Failed to convert audio to WAV: {str(e)}")
    
    def get_available_voices(self):
        """Get list of available voices."""
        return self.available_voices if hasattr(self, 'available_voices') else []

# Initialize the TTS service
tts_service = KokoroTTSService()

# Create FastAPI app
app = FastAPI(title="TTS Service", description="Text-to-Speech API with HTTP and WebSocket support")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "TTS", "model": "kokoro-82M"}

@app.get("/voices")
async def get_voices():
    """Get available voices."""
    return {"voices": tts_service.get_available_voices()}

@app.post("/predict", response_model=TTSResponse)
async def synthesize_endpoint(request: TTSRequest):
    """HTTP endpoint for text-to-speech synthesis."""
    try:
        result = tts_service.synthesize_speech(
            text=request.text,
            voice=request.voice,
            speed=request.speed
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time text-to-speech streaming."""
    await websocket.accept()
    print("🔌 TTS WebSocket connection established")
    
    try:
        while True:
            # Receive text data
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "synthesize":
                # Process text for synthesis
                text = message.get("text", "")
                voice = message.get("voice", tts_service.default_voice)
                
                if text:
                    # Send processing status
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": f"Starting TTS generation with voice '{voice}'",
                        "text_length": len(text),
                        "voice": voice
                    }))
                    
                    # Stream synthesis results
                    async for chunk in tts_service.synthesize_speech_streaming(text, voice):
                        await websocket.send_text(json.dumps(chunk))
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "No text provided"
                    }))
            
            elif message.get("type") == "ping":
                # Respond to ping
                await websocket.send_text(json.dumps({
                    "type": "pong"
                }))
            
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Unknown message type"
                }))
                
    except WebSocketDisconnect:
        print("🔌 TTS WebSocket connection closed")
    except Exception as e:
        print(f"❌ TTS WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting TTS Service with FastAPI...")
    print("📡 Endpoints:")
    print("   POST http://localhost:8002/predict - HTTP TTS")
    print("   WS   ws://localhost:8002/ws - WebSocket TTS")
    print("   GET  http://localhost:8002/voices - Available voices")
    print("   GET  http://localhost:8002/health - Health check")
    
    uvicorn.run(app, host="0.0.0.0", port=8002)