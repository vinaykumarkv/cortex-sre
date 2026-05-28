# test_healer.py - Pytest for self-healing loops
import os
import sys
import pytest

# Add backend directory to sys path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from healer import CodeHealer

@pytest.fixture
def healer_env():
    """Initializes healer and ensures target app starts in a buggy state."""
    healer = CodeHealer()
    healer.restore_bug()
    yield healer
    healer.restore_bug() # Cleanup and restore bug after test

def test_initial_failure(healer_env):
    """Verifies that the target suite initially fails due to the division by zero bug."""
    passed, stdout = healer_env.run_test_suite()
    assert not passed, "Target test suite should initially fail due to buggy code."
    assert "ZeroDivisionError" in stdout, "Traceback should indicate ZeroDivisionError."

def test_healing_success(healer_env):
    """Verifies that the self-healing logic successfully repairs the bug and passes unit tests."""
    # Run the self-healing orchestration loop
    result = healer_env.self_heal_incident({"issue_id": "SEN-404"})
    
    # Assert successful resolution
    assert result["success"], f"Self-healing failed: {result.get('error')}"
    assert result["attempts"] == 1, "Should heal ZeroDivisionError in a single attempt."
    assert "reviews" in result["patch"], "Healed code should contain the patch check."
    
    # Verify that the post-heal test run passes
    post_heal_passed, post_heal_output = healer_env.run_test_suite()
    assert post_heal_passed, "Post-heal test runner should return 0 (all tests passing)."
    assert "passed" in post_heal_output.lower()
