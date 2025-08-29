import logging
from typing import Dict, Any
from fastapi import HTTPException
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


class VoiceProcessingError(Exception):
    """Base exception for voice processing errors."""
    pass


class STTError(VoiceProcessingError):
    """Speech-to-text processing error."""
    pass


class LLMError(VoiceProcessingError):
    """Language model processing error."""
    pass


class TTSError(VoiceProcessingError):
    """Text-to-speech processing error."""
    pass


class AudioProcessingError(VoiceProcessingError):
    """Audio processing error."""
    pass


def create_error_response(error: Exception, request_id: str = None) -> Dict[str, Any]:
    """Create standardized error response."""
    error_type = type(error).__name__
    
    response = {
        "error": True,
        "error_type": error_type,
        "message": str(error),
        "request_id": request_id
    }
    
    # Log the error
    logger.error(f"Error in request {request_id}: {error_type} - {str(error)}")
    
    return response


async def handle_voice_processing_error(error: Exception, request_id: str = None) -> JSONResponse:
    """Handle voice processing errors and return appropriate HTTP response."""
    
    if isinstance(error, (STTError, LLMError, TTSError, AudioProcessingError)):
        status_code = 422  # Unprocessable Entity
    elif isinstance(error, HTTPException):
        status_code = error.status_code
    else:
        status_code = 500  # Internal Server Error
    
    error_response = create_error_response(error, request_id)
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )