#!/usr/bin/env python3
"""
Main server for custom STT and TTS FastAPI services
"""

import uvicorn
import threading
import time
import asyncio
from multiprocessing import Process

def run_stt_server():
    """Run STT FastAPI server on port 8001"""
    print("🎙️  Starting STT FastAPI Service...")
    from stt_model import app as stt_app
    uvicorn.run(stt_app, host="0.0.0.0", port=8001, log_level="info")

def run_tts_server():
    """Run TTS FastAPI server on port 8002"""
    print("🔊 Starting TTS FastAPI Service...")
    from tts_model import app as tts_app
    uvicorn.run(tts_app, host="0.0.0.0", port=8002, log_level="info")

def main():
    print("🎙️🔊 Starting Custom STT + TTS FastAPI Services...")
    print("="*60)
    
    # Start STT server in a separate process
    stt_process = Process(target=run_stt_server, daemon=True)
    stt_process.start()
    
    # Give STT server time to start
    time.sleep(3)
    
    print("\n📡 Available Endpoints:")
    print("   🎙️  STT Service (port 8001):")
    print("      POST http://localhost:8001/predict - HTTP STT")
    print("      WS   ws://localhost:8001/ws - WebSocket STT")
    print("      GET  http://localhost:8001/health - Health check")
    
    print("\n   🔊 TTS Service (port 8002):")
    print("      POST http://localhost:8002/predict - HTTP TTS")
    print("      WS   ws://localhost:8002/ws - WebSocket TTS")
    print("      GET  http://localhost:8002/voices - Available voices")
    print("      GET  http://localhost:8002/health - Health check")
    
    print("\n💡 HTTP Usage Examples:")
    print("   # STT Test:")
    print("   curl -X POST http://localhost:8001/predict \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"audio_data\": \"base64_audio\", \"format\": \"wav\"}'")
    
    print("\n   # TTS Test:")
    print("   curl -X POST http://localhost:8002/predict \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"text\": \"Hello world\", \"voice\": \"af_heart\"}'")
    
    print("\n🌊 WebSocket Usage:")
    print("   # STT WebSocket:")
    print("   ws://localhost:8001/ws")
    print("   Send: {\"type\": \"audio\", \"audio_data\": \"base64_audio\"}")
    
    print("\n   # TTS WebSocket:")
    print("   ws://localhost:8002/ws")
    print("   Send: {\"type\": \"synthesize\", \"text\": \"Hello\", \"voice\": \"af_heart\"}")
    
    print("\n🧪 Testing:")
    print("   python test_api.py --test all")
    print("   python test_streaming.py --test all")
    
    print("\n✨ Features:")
    print("   🎙️  STT: Whisper base model (16kHz)")
    print("   🔊 TTS: Kokoro-82M model (24kHz)")
    print("   ⚡ GPU acceleration (if available)")
    print("   📦 Base64 audio input/output")
    print("   🌊 WebSocket real-time streaming")
    print("   🎭 Multiple Kokoro voices available")
    
    print("\n🔄 Both services running simultaneously...")
    
    try:
        # Start TTS server in main thread (this will block)
        run_tts_server()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        stt_process.terminate()
        stt_process.join()
        print("✅ Services stopped")

if __name__ == "__main__":
    main()