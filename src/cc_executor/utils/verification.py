"""
Verification utilities for detecting hallucinations in large outputs.

Since Claude transcripts truncate large outputs, we need alternative methods
to verify that claimed outputs actually happened.
"""

import os
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from loguru import logger


class OutputVerifier:
    """Verifies that claimed outputs actually occurred, preventing hallucinations."""
    
    def __init__(self, output_dir: str = "test_outputs"):
        """
        Initialize verifier with output directory.
        
        Args:
            output_dir: Directory where test outputs are saved
        """
        self.output_dir = output_dir
        
    def create_verification_marker(self, test_id: str) -> str:
        """
        Create a unique verification marker for a test.
        
        Args:
            test_id: Identifier for the test
            
        Returns:
            Unique marker string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        marker = f"VERIFY_{test_id}_{timestamp}"
        logger.info(f"Created verification marker: {marker}")
        return marker
        
    def verify_output_exists(self, filename: str, expected_size_min: int = 0) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify that an output file exists and meets size requirements.
        
        Args:
            filename: Name of the output file
            expected_size_min: Minimum expected file size in bytes
            
        Returns:
            Tuple of (success, details_dict)
        """
        filepath = os.path.join(self.output_dir, filename)
        
        if not os.path.exists(filepath):
            return False, {"error": "File does not exist", "path": filepath}
            
        size = os.path.getsize(filepath)
        if size < expected_size_min:
            return False, {
                "error": "File too small",
                "actual_size": size,
                "expected_min": expected_size_min
            }
            
        # Calculate checksum
        with open(filepath, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
            
        return True, {
            "path": filepath,
            "size": size,
            "checksum": checksum,
            "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
        }
        
    def verify_content_contains(self, filename: str, expected_content: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify that a file contains expected content.
        
        Args:
            filename: Name of the output file
            expected_content: Content that should exist in the file
            
        Returns:
            Tuple of (success, details_dict)
        """
        filepath = os.path.join(self.output_dir, filename)
        
        if not os.path.exists(filepath):
            return False, {"error": "File does not exist", "path": filepath}
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if expected_content in content:
                # Find line number for better reporting
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if expected_content in line:
                        return True, {
                            "found": True,
                            "line_number": i,
                            "context": line[:100] + "..." if len(line) > 100 else line
                        }
                        
            return False, {"error": "Content not found", "searched_for": expected_content}
            
        except Exception as e:
            return False, {"error": f"Failed to read file: {str(e)}"}
            
    def create_verification_report(self, test_name: str, claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a comprehensive verification report for a test.
        
        Args:
            test_name: Name of the test
            claims: Dictionary of claimed results
            
        Returns:
            Verification report
        """
        report = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "claims": claims,
            "verifications": {}
        }
        
        # Verify output file if claimed
        if "output_file" in claims:
            exists, details = self.verify_output_exists(
                claims["output_file"],
                claims.get("min_size", 0)
            )
            report["verifications"]["file_exists"] = {
                "success": exists,
                "details": details
            }
            
        # Verify content markers if claimed
        if "content_markers" in claims:
            for marker in claims["content_markers"]:
                if "output_file" in claims:
                    contains, details = self.verify_content_contains(
                        claims["output_file"],
                        marker
                    )
                    report["verifications"][f"contains_{marker[:20]}"] = {
                        "success": contains,
                        "details": details
                    }
                    
        # Overall verification status
        all_verified = all(
            v["success"] for v in report["verifications"].values()
        )
        report["verified"] = all_verified
        
        # Save report
        report_file = f"verification_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(self.output_dir, report_file)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Verification report saved: {report_path}")
        logger.info(f"Verification result: {'PASSED' if all_verified else 'FAILED'}")
        
        return report


def verify_no_hallucination(test_name: str, output_file: str, expected_markers: list) -> bool:
    """
    Quick helper to verify a test didn't hallucinate its results.
    
    Args:
        test_name: Name of the test
        output_file: Expected output filename
        expected_markers: List of strings that should appear in output
        
    Returns:
        True if verified, False if hallucination detected
    """
    verifier = OutputVerifier()
    
    claims = {
        "output_file": output_file,
        "min_size": 100,  # At least 100 bytes
        "content_markers": expected_markers
    }
    
    report = verifier.create_verification_report(test_name, claims)
    
    if not report["verified"]:
        logger.error(f"HALLUCINATION DETECTED in {test_name}!")
        logger.error(f"Failed verifications: {report['verifications']}")
        
    return report["verified"]


if __name__ == "__main__":
    """Example usage demonstrating verification."""
    
    # Create test output directory
    os.makedirs("test_outputs", exist_ok=True)
    
    # Simulate a test that creates output
    test_file = "test_outputs/example_test.txt"
    with open(test_file, 'w') as f:
        f.write("Test output\n")
        f.write("VERIFY_MARKER_12345\n")
        f.write("More content here\n")
    
    # Verify the output
    print("=== Verification Example ===\n")
    
    # This should pass
    result = verify_no_hallucination(
        "example_test",
        "example_test.txt",
        ["VERIFY_MARKER_12345", "Test output"]
    )
    print(f"Verification passed: {result}\n")
    
    # This should fail (hallucination)
    result = verify_no_hallucination(
        "hallucination_test",
        "nonexistent_file.txt",
        ["This doesn't exist"]
    )
    print(f"Hallucination detected: {not result}")