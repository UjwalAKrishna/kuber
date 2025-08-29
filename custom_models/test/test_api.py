#!/usr/bin/env python3
"""
Test script for STT and TTS APIs
"""

import requests
import base64
import json
import argparse
import sys
import tempfile
import subprocess
import platform
from pathlib import Path

class APITester:
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
    
    def test_stt(self):
        """Test Speech-to-Text API."""
        print("\n🎙️  Testing STT API...")
        print("="*50)
        
        # Load audio file
        audio_b64 = self.load_audio_file()
        if not audio_b64:
            return False
        
        # Prepare request
        payload = {
            "audio_data": audio_b64,
            "format": "wav",
            "language": "en",
            "task": "transcribe"
        }
        
        try:
            print(f"📤 Sending request to {self.stt_url}/predict...")
            response = requests.post(
                f"{self.stt_url}/predict",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ STT Response:")
                print(f"   Success: {result.get('success', False)}")
                print(f"   Transcription: '{result.get('transcription', '')}'")
                print(f"   Language: {result.get('language', 'unknown')}")
                print(f"   Confidence: {result.get('confidence', 0.0):.2f}")
                print(f"   Duration: {result.get('duration', 0.0):.2f}s")
                
                if result.get('success'):
                    return result.get('transcription', '')
                else:
                    print(f"❌ STT Error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ STT Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ STT Request error: {e}")
            return False
    
    def test_tts(self, text=None, voice="af_sarah"):
        """Test Text-to-Speech API."""
        print("\n🔊 Testing TTS API...")
        print("="*50)
        
        if not text:
            text = "Hello, this is a test of the Kokoro text to speech system."
        
        # Prepare request
        payload = {
            "text": text,
            "voice": voice,
            "speed": 1.0,
            "format": "wav"
        }
        
        try:
            print(f"📤 Sending request to {self.tts_url}/predict...")
            print(f"   Text: '{text}'")
            print(f"   Voice: {voice}")
            
            response = requests.post(
                f"{self.tts_url}/predict",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ TTS Response:")
                print(f"   Success: {result.get('success', False)}")
                print(f"   Voice: {result.get('voice', 'unknown')}")
                print(f"   Duration: {result.get('duration', 0.0):.2f}s")
                print(f"   Sample Rate: {result.get('sample_rate', 0)} Hz")
                
                if result.get('success'):
                    # Save and play audio
                    audio_b64 = result.get('audio_data', '')
                    if audio_b64:
                        return self.save_and_play_audio(audio_b64, f"tts_output_{voice}")
                    else:
                        print("❌ No audio data received")
                        return False
                else:
                    print(f"❌ TTS Error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ TTS Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ TTS Request error: {e}")
            return False
    
    def save_and_play_audio(self, audio_b64, filename_prefix):
        """Save base64 audio to file and play it."""
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_b64)
            
            # Save to file
            output_file = f"{filename_prefix}.wav"
            with open(output_file, 'wb') as f:
                f.write(audio_data)
            
            print(f"💾 Audio saved: {output_file} ({len(audio_data)} bytes)")
            
            # Play audio
            return self.play_audio_file(output_file)
            
        except Exception as e:
            print(f"❌ Failed to save/play audio: {e}")
            return False
    
    def play_audio_file(self, audio_file):
        """Play audio file using system player."""
        try:
            system = platform.system().lower()
            
            print(f"🔊 Playing audio: {audio_file}")
            
            if system == "windows":
                try:
                    import winsound
                    winsound.PlaySound(audio_file, winsound.SND_FILENAME)
                    print("✅ Audio played successfully")
                    return True
                except ImportError:
                    subprocess.run(['start', audio_file], shell=True, check=True)
                    print("✅ Audio player opened")
                    return True
            
            elif system == "darwin":  # macOS
                subprocess.run(['afplay', audio_file], check=True)
                print("✅ Audio played successfully")
                return True
            
            else:  # Linux
                players = ['aplay', 'paplay', 'ffplay', 'mpv']
                for player in players:
                    try:
                        subprocess.run([player, audio_file], check=True, 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
                        print(f"✅ Audio played successfully with {player}")
                        return True
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                
                print("⚠️  No audio player found, but file saved")
                return True
                
        except Exception as e:
            print(f"❌ Failed to play audio: {e}")
            return False
    
    def test_pipeline(self):
        """Test complete STT -> TTS pipeline."""
        print("\n🔄 Testing Complete Pipeline (STT -> TTS)...")
        print("="*60)
        
        # Step 1: STT
        transcription = self.test_stt()
        if not transcription:
            print("❌ Pipeline failed at STT step")
            return False
        
        print(f"\n🔄 Pipeline: Using transcription for TTS...")
        
        # Step 2: TTS with transcription
        success = self.test_tts(text=transcription, voice="af_sarah")
        
        if success:
            print("\n🎉 Pipeline completed successfully!")
            print(f"   Original audio -> '{transcription}' -> Generated speech")
            return True
        else:
            print("❌ Pipeline failed at TTS step")
            return False
    
    def test_multiple_voices(self):
        """Test TTS with multiple voices."""
        print("\n🎭 Testing Multiple Voices...")
        print("="*50)
        
        voices = ["af_sarah", "am_adam", "bf_emma", "bm_george"]
        test_text = "Hello, this is a voice test."
        
        results = []
        for voice in voices:
            print(f"\n🎤 Testing voice: {voice}")
            success = self.test_tts(text=test_text, voice=voice)
            results.append((voice, success))
        
        print(f"\n📊 Voice Test Results:")
        for voice, success in results:
            status = "✅" if success else "❌"
            print(f"   {status} {voice}")
        
        return all(success for _, success in results)
    
    def check_services(self):
        """Check if services are running."""
        print("🔍 Checking service availability...")
        
        # Check STT
        try:
            response = requests.get(f"{self.stt_url}/health", timeout=5)
            stt_status = "✅ Running" if response.status_code == 200 else "❌ Error"
        except:
            stt_status = "❌ Not available"
        
        # Check TTS
        try:
            response = requests.get(f"{self.tts_url}/health", timeout=5)
            tts_status = "✅ Running" if response.status_code == 200 else "❌ Error"
        except:
            tts_status = "❌ Not available"
        
        print(f"   STT Service ({self.stt_url}): {stt_status}")
        print(f"   TTS Service ({self.tts_url}): {tts_status}")
        
        return "✅" in stt_status and "✅" in tts_status

def main():
    parser = argparse.ArgumentParser(description="Test STT and TTS APIs")
    parser.add_argument("--test", choices=["stt", "tts", "pipeline", "voices", "all"], 
                       default="all", help="Which test to run")
    parser.add_argument("--stt-url", default="http://localhost:8001", 
                       help="STT service URL")
    parser.add_argument("--tts-url", default="http://localhost:8002", 
                       help="TTS service URL")
    parser.add_argument("--voice", default="af_sarah", 
                       help="Voice to use for TTS test")
    parser.add_argument("--text", default=None, 
                       help="Custom text for TTS test")
    
    args = parser.parse_args()
    
    print("🧪 API Testing Tool")
    print("="*60)
    
    tester = APITester(args.stt_url, args.tts_url)
    
    # Check services first
    # if not tester.check_services():
    #     print("\n❌ Some services are not available!")
    #     print("💡 Make sure to run: python main.py")
    #     return
    
    success = True
    
    if args.test == "stt":
        success = bool(tester.test_stt())
    
    elif args.test == "tts":
        success = tester.test_tts(text=args.text, voice=args.voice)
    
    elif args.test == "pipeline":
        success = tester.test_pipeline()
    
    elif args.test == "voices":
        success = tester.test_multiple_voices()
    
    elif args.test == "all":
        print("\n🚀 Running all tests...")
        
        # Individual tests
        stt_result = bool(tester.test_stt())
        tts_result = tester.test_tts(voice=args.voice)
        
        # Pipeline test
        pipeline_result = tester.test_pipeline()
        
        # Multiple voices
        voices_result = tester.test_multiple_voices()
        
        success = all([stt_result, tts_result, pipeline_result, voices_result])
        
        print(f"\n📊 Final Results:")
        print(f"   STT Test: {'✅' if stt_result else '❌'}")
        print(f"   TTS Test: {'✅' if tts_result else '❌'}")
        print(f"   Pipeline Test: {'✅' if pipeline_result else '❌'}")
        print(f"   Voices Test: {'✅' if voices_result else '❌'}")
    
    print(f"\n{'🎉 All tests passed!' if success else '❌ Some tests failed!'}")

if __name__ == "__main__":
    main()