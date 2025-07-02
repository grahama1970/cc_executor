#!/usr/bin/env python3
"""Generate an easy-to-read aggregated report from stress test results."""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        return f"{int(seconds//60)}m {seconds%60:.1f}s"

def generate_report(test_dir: Path):
    """Generate aggregated report from test outputs."""
    
    # Find the most recent report JSON
    report_files = list(test_dir.glob("report_*.json"))
    if not report_files:
        print(f"❌ No report files found in {test_dir}")
        return
    
    latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
    
    # Load report data
    with open(latest_report) as f:
        report_data = json.load(f)
    
    # Print header
    print("\n" + "="*80)
    print("📊 STRESS TEST AGGREGATED REPORT")
    print("="*80)
    print(f"Report: {latest_report.name}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Summary statistics
    total = report_data["success"] + report_data["failure"]
    success_rate = (report_data["success"] / max(1, total)) * 100
    
    print("📈 SUMMARY")
    print("-"*40)
    print(f"Total Tests:    {total}")
    print(f"✅ Passed:      {report_data['success']} ({success_rate:.1f}%)")
    print(f"❌ Failed:      {report_data['failure']} ({100-success_rate:.1f}%)")
    
    # Calculate total time if available
    if "tests" in report_data and report_data["tests"]:
        total_time = sum(t.get("duration", 0) for t in report_data["tests"])
        print(f"⏱️  Total Time:   {format_duration(total_time)}")
    
    print()
    
    # Detailed results by test
    print("📋 DETAILED RESULTS")
    print("-"*80)
    print(f"{'Test ID':<25} {'Status':<10} {'Duration':<12} {'Patterns Found'}")
    print("-"*80)
    
    for test in report_data.get("tests", []):
        test_id = test["id"]
        status = "✅ PASS" if test["success"] else "❌ FAIL"
        duration = format_duration(test.get("duration", 0))
        patterns = ", ".join(test.get("patterns_found", []))[:40]
        if len(patterns) > 40:
            patterns += "..."
            
        print(f"{test_id:<25} {status:<10} {duration:<12} {patterns}")
        
        # Find and display output file
        output_files = list(test_dir.glob(f"{test_id}_*.txt"))
        if output_files:
            latest_output = max(output_files, key=lambda p: p.stat().st_mtime)
            # Make it clickable in VS Code terminal
            file_path = latest_output.absolute()
            print(f"{'':>25} 📄 Output: file://{file_path}")
    
    print()
    
    # Failed tests details
    if report_data["failure"] > 0:
        print("⚠️  FAILED TESTS ANALYSIS")
        print("-"*40)
        failed_tests = [t for t in report_data.get("tests", []) if not t["success"]]
        for test in failed_tests:
            print(f"\n❌ {test['id']}")
            print(f"   Duration: {format_duration(test.get('duration', 0))}")
            print(f"   Expected patterns: {test.get('expected_patterns', 'N/A')}")
            print(f"   Found patterns: {test.get('patterns_found', [])}")
            
            # Find output file for debugging
            output_files = list(test_dir.glob(f"{test['id']}_*.txt"))
            if output_files:
                latest_output = max(output_files, key=lambda p: p.stat().st_mtime)
                print(f"   🔍 Debug: file://{latest_output.absolute()}")
    
    print("\n" + "="*80)
    print("💡 QUICK ACTIONS")
    print("-"*40)
    print(f"📂 All outputs: file://{test_dir.absolute()}")
    print(f"📊 Raw report: file://{latest_report.absolute()}")
    
    if report_data["failure"] > 0:
        print("\n🔧 Debug failed tests:")
        print("   tail -n 50 logs/websocket_handler_*.log | grep ERROR")
    
    print()

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        # Try to find the most recent test output directory
        base_dir = Path("test_outputs")
        if not base_dir.exists():
            print("❌ No test_outputs directory found")
            return
            
        # Look for preflight or local test dirs
        candidates = []
        if (base_dir / "preflight").exists():
            candidates.append(base_dir / "preflight")
        if (base_dir / "local").exists():
            candidates.append(base_dir / "local")
        if (base_dir / "final_run").exists():
            candidates.append(base_dir / "final_run")
            
        if not candidates:
            print("❌ No test output directories found")
            return
            
        # Use the most recently modified
        test_dir = max(candidates, key=lambda p: p.stat().st_mtime)
        print(f"Using most recent test directory: {test_dir}")
    
    generate_report(test_dir)

if __name__ == "__main__":
    main()