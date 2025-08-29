#!/usr/bin/env python3
"""
Custom STT Model using Whisper with FastAPI
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
import whisper
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

# Pydantic models for request/response
class STTRequest(BaseModel):
    audio_data: str
    format: str = "wav"
    language: Optional[str] = None
    task: str = "transcribe"

class STTResponse(BaseModel):
    success: bool
    transcription: str = ""
    language: str = "unknown"
    confidence: float = 0.0
    duration: float = 0.0
    segments: list = []
    error: Optional[str] = None

class WhisperSTTService:
    def __init__(self):
        """Initialize the STT service."""
        print("🚀 Setting up Custom STT service...")
        
        # Load Whisper model - using 'base' for better speed/accuracy balance
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = whisper.load_model("base", device=self.device)
        
        print(f"✅ Whisper model loaded on {self.device}")
        
        # Audio processing settings
        self.sample_rate = 16000
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
        
    def transcribe_audio(self, audio_data: str, format: str = "wav", language: str = None, task: str = "transcribe"):
        """Process audio and return transcription."""
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            audio_array = self._process_audio_bytes(audio_bytes)
            
            # Transcription options
            options = {
                "language": language,
                "task": task,
                "fp16": torch.cuda.is_available(),  # Use FP16 on GPU for speed
                "verbose": False
            }
            
            # Remove None values
            options = {k: v for k, v in options.items() if v is not None}
            
            # Perform transcription
            result = self.model.transcribe(audio_array, **options)
            
            return STTResponse(
                success=True,
                transcription=result["text"].strip(),
                language=result.get("language", "unknown"),
                segments=result.get("segments", []),
                confidence=self._calculate_avg_confidence(result.get("segments", [])),
                duration=len(audio_array) / self.sample_rate
            )
            
        except Exception as e:
            return STTResponse(
                success=False,
                error=str(e)
            )
    
    def _process_audio_bytes(self, audio_bytes):
        """Convert audio bytes to numpy array."""
        try:
            # Create temporary file to process audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file.flush()
                
                # Load audio using soundfile
                audio_array, sr = sf.read(temp_file.name)
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                # Convert to mono if stereo
                if len(audio_array.shape) > 1:
                    audio_array = np.mean(audio_array, axis=1)
                
                # Resample if needed
                if sr != self.sample_rate:
                    audio_array = self._resample_audio(audio_array, sr, self.sample_rate)
                
                # Normalize audio
                audio_array = audio_array.astype(np.float32)
                
                return audio_array
                
        except Exception as e:
            raise ValueError(f"Failed to process audio bytes: {str(e)}")
    
    def _process_audio_file(self, audio_path):
        """Process audio file and return numpy array."""
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Load audio using soundfile
            audio_array, sr = sf.read(audio_path)
            
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Resample if needed
            if sr != self.sample_rate:
                audio_array = self._resample_audio(audio_array, sr, self.sample_rate)
            
            # Normalize audio
            audio_array = audio_array.astype(np.float32)
            
            return audio_array
            
        except Exception as e:
            raise ValueError(f"Failed to process audio file: {str(e)}")
    
    def _resample_audio(self, audio, orig_sr, target_sr):
        """Resample audio to target sample rate."""
        try:
            import librosa
            return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
        except ImportError:
            # Fallback: simple resampling (not ideal but works)
            ratio = target_sr / orig_sr
            new_length = int(len(audio) * ratio)
            return np.interp(np.linspace(0, len(audio), new_length), np.arange(len(audio)), audio)
    
    def _calculate_avg_confidence(self, segments):
        """Calculate average confidence from segments."""
        if not segments:
            return 0.0
        
        # Whisper doesn't always provide confidence scores
        # This is a placeholder for when they're available
        confidences = []
        for segment in segments:
            if 'confidence' in segment:
                confidences.append(segment['confidence'])
            elif 'avg_logprob' in segment:
                # Convert log probability to confidence-like score
                confidences.append(max(0.0, min(1.0, np.exp(segment['avg_logprob']))))
        
        return np.mean(confidences) if confidences else 0.8  # Default confidence

# Initialize the STT service
stt_service = WhisperSTTService()

# Create FastAPI app
app = FastAPI(title="STT Service", description="Speech-to-Text API with HTTP and WebSocket support")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "STT", "model": "whisper-base"}

@app.post("/predict", response_model=STTResponse)
async def transcribe_endpoint(request: STTRequest):
    """HTTP endpoint for speech-to-text transcription."""
    try:
        result = stt_service.transcribe_audio(
            audio_data=request.audio_data,
            format=request.format,
            language=request.language,
            task=request.task
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time speech-to-text."""
    await websocket.accept()
    print("🔌 WebSocket connection established")
    
    try:
        while True:
            # Receive audio data
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "audio":
                # Process audio chunk
                audio_data = message.get("audio_data", "")
                language = message.get("language")
                task = message.get("task", "transcribe")
                
                if audio_data:
                    # Send processing status
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": "Processing audio..."
                    }))
                    
                    # Transcribe audio
                    result = stt_service.transcribe_audio(
                        audio_data=audio_data,
                        language=language,
                        task=task
                    )
                    
                    # Send result
                    response = {
                        "type": "result",
                        "success": result.success,
                        "transcription": result.transcription,
                        "language": result.language,
                        "confidence": result.confidence,
                        "duration": result.duration
                    }
                    
                    if result.error:
                        response["error"] = result.error
                    
                    await websocket.send_text(json.dumps(response))
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "No audio data provided"
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
        print("🔌 WebSocket connection closed")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting STT Service with FastAPI...")
    print("📡 Endpoints:")
    print("   POST http://localhost:8001/predict - HTTP STT")
    print("   WS   ws://localhost:8001/ws - WebSocket STT")
    print("   GET  http://localhost:8001/health - Health check")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)