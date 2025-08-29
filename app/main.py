import json
import asyncio
import logging
import uuid
import base64
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path


from orchestrator import VoiceOrchestrator
from utils.audio import chunk_audio, normalize_audio
from utils.error_handling import handle_voice_processing_error, AudioProcessingError
from utils.caching import voice_cache
from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.server.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kuber AI Voice", 
    version="1.0.0",
    description="Low-latency voice conversational pipeline with batch and real-time modes"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = VoiceOrchestrator()


@app.post("/v1/voice/query")
async def voice_query(
    audio: UploadFile = File(...),
    lang: Optional[str] = Form(None),
    voice: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    use_cache: Optional[bool] = Form(True)
):
    """Process voice query through STT -> LLM -> TTS pipeline."""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    request_id = f"{session_id}_{int(uuid.uuid4().int)}"
    
    try:
        # Validate audio file
        if not audio.content_type or not audio.content_type.startswith('audio/'):
            logger.error(f"Invalid audio content type: {audio.content_type}")
            raise AudioProcessingError("Invalid audio file format")
        
        # Read and validate audio file
        audio_bytes = await audio.read()
        if len(audio_bytes) == 0:
            logger.error("Empty audio file received")
            raise AudioProcessingError("Empty audio file")
        
        logger.info(f"Processing voice query {request_id}, audio size: {len(audio_bytes)} bytes")
        
        # Process through orchestrator
        result = await orchestrator.process_voice_query(
            audio_bytes=audio_bytes,
            session_id=session_id,
            lang=lang,
            voice=voice,
            use_cache=use_cache
        )
        
        logger.info(f"Voice query {request_id} completed in {result.get('timings', {}).get('total_ms', 0)}ms")
        return JSONResponse(content=result)
    
    except Exception as e:
        logger.error(f"Voice query {request_id} failed: {str(e)}")
        return await handle_voice_processing_error(e, request_id)


@app.websocket("/v1/realtime/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice interaction."""
    session_id = str(uuid.uuid4())
    audio_buffer = bytearray()
    conversation_history = []  # Track conversation context
    is_processing = False
    
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection established for session {session_id}")
        
        # Wait for handshake
        handshake = await websocket.receive_text()
        handshake_data = json.loads(handshake)
        
        await websocket.send_text(json.dumps({
            "type": "session.created",
            "session_id": session_id,
            "message": "Real-time mode active! Start speaking naturally - responses will stream back in real-time."
        }))
        
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data["type"] == "input.audio":
                # Decode and append audio chunk
                try:
                    audio_chunk = base64.b64decode(data["audio"])
                    audio_buffer.extend(audio_chunk)
                    
                    # For real-time processing, try partial transcription on larger buffers
                    if len(audio_buffer) > 32000 and not is_processing:  # ~2 seconds at 16kHz
                        try:
                            # Attempt partial transcription
                            normalized_audio = normalize_audio(bytes(audio_buffer))
                            partial_transcript, confidence = await orchestrator.stt_adapter.transcribe(normalized_audio)
                            
                            if partial_transcript and len(partial_transcript.strip()) > 0:
                                await websocket.send_text(json.dumps({
                                    "type": "transcript.partial",
                                    "text": partial_transcript,
                                    "confidence": confidence
                                }))
                        except Exception as partial_e:
                            # If partial transcription fails, just send acknowledgment
                            await websocket.send_text(json.dumps({
                                "type": "transcript.partial", 
                                "text": "..."
                            }))
                    else:
                        # Send simple acknowledgment for small buffers
                        await websocket.send_text(json.dumps({
                            "type": "transcript.partial",
                            "text": "..."
                        }))
                        
                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Failed to process audio chunk"
                    }))
            
            elif data["type"] == "input.commit":
                if not audio_buffer:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "No audio data to process"
                    }))
                    continue
                
                # Prevent multiple simultaneous processing
                if is_processing:
                    await websocket.send_text(json.dumps({
                        "type": "transcript.partial",
                        "text": "Processing previous input..."
                    }))
                    continue
                
                is_processing = True
                
                try:
                    logger.info(f"Processing {len(audio_buffer)} bytes of audio for session {session_id}")
                    
                    # Normalize audio
                    normalized_audio = normalize_audio(bytes(audio_buffer))
                    
                    # Transcribe
                    transcript, confidence = await orchestrator.stt_adapter.transcribe(normalized_audio)
                    
                    # Send final transcript
                    await websocket.send_text(json.dumps({
                        "type": "transcript.final",
                        "text": transcript,
                        "confidence": confidence
                    }))
                    
                    # Check for conversation end commands
                    if any(word in transcript.lower() for word in ['goodbye', 'bye', 'exit', 'quit', 'end conversation']):
                        await websocket.send_text(json.dumps({
                            "type": "conversation.ending",
                            "message": "Goodbye! Thanks for chatting."
                        }))
                        
                        # Generate farewell response
                        farewell_audio = await orchestrator.tts_adapter.synthesize("Goodbye! Thanks for chatting.")
                        farewell_chunks = chunk_audio(farewell_audio, chunk_duration_ms=500)
                        for i, chunk in enumerate(farewell_chunks):
                            chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                            await websocket.send_text(json.dumps({
                                "type": "output.audio_chunk",
                                "audio": chunk_b64,
                                "chunk_index": i
                            }))
                            await asyncio.sleep(0.05)
                        
                        await websocket.send_text(json.dumps({
                            "type": "output.complete",
                            "total_chunks": len(farewell_chunks)
                        }))
                        break  # End the conversation
                    
                    # Add user input to conversation history
                    conversation_history.append({"role": "user", "content": transcript})
                    
                    # Build context for LLM (last 10 exchanges to keep it manageable)
                    context_messages = conversation_history[-20:]  # Last 10 user-assistant pairs
                    context_text = ""
                    for msg in context_messages:
                        if msg["role"] == "user":
                            context_text += f"User: {msg['content']}\n"
                        else:
                            context_text += f"Assistant: {msg['content']}\n"
                    
                    # Generate LLM response with conversation context
                    if context_text:
                        full_prompt = f"Previous conversation:\n{context_text}\nUser: {transcript}\nAssistant:"
                    else:
                        full_prompt = transcript
                    
                    llm_result = await orchestrator.llm_adapter.generate(full_prompt)
                    
                    # Add assistant response to conversation history
                    conversation_history.append({"role": "assistant", "content": llm_result.text})
                    
                    # Send LLM response text
                    await websocket.send_text(json.dumps({
                        "type": "llm.response",
                        "text": llm_result.text
                    }))
                    
                    # Synthesize audio response with real-time streaming
                    await websocket.send_text(json.dumps({
                        "type": "synthesis.started",
                        "message": "Generating audio response..."
                    }))
                    
                    audio_response = await orchestrator.tts_adapter.synthesize(llm_result.text)
                    
                    # Stream audio chunks immediately with smaller chunks for lower latency
                    audio_chunks = chunk_audio(audio_response, chunk_duration_ms=250)  # Smaller chunks
                    for i, chunk in enumerate(audio_chunks):
                        chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                        await websocket.send_text(json.dumps({
                            "type": "output.audio_chunk",
                            "audio": chunk_b64,
                            "chunk_index": i,
                            "total_chunks": len(audio_chunks)
                        }))
                        # Minimal delay for real-time streaming
                        await asyncio.sleep(0.01)
                    
                    # Send completion marker with conversation continuation prompt
                    await websocket.send_text(json.dumps({
                        "type": "output.complete",
                        "total_chunks": len(audio_chunks),
                        "message": "Ready for next input. Continue speaking naturally!"
                    }))
                    
                    logger.info(f"WebSocket processing completed for session {session_id}. Conversation history: {len(conversation_history)} messages")
                    
                except Exception as e:
                    logger.error(f"WebSocket processing error for session {session_id}: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
                finally:
                    # Reset processing state and clear buffer for next input
                    is_processing = False
                    audio_buffer.clear()
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass


@app.get("/v1/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return voice_cache.stats()


@app.post("/v1/cache/clear")
async def clear_cache():
    """Clear the voice query cache."""
    voice_cache.clear()
    return {"message": "Cache cleared successfully"}


@app.post("/v1/cache/cleanup")
async def cleanup_cache():
    """Remove expired entries from cache."""
    removed_count = voice_cache.cleanup_expired()
    return {"message": f"Removed {removed_count} expired entries"}


@app.get("/v1/providers")
async def list_providers():
    """List available providers for each component."""
    try:
        from .adapters.registry import registry
    except ImportError:
        from app.adapters.registry import registry
    
    return {
        "stt_providers": registry.available_stt_providers,
        "llm_providers": registry.available_llm_providers,
        "tts_providers": registry.available_tts_providers,
        "current_config": {
            "stt": config.providers.stt,
            "llm": config.providers.llm,
            "tts": config.providers.tts
        }
    }


@app.get("/v1/config")
async def get_config():
    """Get current configuration (excluding sensitive data)."""
    return {
        "providers": config.providers.dict(),
        "server": config.server.dict(),
        "nudge": {
            "cooldown_interactions": config.nudge.cooldown_interactions,
            "keywords_count": len(config.nudge.keywords)
        }
    }


@app.get("/v1/gold/invest")
async def gold_investment_page():
    """Serve gold investment page with Simplify Money branding."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gold Investment - Simplify Money</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                color: #ffffff;
                min-height: 100vh;
                line-height: 1.6;
            }
            
            .header {
                background: rgba(0, 0, 0, 0.3);
                padding: 1rem 2rem;
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(255, 215, 0, 0.3);
            }
            
            .logo {
                height: 50px;
                filter: brightness(1.2);
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .hero {
                text-align: center;
                margin: 3rem 0;
            }
            
            .hero h1 {
                font-size: 3rem;
                margin-bottom: 1rem;
                background: linear-gradient(45deg, #ffd700, #ffed4e);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .hero p {
                font-size: 1.2rem;
                color: #e0e0e0;
                margin-bottom: 2rem;
            }
            
            .gold-widget {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 2rem;
                margin: 2rem 0;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 215, 0, 0.3);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            
            .gold-price {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                padding: 1rem;
                background: rgba(255, 215, 0, 0.1);
                border-radius: 10px;
            }
            
            .price-info h3 {
                color: #ffd700;
                font-size: 1.5rem;
            }
            
            .price-value {
                font-size: 2rem;
                font-weight: bold;
                color: #ffffff;
            }
            
            .investment-options {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin: 2rem 0;
            }
            
            .option-card {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 1.5rem;
                border: 1px solid rgba(255, 215, 0, 0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .option-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(255, 215, 0, 0.2);
            }
            
            .option-card h4 {
                color: #ffd700;
                margin-bottom: 1rem;
                font-size: 1.2rem;
            }
            
            .cta-button {
                background: linear-gradient(45deg, #ffd700, #ffed4e);
                color: #1a1a2e;
                padding: 1rem 2rem;
                border: none;
                border-radius: 25px;
                font-size: 1.1rem;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                margin: 1rem 0;
            }
            
            .cta-button:hover {
                transform: scale(1.05);
                box-shadow: 0 5px 15px rgba(255, 215, 0, 0.4);
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin: 2rem 0;
            }
            
            .feature {
                text-align: center;
                padding: 1rem;
            }
            
            .feature-icon {
                font-size: 2rem;
                margin-bottom: 0.5rem;
            }
            
            .footer {
                text-align: center;
                margin-top: 3rem;
                padding: 2rem;
                border-top: 1px solid rgba(255, 215, 0, 0.3);
                color: #b0b0b0;
            }
            
            @media (max-width: 768px) {
                .hero h1 {
                    font-size: 2rem;
                }
                
                .container {
                    padding: 1rem;
                }
                
                .gold-price {
                    flex-direction: column;
                    text-align: center;
                }
            }
        </style>
    </head>
    <body>
        <header class="header">
            <img src="https://www.simplifymoney.in/images/SM_Logo_White_Gold.png" alt="Simplify Money" class="logo">
        </header>
        
        <div class="container">
            <section class="hero">
                <h1>Smart Gold Investment</h1>
                <p>Start your gold investment journey with India's most trusted AI-powered financial advisor</p>
            </section>
            
            <div class="gold-widget">
                <div class="gold-price">
                    <div class="price-info">
                        <h3>Gold Price Today</h3>
                        <p>24K Gold per gram</p>
                    </div>
                    <div class="price-value">₹6,847</div>
                </div>
                
                <div class="investment-options">
                    <div class="option-card">
                        <h4>🏆 Digital Gold</h4>
                        <p>Start with as low as ₹100. Buy, sell, and store gold digitally with 99.9% purity guarantee.</p>
                        <a href="#" class="cta-button">Start Investing</a>
                    </div>
                    
                    <div class="option-card">
                        <h4>📈 Gold ETFs</h4>
                        <p>Invest in gold through exchange-traded funds for better liquidity and lower storage costs.</p>
                        <a href="#" class="cta-button">Explore ETFs</a>
                    </div>
                    
                    <div class="option-card">
                        <h4>🎯 SIP in Gold</h4>
                        <p>Systematic Investment Plan in gold to build wealth gradually with rupee cost averaging.</p>
                        <a href="#" class="cta-button">Start SIP</a>
                    </div>
                    
                    <div class="option-card">
                        <h4>💰 Gold Savings</h4>
                        <p>Automated gold savings plans that help you accumulate gold based on your spending patterns.</p>
                        <a href="#" class="cta-button">Auto Save</a>
                    </div>
                </div>
                
                <div class="features">
                    <div class="feature">
                        <div class="feature-icon">🔒</div>
                        <h4>Secure Storage</h4>
                        <p>Bank-grade security</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">📱</div>
                        <h4>Easy Trading</h4>
                        <p>Buy/sell instantly</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">💎</div>
                        <h4>99.9% Pure</h4>
                        <p>Certified purity</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">📊</div>
                        <h4>AI Insights</h4>
                        <p>Smart recommendations</p>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 2rem;">
                    <a href="#" class="cta-button" style="font-size: 1.3rem; padding: 1.2rem 3rem;">
                        Get Started with Gold Investment
                    </a>
                </div>
            </div>
        </div>
        
        <footer class="footer">
            <p>&copy; 2024 Simplify Money. All rights reserved. | Powered by AI for smarter financial decisions</p>
            <p>Investment in securities market are subject to market risks. Read all the related documents carefully before investing.</p>
        </footer>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level,
        reload=True
    )