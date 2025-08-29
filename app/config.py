import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field



# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, skip loading
    pass


# Removed unused config classes: WhisperConfig, OpenAIConfig


class LitSTTConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    api_url: str = Field(description="LIT STT API URL")


class HFASRConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    api_url: str = Field(description="HuggingFace ASR API URL")
    api_token: Optional[str] = Field(description="HuggingFace API token")
    use_auth_token: bool = Field(description="Whether to use HF auth token")


# Removed unused config classes: HFLocalConfig, LMStudioConfig, ElevenLabsConfig, CoquiConfig


class LitTTSConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    api_url: str = Field(description="LIT TTS API URL")


class HFTTSConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    api_url: str = Field(description="HuggingFace TTS API URL")
    api_token: Optional[str] = Field(description="HuggingFace API token")
    use_auth_token: bool = Field(description="Whether to use HF auth token")


# Removed unused config classes: AzureConfig, GoogleConfig


class GeminiConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    api_key: Optional[str] = Field(description="Google Gemini API key")
    model_name: str = Field(description="Gemini model name")
    temperature: float = Field(description="Sampling temperature")
    max_tokens: int = Field(description="Maximum tokens to generate")
    timeout: int = Field(description="Request timeout in seconds")


class ProvidersConfig(BaseModel):
    stt: str = Field(description="STT provider to use")
    llm: str = Field(description="LLM provider to use")
    tts: str = Field(description="TTS provider to use")


class ServerConfig(BaseModel):
    host: str = Field(description="Server host")
    port: int = Field(description="Server port")
    log_level: str = Field(description="Logging level")
    reload: bool = Field(description="Enable auto-reload")


class CacheConfig(BaseModel):
    enabled: bool = Field(description="Enable caching")
    default_ttl: float = Field(description="Default TTL in seconds")
    max_size: int = Field(description="Maximum cache entries")


class NudgeConfig(BaseModel):
    keywords: List[str] = Field(description="Keywords that trigger nudge")
    message: str = Field(description="Nudge message to append")
    cooldown_interactions: int = Field(description="Interactions between nudges")


class Config:
    """Configuration manager that loads from YAML files and environment variables."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.environ.get('CONFIG_FILE', 'config.yaml')
        
        self.config_path = Path(config_path)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file and environment variables."""
        # Load base configuration from file
        config_data = self._load_config_file()
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Initialize configuration objects
        self._initialize_configs(config_data)
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable expansion."""
        if not self.config_path.exists():
            print(f"⚠️  Config file {self.config_path} not found, using defaults")
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
                # Expand environment variables in the YAML content
                content = os.path.expandvars(content)
                return yaml.safe_load(content) or {}
        except Exception as e:
            print(f"⚠️  Error loading config file {self.config_path}: {e}")
            return {}
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'providers': {
                'stt': 'lit_stt',
                'llm': 'gemini', 
                'tts': 'lit_tts'
            },
            'lit_stt': {
                'api_url': 'http://localhost:8001/predict'
            },
            'hf_asr': {
                'api_url': 'https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3',
                'api_token': None,
                'use_auth_token': False
            },
            'lit_tts': {
                'api_url': 'http://localhost:8002/predict'
            },
            'hf_tts': {
                'api_url': 'https://router.huggingface.co/fal-ai/fal-ai/kokoro/american-english',
                'api_token': None,
                'use_auth_token': False
            },
            'gemini': {
                'api_key': None,
                'model_name': 'gemini-2.0-flash',
                'temperature': 0.7,
                'max_tokens': 2000,
                'timeout': 30
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'log_level': 'info',
                'reload': False
            },
            'cache': {
                'enabled': True,
                'default_ttl': 300.0,
                'max_size': 1000
            },
            'nudge': {
                'keywords': ['gold', 'digital gold', 'sovereign gold', 'invest', 'investment'],
                'message': 'Also, you may consider exploring digital gold on Simplify. Want a quick summary?',
                'cooldown_interactions': 2
            }
        }
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Merge with defaults first
        defaults = self._get_default_config()
        for section, section_defaults in defaults.items():
            if section not in config_data:
                config_data[section] = {}
            for key, default_value in section_defaults.items():
                if key not in config_data[section]:
                    config_data[section][key] = default_value
        
        # Server overrides
        server_config = config_data['server']
        server_config['host'] = os.environ.get('SERVER_HOST', server_config['host'])
        server_config['port'] = int(os.environ.get('SERVER_PORT', str(server_config['port'])))
        server_config['log_level'] = os.environ.get('LOG_LEVEL', server_config['log_level'])
        
        # Provider overrides
        providers_config = config_data['providers']
        providers_config['stt'] = os.environ.get('STT_PROVIDER', providers_config['stt'])
        providers_config['llm'] = os.environ.get('LLM_PROVIDER', providers_config['llm'])
        providers_config['tts'] = os.environ.get('TTS_PROVIDER', providers_config['tts'])
        
        # HuggingFace API tokens
        hf_token = os.environ.get('HUGGINGFACE_TOKEN') or os.environ.get('HF_TOKEN')
        if hf_token:
            config_data['hf_asr']['api_token'] = hf_token
            config_data['hf_asr']['use_auth_token'] = True
            config_data['hf_tts']['api_token'] = hf_token
            config_data['hf_tts']['use_auth_token'] = True
        
        # Gemini overrides
        gemini_config = config_data['gemini']
        gemini_config['api_key'] = os.environ.get('GEMINI_API_KEY', gemini_config['api_key'])
        gemini_config['model_name'] = os.environ.get('GEMINI_MODEL', gemini_config['model_name'])
        if 'GEMINI_TEMPERATURE' in os.environ:
            gemini_config['temperature'] = float(os.environ['GEMINI_TEMPERATURE'])
        if 'GEMINI_MAX_TOKENS' in os.environ:
            gemini_config['max_tokens'] = int(os.environ['GEMINI_MAX_TOKENS'])
        
        # Cache overrides
        cache_config = config_data['cache']
        cache_config['enabled'] = os.environ.get('CACHE_ENABLED', 'true').lower() == 'true'
        if 'CACHE_TTL' in os.environ:
            cache_config['default_ttl'] = float(os.environ['CACHE_TTL'])
        if 'CACHE_MAX_SIZE' in os.environ:
            cache_config['max_size'] = int(os.environ['CACHE_MAX_SIZE'])

    
        
        return config_data
    
    def _initialize_configs(self, config_data: Dict[str, Any]):
        """Initialize all configuration objects."""
        self.providers = ProvidersConfig(**config_data.get('providers', {}))
        self.lit_stt = LitSTTConfig(**config_data.get('lit_stt', {}))
        self.hf_asr = HFASRConfig(**config_data.get('hf_asr', {}))
        self.lit_tts = LitTTSConfig(**config_data.get('lit_tts', {}))
        self.hf_tts = HFTTSConfig(**config_data.get('hf_tts', {}))
        self.gemini = GeminiConfig(**config_data.get('gemini', {}))
        self.server = ServerConfig(**config_data.get('server', {}))
        self.cache = CacheConfig(**config_data.get('cache', {}))
        self.nudge = NudgeConfig(**config_data.get('nudge', {}))
    
    def reload(self):
        """Reload configuration from file."""
        self._load_config()
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary (excluding sensitive data)."""
        return {
            'providers': self.providers.model_dump(),
            'server': self.server.model_dump(),
            'cache': self.cache.model_dump(),
            'nudge': {
                'keywords_count': len(self.nudge.keywords),
                'cooldown_interactions': self.nudge.cooldown_interactions
            }
        }


# Global config instance
config = Config()