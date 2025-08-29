import time
import base64
import logging
import warnings
from typing import Optional, Dict, Any

# Suppress transformers warnings in orchestrator
warnings.filterwarnings("ignore", message=".*return_token_timestamps.*deprecated.*")
warnings.filterwarnings("ignore", message=".*past_key_values.*deprecated.*")
warnings.filterwarnings("ignore", message=".*EncoderDecoderCache.*")


from adapters.registry import registry
from utils.audio import normalize_audio
from utils.nudge import nudge_manager
from utils.caching import voice_cache
from config import config

logger = logging.getLogger(__name__)


class VoiceOrchestrator:
    """Main orchestrator for voice processing pipeline."""
    
    def __init__(self):
        self._initialize_adapters()
    
    def _initialize_adapters(self):
        """Initialize adapters based on configuration."""
        try:
            self.stt_adapter = registry.get_stt_adapter(config.providers.stt)
            self.llm_adapter = registry.get_llm_adapter(config.providers.llm)
            self.tts_adapter = registry.get_tts_adapter(config.providers.tts)
            
            logger.info(f"Initialized adapters - STT: {config.providers.stt}, "
                       f"LLM: {config.providers.llm}, TTS: {config.providers.tts}")
        except Exception as e:
            logger.error(f"Failed to initialize adapters: {e}")
            raise
    
    async def process_voice_query(
        self, 
        audio_bytes: bytes, 
        session_id: Optional[str] = None,
        lang: Optional[str] = None,
        voice: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Process a complete voice query through STT -> LLM -> TTS pipeline."""
        start_time = time.time()
        timings = {}
        session_id = session_id or "anonymous"
        
        logger.debug(f"Starting voice processing for session {session_id}")
        
        # Check cache first
        if use_cache:
            cached_result = voice_cache.get(audio_bytes, session_id)
            if cached_result:
                logger.info(f"Cache hit for session {session_id}")
                cached_result["request_id"] = f"{session_id}_{int(time.time())}"
                cached_result["from_cache"] = True
                return cached_result
        
        try:
            # Step 1: Normalize audio
            logger.debug("Normalizing audio")
            normalized_audio = normalize_audio(audio_bytes)
            
            # Step 2: Speech-to-Text
            logger.debug("Starting STT processing")
            stt_start = time.time()
            transcript, confidence = await self.stt_adapter.transcribe(normalized_audio)
            stt_time = (time.time() - stt_start) * 1000
            timings["stt_ms"] = round(stt_time, 2)
            logger.debug(f"STT completed in {stt_time:.2f}ms: '{transcript}'")
            
            # Step 3: LLM Generation
            logger.debug("Starting LLM processing")
            llm_start = time.time()
            llm_result = await self.llm_adapter.generate(transcript)
            llm_time = (time.time() - llm_start) * 1000
            timings["llm_ms"] = round(llm_time, 2)
            logger.debug(f"LLM completed in {llm_time:.2f}ms")
            
            # Step 4: Check for gold keywords and nudging
            response_text = llm_result.text
            gold_nudge_data = None
            
            # Check if user mentioned gold-related keywords
            if nudge_manager.has_gold_keywords(transcript):
                gold_nudge_data = nudge_manager.get_gold_nudge_data()
                logger.debug("Gold keywords detected, adding nudge data")
            
            # Check for general nudge (existing functionality)
            if session_id and nudge_manager.should_nudge(session_id, llm_result.function_call is not None):
                response_text += f" {nudge_manager.get_nudge_message()}"
                logger.debug("Added general nudge message")
            
            # Step 5: Text-to-Speech
            logger.debug("Starting TTS processing")
            tts_start = time.time()
            audio_output = await self.tts_adapter.synthesize(response_text)
            tts_time = (time.time() - tts_start) * 1000
            timings["tts_ms"] = round(tts_time, 2)
            logger.debug(f"TTS completed in {tts_time:.2f}ms")
            
            # Calculate total time
            total_time = (time.time() - start_time) * 1000
            timings["total_ms"] = round(total_time, 2)
            
            # Encode audio as base64
            audio_b64 = base64.b64encode(audio_output).decode('utf-8')
            
            result = {
                "request_id": f"{session_id}_{int(time.time())}",
                "transcript": transcript,
                "llm_text": response_text,
                "audio_b64": audio_b64,
                "timings": timings,
                "confidence": confidence,
                "from_cache": False
            }
            
            # Add gold nudge data if detected
            if gold_nudge_data:
                result["gold_nudge"] = gold_nudge_data
            
            # Cache the result
            if use_cache:
                voice_cache.set(audio_bytes, result, session_id)
                logger.debug("Result cached")
            
            logger.info(f"Voice processing completed for session {session_id} in {total_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Voice processing failed for session {session_id}: {e}")
            raise