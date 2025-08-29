from typing import Dict, Type
from .base import STTAdapter, LLMAdapter, TTSAdapter
from .hf_asr import HuggingFaceASR
from .lit_stt import LitSTT
from .hf_tts import HuggingFaceTTS
from .lit_tts import LitTTS
from .gemini_llm import GeminiLLM


class AdapterRegistry:
    """Registry for managing adapter instances and types."""
    
    def __init__(self):
        self._stt_adapters: Dict[str, Type[STTAdapter]] = {
            "hf_asr": HuggingFaceASR,
            "lit_stt": LitSTT,
        }
        
        self._llm_adapters: Dict[str, Type[LLMAdapter]] = {
            "gemini": GeminiLLM,
        }
        
        self._tts_adapters: Dict[str, Type[TTSAdapter]] = {
            "hf_tts": HuggingFaceTTS,
            "lit_tts": LitTTS,
        }
        
        # Cache for adapter instances
        self._adapter_instances: Dict[str, object] = {}
    
    def get_stt_adapter(self, name: str) -> STTAdapter:
        """Get STT adapter instance, creating if not cached."""
        if name not in self._stt_adapters:
            raise ValueError(f"Unknown STT adapter: {name}. Available: {list(self._stt_adapters.keys())}")
        
        cache_key = f"stt_{name}"
        if cache_key not in self._adapter_instances:
            self._adapter_instances[cache_key] = self._stt_adapters[name]()
        
        return self._adapter_instances[cache_key]
    
    def get_llm_adapter(self, name: str) -> LLMAdapter:
        """Get LLM adapter instance, creating if not cached."""
        if name not in self._llm_adapters:
            raise ValueError(f"Unknown LLM adapter: {name}. Available: {list(self._llm_adapters.keys())}")
        
        cache_key = f"llm_{name}"
        if cache_key not in self._adapter_instances:
            self._adapter_instances[cache_key] = self._llm_adapters[name]()
        
        return self._adapter_instances[cache_key]
    
    def get_tts_adapter(self, name: str) -> TTSAdapter:
        """Get TTS adapter instance, creating if not cached."""
        if name not in self._tts_adapters:
            raise ValueError(f"Unknown TTS adapter: {name}. Available: {list(self._tts_adapters.keys())}")
        
        cache_key = f"tts_{name}"
        if cache_key not in self._adapter_instances:
            self._adapter_instances[cache_key] = self._tts_adapters[name]()
        
        return self._adapter_instances[cache_key]
    
    @property
    def available_stt_providers(self) -> list[str]:
        """Get list of available STT providers."""
        return list(self._stt_adapters.keys())
    
    @property
    def available_llm_providers(self) -> list[str]:
        """Get list of available LLM providers."""
        return list(self._llm_adapters.keys())
    
    @property
    def available_tts_providers(self) -> list[str]:
        """Get list of available TTS providers."""
        return list(self._tts_adapters.keys())
    
    def clear_cache(self) -> None:
        """Clear all cached adapter instances."""
        self._adapter_instances.clear()


# Global registry instance
registry = AdapterRegistry()