# Kuber AI Voice

A low-latency voice conversational AI system with both batch and real-time modes, built using FastAPI and modern AI models. This project demonstrates a complete voice processing pipeline with Speech-to-Text (STT), Large Language Model (LLM), and Text-to-Speech (TTS) capabilities.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [System Components](#system-components)
  - [API Architecture](#api-architecture)
  - [Adapter Pattern](#adapter-pattern)
- [Features](#features)
  - [Voice Processing Modes](#voice-processing-modes)
  - [Gold Investment Nudging](#gold-investment-nudging)
- [Deployment](#deployment)
  - [Docker Deployment](#docker-deployment)
  - [Direct Deployment](#direct-deployment)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Performance](#performance)
- [Contributing](#contributing)

## 🎯 Overview

Kuber AI Voice is a multi-service voice conversational AI platform that processes voice queries through a sophisticated pipeline. The system supports both turn-based voice Q&A and experimental real-time streaming conversations.

**Key Capabilities:**
- **Voice-to-Voice Conversations**: Complete audio input to audio output pipeline
- **Real-time Processing**: WebSocket-based streaming for low-latency interactions
- **Intelligent Nudging**: Context-aware investment suggestions
- **Extensible Architecture**: Plugin-based adapter system for easy provider switching
- **Performance Monitoring**: Detailed latency tracking and caching

## 📸 Demo & Screenshots

### **Live Demo Video**
[Watch the complete voice interaction flow in action:](screenshots/demo.mp4)

### **Application Interface**
![Kuber AI Voice Interface](screenshots/Screenshot%202025-08-29%20062011.png)

*The modern web interface featuring voice recording, real-time streaming, and intelligent conversation management with dark/light mode support.*

**Interface Features:**
- 🎙️ **Voice Recording**: One-click audio capture with visual feedback
- 🌊 **Real-time Streaming**: Live conversation mode with WebSocket integration
- 🎨 **Modern UI**: Clean, responsive design with dark/light theme toggle
- 💬 **Chat Interface**: WhatsApp-style conversation bubbles with audio playback
- 📊 **Visual Feedback**: Waveform animations and recording indicators
- 💰 **Smart Nudging**: Contextual investment suggestions with rich UI cards

## 🏗️ Architecture

### System Components

The system consists of **3 main services**:

#### 1. **Main API Service** (Port 8000)
- **FastAPI backend** with voice processing orchestration
- **RESTful endpoints** for batch voice processing
- **WebSocket endpoints** for real-time streaming
- **Adapter management** for pluggable AI providers
- **Caching system** for improved performance
- **Gold investment nudging** with session management

#### 2. **Custom Models Service** (Ports 8001-8002)
- **Local STT Service** (Port 8001): Whisper-based speech recognition
- **Local TTS Service** (Port 8002): Kokoro-82M text-to-speech
- **HTTP and WebSocket APIs** for both services
- **Local alternatives** to cloud-based AI services

#### 3. **Web UI Service** (Port 3000)
- **Interactive web interface** with voice recording capabilities
- **Real-time audio playback** and waveform visualization
- **Dark/light mode support** with responsive design
- **WebSocket integration** for streaming conversations

### API Architecture

The core API follows a **pipeline-based architecture**:

```
Audio Input → Audio Normalization → STT → LLM → Nudge Logic → TTS → Audio Output
```

**Processing Pipeline:**
1. **Audio Normalization**: Standardizes input audio format using ffmpeg
2. **Speech-to-Text**: Converts audio to text with confidence scoring
3. **LLM Generation**: Processes text and generates intelligent responses
4. **Nudge Detection**: Analyzes content for investment opportunities
5. **Text-to-Speech**: Synthesizes response audio
6. **Response Packaging**: Returns JSON with audio, text, and timing data

### Adapter Pattern

The system uses a **pluggable adapter architecture** for maximum extensibility:

#### **STT Adapters**
- `lit_stt`: Local Whisper-based transcription service
- `hf_asr`: HuggingFace ASR API integration

#### **LLM Adapters**
- `gemini`: Google Gemini 2.0 Flash model (default)

#### **TTS Adapters**
- `lit_tts`: Local Kokoro-82M synthesis service
- `hf_tts`: HuggingFace TTS API integration

**Default Configuration:**
- **STT**: Whisper (local via custom models service)
- **LLM**: Google Gemini 2.0 Flash
- **TTS**: Kokoro-82M (local via custom models service)

**Adding New Providers:**
To integrate a new LLM or TTS provider:

1. **Create Adapter Class**: Implement the base adapter interface
```python
# Example: app/adapters/my_llm.py
from .base import LLMAdapter, LLMResult

class MyLLMAdapter(LLMAdapter):
    async def generate(self, prompt: str, functions=None) -> LLMResult:
        # Your implementation here
        return LLMResult(text="response", confidence=0.9)
```

2. **Register in Registry**: Add to `app/adapters/registry.py`
```python
self._llm_adapters["my_llm"] = MyLLMAdapter
```

3. **Update Configuration**: Modify `app/config.yaml`
```yaml
providers:
  llm: "my_llm"  # Switch to your adapter

my_llm:
  api_url: "https://your-api-endpoint.com"
  api_key: "${MY_LLM_API_KEY}"
```

## ✨ Features

### Voice Processing Modes

#### **Mode A: Turn-based Voice Q&A (HTTP)**
- **Endpoint**: `POST /v1/voice/query`
- **Process**: Upload audio file → Get complete response with audio
- **Use Case**: Traditional voice assistants, batch processing
- **Response**: JSON with transcript, LLM text, audio (base64), and timing metrics

#### **Mode B: Real-time Streaming (WebSocket)**
- **Endpoint**: `WS /v1/realtime/ws`
- **Process**: Continuous audio streaming with real-time responses
- **Use Case**: Natural conversations, live interactions
- **Features**: Partial transcripts, streaming audio responses, conversation context

**Note**: Real-time streaming is an experimental feature with limited implementation due to time constraints. It demonstrates the WebSocket flow but may require additional optimization for production use.

### Gold Investment Nudging

The system includes intelligent **contextual nudging** for gold investment opportunities:

**Trigger Conditions:**
- User mentions gold-related keywords: `gold`, `digital gold`, `sovereign gold`, `invest`, `investment`
- Configurable keyword detection from `app/config.yaml`

**Nudge Features:**
- **Session-based cooldowns**: Prevents spam (configurable interaction intervals)
- **Rich UI integration**: Special gold-themed message cards
- **Direct linking**: Links to investment landing page at `/v1/gold/invest`
- **Contextual messaging**: "Also, you may consider exploring digital gold on Simplify. Want a quick summary?"

## 🚀 Deployment

### Docker Deployment

**Prerequisites:**
- Docker and Docker Compose installed
- 4GB+ RAM recommended for local models

**Setup Steps:**

1. **Configure API Keys**: Update `app/.env` with your API credentials
```bash
# Required API keys
GEMINI_API_KEY=your-gemini-api-key-here
HF_TOKEN=your-huggingface-token-here  # Optional but recommended
```

2. **Review Configuration**: Check `app/config.yaml` for provider settings
```yaml
providers:
  stt: "lit_stt"    # Local Whisper service
  llm: "gemini"     # Google Gemini (requires API key)
  tts: "lit_tts"    # Local Kokoro TTS service
```

> **⚠️ Important Note**: If using custom models (`lit_stt` or `lit_tts`), ensure the API URLs in `config.yaml` are correctly configured. The file contains both Docker and localhost URLs - simply uncomment the appropriate ones for your deployment method.

3. **Deploy Services**:
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

4. **Wait for Initialization**: Services may take 2-3 minutes to fully start
   - Custom models need to download and load AI models
   - Health checks ensure services are ready

5. **Access Applications**:
   - **Web UI**: http://localhost:3000
   - **API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs

### Direct Deployment

**Prerequisites:**
- Python 3.10+ installed
- ffmpeg installed on system
- 8GB+ RAM recommended

**Setup Steps:**

1. **Create Virtual Environment**:
```bash
python -m venv kuber-ai-voice
source kuber-ai-voice/bin/activate  # Linux/Mac
# OR
kuber-ai-voice\Scripts\activate     # Windows
```

2. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure Environment**:
```bash
# Copy and edit environment file
cp app/.env.example app/.env
# Edit app/.env with your API keys
```

> **⚠️ Important Note**: If using custom models (`lit_stt` or `lit_tts`), ensure the API URLs in `app/config.yaml` are correctly configured. The file contains both Docker and localhost URLs - simply uncomment the appropriate ones for your deployment method.

4. **Run All Services**:
```bash
# Start all services together
python run_server.py

# OR run individual services
python run_server.py --app-only      # API only (port 8000)
python run_server.py --ui-only       # UI only (port 3000)
python run_server.py --models-only   # Custom models only (ports 8001-8002)
```

5. **Individual Service Startup** (Alternative):
```bash
# Terminal 1: Custom Models
cd custom_models && python main.py

# Terminal 2: Main API
cd app && python main.py

# Terminal 3: Web UI
cd ui && python main.py
```

**Service URLs:**
- **Web UI**: http://localhost:3000
- **Main API**: http://localhost:8000
- **STT Service**: http://localhost:8001
- **TTS Service**: http://localhost:8002

## ⚙️ Configuration

### Environment Variables (`app/.env`)

**Required:**
```bash
GEMINI_API_KEY=your-gemini-api-key-here
```

**Optional:**
```bash
HF_TOKEN=your-huggingface-token-here
LIT_STT_API_URL=http://localhost:8001      # For direct deployment
LIT_TTS_API_URL=http://localhost:8002/predict
```

### Provider Configuration (`app/config.yaml`)

```yaml
providers:
  stt: "lit_stt"    # lit_stt, hf_asr
  llm: "gemini"     # gemini only
  tts: "lit_tts"    # lit_tts, hf_tts

# Service endpoints (auto-configured for Docker)
lit_stt:
  api_url: "${LIT_STT_API_URL:-http://custom-models:8001}"

lit_tts:
  api_url: "${LIT_TTS_API_URL:-http://custom-models:8002/predict}"

# Nudging configuration
nudge:
  keywords: ["gold", "digital gold", "sovereign gold", "invest", "investment"]
  message: "Also, you may consider exploring digital gold on Simplify. Want a quick summary?"
  cooldown_interactions: 2
```

## 📚 API Documentation

### REST Endpoints

#### Voice Query Processing
```http
POST /v1/voice/query
Content-Type: multipart/form-data

Parameters:
- audio: Audio file (required)
- session_id: Session identifier (optional)
- lang: Language code (optional)
- voice: Voice preference (optional)
- use_cache: Enable caching (optional, default: true)
```

**Response:**
```json
{
  "request_id": "session_123_1234567890",
  "transcript": "Hello, how are you?",
  "llm_text": "I'm doing well, thank you for asking!",
  "audio_b64": "base64-encoded-audio-data",
  "timings": {
    "stt_ms": 245.67,
    "llm_ms": 892.34,
    "tts_ms": 567.89,
    "total_ms": 1705.90
  },
  "confidence": 0.95,
  "from_cache": false
}
```

#### WebSocket Real-time
```javascript
// Connect
const ws = new WebSocket('ws://localhost:8000/v1/realtime/ws');

// Send handshake
ws.send(JSON.stringify({
  type: 'handshake',
  config: { lang: 'en' }
}));

// Send audio chunks
ws.send(JSON.stringify({
  type: 'input.audio',
  audio: base64AudioData
}));

// Commit for processing
ws.send(JSON.stringify({
  type: 'input.commit'
}));
```

### Utility Endpoints

- `GET /health` - Service health check
- `GET /v1/providers` - List available providers
- `GET /v1/config` - Current configuration
- `GET /v1/cache/stats` - Cache statistics
- `POST /v1/cache/clear` - Clear cache

## 🧪 Testing

### Manual Testing

**Test Voice Query:**
```bash
curl -X POST http://localhost:8000/v1/voice/query \
  -F "audio=@sample.wav" \
  -F "session_id=test_session"
```

**Test Health:**
```bash
curl http://localhost:8000/health
```

### Performance Benchmarking

The system includes built-in performance monitoring:

**Latency Targets:**
- **Total end-to-end**: ≤3s for short queries (≤10s audio)
- **STT processing**: ≤800ms for typical voice input
- **LLM generation**: ≤1.5s for standard responses
- **TTS synthesis**: ≤1s for typical response length

**Monitoring:**
- All responses include detailed timing breakdowns
- Cache hit rates tracked for optimization
- WebSocket streaming latency measured

## 🎯 Performance

**Optimizations Included:**
- **Intelligent Caching**: Reduces repeated processing overhead
- **Audio Normalization**: Ensures consistent STT performance
- **Async Processing**: Non-blocking I/O for better throughput
- **Local Models**: Reduces API latency for STT/TTS
- **Connection Pooling**: Efficient HTTP client management

**Scalability Considerations:**
- Stateless design enables horizontal scaling
- Adapter pattern allows provider load balancing
- Session management supports concurrent users
- Docker deployment ready for orchestration

---

**Built with ❤️ for intelligent voice interactions**

*For questions, issues, or contributions, please refer to the project documentation or create an issue in the repository.*