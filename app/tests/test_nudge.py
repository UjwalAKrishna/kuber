import pytest
from utils.nudge import NudgeManager


def test_nudge_manager_basic():
    """Test basic nudge manager functionality."""
    manager = NudgeManager()
    
    # First interaction with function call should trigger nudge
    assert manager.should_nudge("session1", True) == True
    
    # Second interaction should not trigger nudge (cooldown)
    assert manager.should_nudge("session1", True) == False
    
    # Third interaction should trigger nudge again
    assert manager.should_nudge("session1", True) == True


def test_nudge_manager_no_function_call():
    """Test nudge manager when no function call is present."""
    manager = NudgeManager()
    
    # No function call should never trigger nudge
    assert manager.should_nudge("session1", False) == False
    assert manager.should_nudge("session1", False) == False


def test_nudge_manager_different_sessions():
    """Test nudge manager with different sessions."""
    manager = NudgeManager()
    
    # Different sessions should be independent
    assert manager.should_nudge("session1", True) == True
    assert manager.should_nudge("session2", True) == True
    
    # Cooldown should be per session
    assert manager.should_nudge("session1", True) == False
    assert manager.should_nudge("session2", True) == False


def test_nudge_message():
    """Test nudge message retrieval."""
    manager = NudgeManager()
    message = manager.get_nudge_message()
    
    assert "digital gold" in message.lower()
    assert "simplify" in message.lower()