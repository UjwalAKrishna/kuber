#!/usr/bin/env python3
"""
Test script for streaming STT and TTS APIs
"""

import asyncio
import websockets
import json
import base64
import argparse
import time
from pathlib import Path
import aiohttp

class StreamingTester:
    def __init__(self, stt_url="http://localhost:8001", tts_url="http://localhost:8002"):
        self.stt_url = stt_url
        self.tts_url = tts_url
        self.audio_file = "sample.wav"
    
    def load_audio_file(self):
        """Load and encode audio file to base64."""
        audio_path = Path(".") / self.audio_file
        if not audio_path.exists():
            audio_path = Path(self.audio_file)
            if not audio_path.exists():
                print(f"❌ Audio file not found: {self.audio_file}")
                return None
        
        try:
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            print(f"✅ Loaded audio file: {audio_path} ({len(audio_data)} bytes)")
            return audio_b64
        
        except Exception as e:
            print(f"❌ Failed to load audio file: {e}")
            return None
    
    async def test_stt_streaming(self):
        """Test STT WebSocket streaming."""
        print("\n🎙️  Testing STT WebSocket Streaming...")
        print("="*50)
        
        audio_b64 = self.load_audio_file()
        if not audio_b64:
            return False
        
        # Convert HTTP URL to WebSocket URL
        ws_url = self.stt_url.replace("http://", "ws://").replace("https://", "wss://")
        
        try:
            print(f"🔌 Connecting to WebSocket: {ws_url}/ws")
            
            async with websockets.connect(f"{ws_url}/ws") as websocket:
                print("✅ WebSocket connected")
                
                # Send audio message
                message = {
                    "type": "audio",
                    "audio_data": audio_b64,
                    "language": "en",
                    "task": "transcribe"
                }
                
                print("📤 Sending audio data...")
                await websocket.send(json.dumps(message))
                
                # Receive responses
                results = []
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        data = json.loads(response)
                        
                        if data.get("type") == "status":
                            print(f"📊 Status: {data.get('message')}")
                        
                        elif data.get("type") == "result":
                            success = data.get("success", False)
                            transcription = data.get("transcription", "")
                            language = data.get("language", "unknown")
                            confidence = data.get("confidence", 0)
                            duration = data.get("duration", 0)
                            
                            if success:
                                print(f"✅ Transcription: '{transcription}'")
                                print(f"   Language: {language}")
                                print(f"   Confidence: {confidence:.2f}")
                                print(f"   Duration: {duration:.2f}s")
                                results.append(data)
                                break  # Got final result
                            else:
                                error = data.get("error", "Unknown error")
                                print(f"❌ Transcription failed: {error}")
                                return False
                        
                        elif data.get("type") == "error":
                            print(f"❌ Error: {data.get('message')}")
                            return False
                        
                        elif data.get("type") == "pong":
                            print("🏓 Pong received")
                        
                    except asyncio.TimeoutError:
                        print("⏰ Response timeout")
                        break
                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 WebSocket connection closed")
                        break
                
                print(f"📊 STT WebSocket Results:")
                print(f"   Results received: {len(results)}")
                print(f"   Success: {'✅' if results else '❌'}")
                
                return len(results) > 0
                
        except Exception as e:
            print(f"❌ STT WebSocket error: {e}")
            return False
    
    async def test_tts_streaming(self, text=None, voice="af_heart"):
        """Test TTS WebSocket streaming."""
        print("\n🔊 Testing TTS WebSocket Streaming...")
        print("="*50)
        
        if not text:
            text = "Hello, this is a test of streaming text to speech synthesis using Kokoro."
        
        # Convert HTTP URL to WebSocket URL
        ws_url = self.tts_url.replace("http://", "ws://").replace("https://", "wss://")
        
        try:
            print(f"🔌 Connecting to TTS WebSocket: {ws_url}/ws")
            
            async with websockets.connect(f"{ws_url}/ws") as websocket:
                print("✅ TTS WebSocket connected")
                
                # Send synthesis message
                message = {
                    "type": "synthesize",
                    "text": text,
                    "voice": voice
                }
                
                print(f"📤 Sending synthesis request...")
                print(f"   Text: '{text}'")
                print(f"   Voice: {voice}")
                
                await websocket.send(json.dumps(message))
                
                # Receive responses
                audio_chunks = []
                final_result = None
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        data = json.loads(response)
                        
                        if data.get("type") == "status":
                            print(f"📊 Status: {data.get('message')}")
                            print(f"   Text length: {data.get('text_length')} chars")
                            print(f"   Voice: {data.get('voice')}")
                        
                        elif data.get("type") == "audio_chunk":
                            chunk_index = data.get("chunk_index", 0)
                            samples = data.get("samples", 0)
                            duration = data.get("duration", 0)
                            audio_data = data.get("audio_data", "")
                            gs = data.get("gs", "")
                            ps = data.get("ps", "")
                            
                            print(f"🔊 Chunk {chunk_index}: {samples} samples ({duration:.2f}s)")
                            print(f"   gs={gs}, ps={ps}")
                            
                            if audio_data:
                                audio_chunks.append(audio_data)
                                
                                # Save individual chunk
                                chunk_audio = base64.b64decode(audio_data)
                                chunk_file = f"ws_tts_chunk_{chunk_index}_{voice}.wav"
                                with open(chunk_file, 'wb') as f:
                                    f.write(chunk_audio)
                                print(f"💾 Saved: {chunk_file}")
                        
                        elif data.get("type") == "complete":
                            total_chunks = data.get("total_chunks", 0)
                            total_samples = data.get("total_samples", 0)
                            duration = data.get("duration", 0)
                            final_audio = data.get("audio_data", "")
                            
                            print(f"✅ Complete: {total_chunks} chunks, {total_samples} samples ({duration:.2f}s)")
                            
                            if final_audio:
                                # Save final combined audio
                                final_audio_data = base64.b64decode(final_audio)
                                final_file = f"ws_tts_final_{voice}.wav"
                                with open(final_file, 'wb') as f:
                                    f.write(final_audio_data)
                                print(f"💾 Final audio saved: {final_file}")
                            
                            final_result = data
                            break  # Synthesis complete
                        
                        elif data.get("type") == "error":
                            print(f"❌ Error: {data.get('message')}")
                            return False
                        
                        elif data.get("type") == "pong":
                            print("🏓 Pong received")
                        
                    except asyncio.TimeoutError:
                        print("⏰ Response timeout")
                        break
                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 TTS WebSocket connection closed")
                        break
                
                print(f"📊 TTS WebSocket Results:")
                print(f"   Audio chunks received: {len(audio_chunks)}")
                print(f"   Final result: {'✅' if final_result else '❌'}")
                
                return final_result is not None
                
        except Exception as e:
            print(f"❌ TTS WebSocket error: {e}")
            return False
    
    async def test_stt_websocket_ping(self):
        """Test STT WebSocket ping/pong."""
        print("\n🏓 Testing STT WebSocket Ping...")
        print("="*50)
        
        ws_url = self.stt_url.replace("http://", "ws://").replace("https://", "wss://")
        
        try:
            async with websockets.connect(f"{ws_url}/ws") as websocket:
                print("✅ WebSocket connected")
                
                # Send ping
                ping_message = {"type": "ping"}
                await websocket.send(json.dumps(ping_message))
                print("📤 Ping sent")
                
                # Wait for pong
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data.get("type") == "pong":
                    print("✅ Pong received - WebSocket is responsive")
                    return True
                else:
                    print(f"❌ Unexpected response: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Ping test failed: {e}")
            return False
    
    async def test_tts_websocket_ping(self):
        """Test TTS WebSocket ping/pong."""
        print("\n🏓 Testing TTS WebSocket Ping...")
        print("="*50)
        
        ws_url = self.tts_url.replace("http://", "ws://").replace("https://", "wss://")
        
        try:
            async with websockets.connect(f"{ws_url}/ws") as websocket:
                print("✅ TTS WebSocket connected")
                
                # Send ping
                ping_message = {"type": "ping"}
                await websocket.send(json.dumps(ping_message))
                print("📤 Ping sent")
                
                # Wait for pong
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data.get("type") == "pong":
                    print("✅ Pong received - TTS WebSocket is responsive")
                    return True
                else:
                    print(f"❌ Unexpected response: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ TTS Ping test failed: {e}")
            return False
    
    async def test_streaming_pipeline(self):
        """Test STT WebSocket -> TTS streaming pipeline."""
        print("\n🔄 Testing Streaming Pipeline (STT WebSocket -> TTS)...")
        print("="*60)
        
        # Step 1: STT WebSocket
        print("🎙️  Step 1: WebSocket STT...")
        stt_success = await self.test_stt_streaming()
        
        if not stt_success:
            print("❌ Pipeline failed at STT step")
            return False
        
        # Step 2: TTS Streaming with a test message
        print("\n🔊 Step 2: Streaming TTS...")
        pipeline_text = "This is a streaming pipeline test where speech was converted to text using WebSocket and now back to speech."
        tts_success = await self.test_tts_streaming(text=pipeline_text, voice="af_heart")
        
        if tts_success:
            print("\n🎉 Streaming Pipeline completed successfully!")
            return True
        else:
            print("❌ Pipeline failed at TTS step")
            return False

async def main():
    parser = argparse.ArgumentParser(description="Test WebSocket Streaming STT and TTS APIs")
    parser.add_argument("--test", choices=["stt", "tts", "stt-ping", "tts-ping", "pipeline", "all"], 
                       default="all", help="Which streaming test to run")
    parser.add_argument("--stt-url", default="http://localhost:8001", 
                       help="STT service URL")
    parser.add_argument("--tts-url", default="http://localhost:8002", 
                       help="TTS service URL")
    parser.add_argument("--voice", default="af_heart", 
                       help="Voice to use for TTS test")
    parser.add_argument("--text", default=None, 
                       help="Custom text for TTS test")
    
    args = parser.parse_args()
    
    print("🌊 WebSocket Streaming API Testing Tool")
    print("="*60)
    
    tester = StreamingTester(args.stt_url, args.tts_url)
    
    success = True
    
    if args.test == "stt":
        success = await tester.test_stt_streaming()
    
    elif args.test == "tts":
        success = await tester.test_tts_streaming(text=args.text, voice=args.voice)
    
    elif args.test == "stt-ping":
        success = await tester.test_stt_websocket_ping()
    
    elif args.test == "tts-ping":
        success = await tester.test_tts_websocket_ping()
    
    elif args.test == "pipeline":
        success = await tester.test_streaming_pipeline()
    
    elif args.test == "all":
        print("\n🚀 Running all WebSocket streaming tests...")
        
        # WebSocket ping tests
        stt_ping_result = await tester.test_stt_websocket_ping()
        tts_ping_result = await tester.test_tts_websocket_ping()
        
        # Individual streaming tests
        stt_result = await tester.test_stt_streaming()
        tts_result = await tester.test_tts_streaming(voice=args.voice)
        
        # Pipeline test
        pipeline_result = await tester.test_streaming_pipeline()
        
        success = all([stt_ping_result, tts_ping_result, stt_result, tts_result, pipeline_result])
        
        print(f"\n📊 Final WebSocket Streaming Results:")
        print(f"   STT WebSocket Ping: {'✅' if stt_ping_result else '❌'}")
        print(f"   TTS WebSocket Ping: {'✅' if tts_ping_result else '❌'}")
        print(f"   STT WebSocket: {'✅' if stt_result else '❌'}")
        print(f"   TTS WebSocket: {'✅' if tts_result else '❌'}")
        print(f"   Pipeline Streaming: {'✅' if pipeline_result else '❌'}")
    
    print(f"\n{'🎉 All WebSocket streaming tests passed!' if success else '❌ Some WebSocket streaming tests failed!'}")

if __name__ == "__main__":
    asyncio.run(main())