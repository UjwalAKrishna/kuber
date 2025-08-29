import aiohttp
import json
import asyncio
from typing import Optional
from .base import LLMAdapter, LLMResult
from config import config


class GeminiLLM(LLMAdapter):
    """Google Gemini LLM adapter."""
    
    def __init__(self):
        self.api_key = config.gemini.api_key
        self.model_name = config.gemini.model_name
        self.temperature = config.gemini.temperature
        self.max_tokens = config.gemini.max_tokens
        self.timeout = config.gemini.timeout
        
        if not self.api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable.")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    
    async def generate(self, prompt: str, functions: Optional[list] = None) -> LLMResult:
        """Generate response using Google Gemini API."""
        try:
            # Enhanced prompt for conversational financial expert responses
            system_prompt = """You are a friendly, conversational financial expert. Keep your responses:
- Concise and conversational (2-3 sentences max)
- Easy to understand for beginners
- Practical and actionable
- Warm and approachable in tone
- Focus on key points, not lengthy explanations

User question: """
            
            enhanced_prompt = system_prompt + prompt
            
            # Prepare the request payload
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": enhanced_prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": min(self.max_tokens, 100),  # Limit for conversational responses
                    "candidateCount": 1
                }
            }
            
            # Add function calling if provided
            if functions:
                payload["tools"] = [{"functionDeclarations": functions}]
            
            # Make API request
            url = f"{self.base_url}/{self.model_name}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._parse_response(result, prompt)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Gemini API error {response.status}: {error_text}")
        
        except Exception as e:
            # Return fallback response on error
            return LLMResult(
                text=f"I apologize, but I'm having trouble processing your request right now. Error: {str(e)}"
            )
    
    def _parse_response(self, response: dict, original_prompt: str) -> LLMResult:
        """Parse Gemini API response."""
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                return LLMResult(text="I'm sorry, I couldn't generate a response.")
            
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            if not parts:
                return LLMResult(text="I'm sorry, I couldn't generate a response.")
            
            # Extract text response
            text_response = ""
            function_call = None
            
            for part in parts:
                if "text" in part:
                    text_response += part["text"]
                elif "functionCall" in part:
                    function_call = part["functionCall"]
            
            # Check for gold investment keywords if no function call detected
            if not function_call:
                from utils.nudge import nudge_manager
                if nudge_manager.has_gold_keywords(original_prompt) or nudge_manager.has_gold_keywords(text_response):
                    function_call = {"name": "suggest_gold_investment", "arguments": {}}
            
            return LLMResult(
                text=text_response.strip(),
                function_call=function_call
            )
        
        except Exception as e:
            return LLMResult(
                text=f"I encountered an error while processing the response: {str(e)}"
            )