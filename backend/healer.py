# healer.py - Self-Healing Code Engine
import os
import subprocess
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class CodeHealer:
    """
    CodeHealer automates local code repair.
    It runs tests, captures failures, prompts a simulated/real LLM patcher,
    re-applies the fix, and runs tests again recursively up to max_retries.
    """
    def __init__(self, target_dir=None):
        if target_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.target_dir = os.path.join(project_root, "demo_data", "workspace_target")
        else:
            self.target_dir = target_dir
        self.app_file = os.path.join(self.target_dir, "app.py")
        self.test_file = os.path.join(self.target_dir, "test_app.py")

    def run_test_suite(self):
        """Runs the pytest suite on the target directory and captures the stdout."""
        logger.info(f"Running test suite in {self.target_dir}...")
        try:
            # Run pytest on the target test file
            result = subprocess.run(
                ["pytest", self.test_file],
                cwd=self.target_dir,
                capture_output=True,
                text=True,
                shell=True
            )
            # pytest returns 0 if all pass, >0 if there are failures
            return result.returncode == 0, result.stdout
        except Exception as e:
            logger.error(f"Failed to execute test suite: {e}")
            return False, str(e)

    def self_heal_incident(self, incident_details, max_retries=3):
        """
        Orchestrates the healing loop:
          1. Runs tests to confirm failure.
          2. Parses stack trace.
          3. Generates a targeted code fix (simulating an LLM healer).
          4. Applies patch.
          5. Re-runs tests to verify.
        """
        logger.info(f"Initiating self-healing loop for incident {incident_details.get('issue_id')}...")
        
        # Step 1: Verify current failure status
        passed, test_output = self.run_test_suite()
        if passed:
            logger.info("Test suite is already passing! No healing required.")
            return {
                "success": True,
                "attempts": 0,
                "patch": "None (tests already passing)",
                "test_output": test_output
            }
            
        logger.warning("Test suite failed. Commencing automated repair iterations...")
        
        attempt = 0
        current_error_logs = test_output
        
        while attempt < max_retries:
            attempt += 1
            logger.info(f"Healing Attempt #{attempt} of {max_retries}...")
            
            # Step 2: Simulated LLM Patcher
            # In a live product, we would call `gemini-3.5-flash` or similar, feeding it:
            # (a) The original buggy file content
            # (b) The failing pytest traceback
            # Here we simulate the LLM output based on the traceback content.
            patch_content, fix_explanation = self._generate_patch(current_error_logs)
            
            if not patch_content:
                logger.error("Simulated LLM patch generation failed to match any known traceback.")
                return {
                    "success": False,
                    "attempts": attempt,
                    "error": "Failed to generate patch"
                }

            # Step 3: Apply the code patch
            logger.info(f"Applying patch to {self.app_file}...")
            self._apply_patch(patch_content)
            
            # Step 4: Re-run test suite
            passed, post_patch_output = self.run_test_suite()
            
            if passed:
                logger.info(f"Self-healing SUCCESSFUL on Attempt #{attempt}! All unit tests are green.")
                return {
                    "success": True,
                    "attempts": attempt,
                    "patch": patch_content,
                    "explanation": fix_explanation,
                    "test_output": post_patch_output
                }
            else:
                logger.warning(f"Attempt #{attempt} failed. Retrying code analysis with new test failures...")
                current_error_logs = post_patch_output
                
        logger.error(f"Self-healing FAILED after {max_retries} attempts.")
        return {
            "success": False,
            "attempts": max_retries,
            "error": "Max retries reached without passing tests",
            "test_output": current_error_logs
        }

    def _generate_patch(self, traceback_logs):
        """Ollama (llama3.2) when enabled, else rule-based demo patch."""
        from config import use_ollama

        if use_ollama():
            try:
                from llm.ollama_client import generate_patch, is_available
                if is_available():
                    with open(self.app_file, "r", encoding="utf-8") as f:
                        source = f.read()
                    patch, explanation = generate_patch(source, traceback_logs)
                    if patch and patch.strip():
                        logger.info("Ollama generated patch successfully.")
                        return patch, explanation
                else:
                    logger.warning("Ollama not reachable or model missing; using rule-based patch.")
            except Exception as e:
                logger.warning("Ollama patch failed (%s); using rule-based patch.", e)

        return self._generate_simulated_llm_patch(traceback_logs)

    def _generate_simulated_llm_patch(self, traceback_logs):
        """
        Simulates the cognitive step of an LLM identifying the bug inapp.py
        from the pytest traceback logs and writing a drop-in replacement.
        """
        # Case 1: ZeroDivisionError
        if "ZeroDivisionError" in traceback_logs or "division by zero" in traceback_logs:
            logger.info("Cognitive Engine matched: 'ZeroDivisionError: division by zero' in app.py")
            
            fixed_code = """# app.py - Production Product Rating Service
def calculate_product_rating(reviews):
    \"\"\"
    Calculates the average rating from a list of review dictionaries.
    Each review has a 'score' key containing an integer from 1 to 5.
    \"\"\"
    if not reviews:
        # Handle zero-rating division scenario gracefully
        return 0.0
        
    total_score = sum(review['score'] for review in reviews)
    count = len(reviews)
    
    average = total_score / count
    return average
"""
            explanation = "Added an explicit guard check `if not reviews: return 0.0` at the entry of the rating calculation function to prevent ZeroDivisionError when review array length is 0."
            return fixed_code, explanation

        # Fallback case: General syntax or generic repair
        logger.warning("Traceback did not match standard Sentry demonstration pattern.")
        return None, None

    def _apply_patch(self, new_content):
        """Safely overwrites the app.py with the patched code."""
        with open(self.app_file, "w") as f:
            f.write(new_content)

    def restore_bug(self):
        """Resets app.py back to its buggy state to allow repeating the demo."""
        buggy_code = """# app.py - Production Product Rating Service
def calculate_product_rating(reviews):
    \"\"\"
    Calculates the average rating from a list of review dictionaries.
    Each review has a 'score' key containing an integer from 1 to 5.
    \"\"\"
    total_score = sum(review['score'] for review in reviews)
    count = len(reviews)
    
    # CRITICAL BUG: Raises ZeroDivisionError when reviews list is empty!
    average = total_score / count
    return average
"""
        with open(self.app_file, "w") as f:
            f.write(buggy_code)
        logger.info("Target file app.py restored to buggy state for fresh demo runs.")

if __name__ == "__main__":
    # Local dry-run of healer
    logging.basicConfig(level=logging.INFO)
    healer = CodeHealer()
    healer.restore_bug()
    print("Testing local healing...")
    res = healer.self_heal_incident({"issue_id": "SEN-404"})
    print("Healer outcome:", res["success"], "Attempts:", res["attempts"])
