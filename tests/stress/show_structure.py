#!/usr/bin/env python3
"""
Show the structure of the new stress test organization.
"""
import json
from pathlib import Path

def show_structure():
    """Display the test structure and counts."""
    base_dir = Path(__file__).parent
    
    print("CC Executor Stress Test Structure")
    print("=" * 50)
    
    configs = [
        ("Simple", "simple_stress_tests.json"),
        ("Medium", "medium_stress_tests.json"),
        ("Complex", "complex_stress_tests.json"),
        ("All", "all_stress_tests.json")
    ]
    
    for name, filename in configs:
        config_path = base_dir / "configs" / filename
        prompt_path = base_dir / "prompts" / filename.replace(".json", "_prompt.md")
        runner_path = base_dir / "runners" / f"run_{filename.replace('.json', '.py')}"
        report_path = base_dir / "reports" / filename.replace(".json", "_report.md")
        
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
            
            if "tests" in data:
                # Simple format
                test_count = len(data["tests"])
                timeout = data.get("timeout", "N/A")
                print(f"\n{name} Tests:")
                print(f"  Config: {config_path.name}")
                print(f"  Tests: {test_count}")
                print(f"  Timeout: {timeout}s")
            else:
                # Categorized format
                total_tests = 0
                categories = []
                for cat_name, cat_data in data.get("categories", {}).items():
                    test_count = len(cat_data.get("tests", []))
                    total_tests += test_count
                    categories.append(f"{cat_name}({test_count})")
                
                print(f"\n{name} Tests:")
                print(f"  Config: {config_path.name}")
                print(f"  Total Tests: {total_tests}")
                print(f"  Categories: {', '.join(categories)}")
            
            print(f"  Prompt: {'✓' if prompt_path.exists() else '✗'} {prompt_path.name}")
            print(f"  Runner: {'✓' if runner_path.exists() else '✗'} {runner_path.name}")
            print(f"  Report: {'✓' if report_path.exists() else 'pending'} {report_path.name}")
    
    print("\n" + "=" * 50)
    print("✓ = File exists")
    print("✗ = File missing")
    print("pending = Will be generated when tests run")

if __name__ == "__main__":
    show_structure()