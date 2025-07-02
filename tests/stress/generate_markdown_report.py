#!/usr/bin/env python3
"""
Generate a markdown report from the comprehensive stress test results.
"""

import json
import sys
import os
from datetime import datetime

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from markdown_report_generator import MarkdownReportGenerator

# Load the latest test results
results_dir = "/home/graham/workspace/experiments/cc_executor/test_results/stress/logs"
report_file = "report_20250630_144439.json"

with open(os.path.join(results_dir, report_file), 'r') as f:
    results = json.load(f)

# Convert to format expected by generator
formatted_results = {
    "total_tests": results["total"],
    "successful_tests": results["passed"],
    "failed_tests": results["failed"],
    "total_duration": sum(t["duration"] for t in results["tests"]),
    "categories": {
        "all_tests": results["tests"]
    }
}

# Generate markdown report
generator = MarkdownReportGenerator()
markdown_report = generator.generate_report(
    formatted_results,
    title="Comprehensive WebSocket Stress Test Report",
    include_responses=False
)

# Add additional details for each test
additional_details = []
additional_details.append("\n## Test Details\n")

for test in results["tests"]:
    status = "✅" if test["success"] else "❌"
    additional_details.append(f"### {status} {test['name']}\n")
    additional_details.append(f"- **Duration:** {test['duration']:.2f}s")
    
    if "exit_code" in test:
        additional_details.append(f"- **Exit Code:** {test['exit_code']}")
    
    if "output_size" in test:
        additional_details.append(f"- **Output Size:** {test['output_size']} bytes")
        
    if "word_count" in test:
        additional_details.append(f"- **Word Count:** {test['word_count']}")
        
    if "valid_json_lines" in test:
        additional_details.append(f"- **Valid JSON Lines:** {test['valid_json_lines']}/{test['total_lines']}")
        
    if "has_streaming" in test:
        additional_details.append(f"- **Streaming:** {'Yes' if test['has_streaming'] else 'No'}")
        
    if "error" in test:
        additional_details.append(f"- **Error:** {test['error'] or 'None'}")
        
    if "timed_out" in test:
        additional_details.append(f"- **Timed Out:** {'Yes' if test['timed_out'] else 'No'}")
        
    if "successful_requests" in test:
        additional_details.append(f"- **Successful Requests:** {test['successful_requests']}/{test['requests']}")
        
    additional_details.append("\n")

# Combine report with additional details
full_report = markdown_report + "\n".join(additional_details)

# Add failure analysis
full_report += """
## Failure Analysis

### Common Issues

1. **Claude CLI Exit Code 1**: Most tests failed with exit code 1, indicating:
   - Missing API key (ANTHROPIC_API_KEY not set)
   - Rate limiting
   - Invalid command syntax

2. **Low Success Rate (44.4%)**: 
   - 5 out of 9 tests failed
   - All Claude-dependent tests failed
   - Only infrastructure tests passed

### Successful Tests
- ✅ **JSON Streaming Validation**: WebSocket properly handles JSON streaming
- ✅ **Error Handling**: Errors are properly caught and handled
- ✅ **Environment Validation**: Environment variables correctly set
- ✅ **Buffer Chunking**: Large outputs properly chunked

### Failed Tests
- ❌ **Claude-dependent tests**: All tests requiring Claude API failed
- ❌ **Concurrent Requests**: 0/3 concurrent requests succeeded

## Recommendations

1. **Set ANTHROPIC_API_KEY**: Export the API key before running tests
2. **Check Rate Limits**: Ensure API quota is available
3. **Review Command Syntax**: Verify Claude CLI command format
4. **Add Retry Logic**: Implement adaptive retry for rate limits
5. **Mock Tests**: Consider mocked tests for CI/CD environments

## Test Environment

- **Date:** 2025-06-30
- **Time:** 14:44:20 - 14:44:39
- **Duration:** 7.2 seconds
- **WebSocket Handler:** Successfully started
- **MCP Config:** Found at `.mcp.json`
- **API Key:** Not set (WARNING)
"""

# Save the markdown report
output_file = os.path.join(
    "/home/graham/workspace/experiments/cc_executor/test_results/stress/reports",
    f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
)

os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w') as f:
    f.write(full_report)

print(f"Markdown report generated: {output_file}")
print("\n" + "="*60)
print("Report Preview:")
print("="*60)
print(full_report[:1000] + "...")