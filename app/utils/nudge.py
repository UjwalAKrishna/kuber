from typing import Dict
import time
from config import config


class NudgeManager:
    def __init__(self):
        self.session_data: Dict[str, dict] = {}
    
    def should_nudge(self, session_id: str, has_function_call: bool) -> bool:
        """Check if we should add a nudge based on session cooldown."""
        if not has_function_call:
            return False
        
        current_time = time.time()
        
        if session_id not in self.session_data:
            self.session_data[session_id] = {
                "last_nudge_time": 0,
                "interaction_count": 0
            }
        
        session = self.session_data[session_id]
        session["interaction_count"] += 1
        
        # Check cooldown: at least N interactions since last nudge (from config)
        interactions_since_nudge = session["interaction_count"] - session.get("last_nudge_interaction", 0)
        
        if interactions_since_nudge >= config.nudge.cooldown_interactions:
            session["last_nudge_time"] = current_time
            session["last_nudge_interaction"] = session["interaction_count"]
            return True
        
        return False
    
    def get_nudge_message(self) -> str:
        """Get the configured nudge message."""
        return config.nudge.message
    
    def has_gold_keywords(self, text: str) -> bool:
        """Check if text contains gold investment keywords from config."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in config.nudge.keywords)
    
    def get_gold_nudge_data(self) -> dict:
        """Get gold investment nudge message and link."""
        return {
            "message": "💰 Interested in gold investment? Discover smart gold investment options with Simplify Money!",
            "link": "/v1/gold/invest",
            "display_text": "Explore Gold Investment Options"
        }


# Global nudge manager instance
nudge_manager = NudgeManager()