#!/usr/bin/env python3
"""Helper to update test report incrementally after each scenario."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class TestReportUpdater:
    def __init__(self, report_path: str = "arango_tools_test_report.md"):
        self.report_path = Path(report_path)
        self.stats = {
            "total_scenarios": 20,
            "completed": 0,
            "in_progress": 0,
            "failed": 0,
            "tool_calls": {
                "schema": {"total": 0, "successful": 0},
                "query": {"total": 0, "successful": 0},
                "insert": {"total": 0, "successful": 0},
                "edge": {"total": 0, "successful": 0},
                "upsert": {"total": 0, "successful": 0}
            },
            "errors": [],
            "performance": {
                "total_time_ms": 0,
                "operations": []
            },
            "knowledge_growth": {
                "documents": 0,
                "edges": 0,
                "insights": 0,
                "lessons": 0
            }
        }
    
    def update_scenario(self, scenario_num: int, status: str, results: Dict[str, Any]):
        """Update a specific scenario's results in the report."""
        # This would update the markdown file with the scenario results
        # Including:
        # - Status (completed/failed)
        # - Tool calls made
        # - Errors encountered
        # - Knowledge gained
        # - Performance metrics
        pass
    
    def increment_tool_usage(self, tool_name: str, success: bool, response_time_ms: float):
        """Track tool usage statistics."""
        if tool_name in self.stats["tool_calls"]:
            self.stats["tool_calls"][tool_name]["total"] += 1
            if success:
                self.stats["tool_calls"][tool_name]["successful"] += 1
        
        self.stats["performance"]["operations"].append({
            "tool": tool_name,
            "success": success,
            "time_ms": response_time_ms,
            "timestamp": datetime.now().isoformat()
        })
        self.stats["performance"]["total_time_ms"] += response_time_ms
    
    def add_error(self, error_type: str, error_message: str, recovery_method: str = None):
        """Log an error and how it was recovered."""
        self.stats["errors"].append({
            "type": error_type,
            "message": error_message,
            "recovery": recovery_method,
            "timestamp": datetime.now().isoformat()
        })
    
    def update_knowledge_growth(self, doc_delta: int = 0, edge_delta: int = 0, 
                               insight_delta: int = 0, lesson_delta: int = 0):
        """Track knowledge base growth."""
        self.stats["knowledge_growth"]["documents"] += doc_delta
        self.stats["knowledge_growth"]["edges"] += edge_delta
        self.stats["knowledge_growth"]["insights"] += insight_delta
        self.stats["knowledge_growth"]["lessons"] += lesson_delta
    
    def generate_summary(self) -> str:
        """Generate current summary statistics."""
        avg_time = (self.stats["performance"]["total_time_ms"] / 
                   len(self.stats["performance"]["operations"]) 
                   if self.stats["performance"]["operations"] else 0)
        
        summary = f"""
## Current Statistics

### Progress
- Completed: {self.stats['completed']}/{self.stats['total_scenarios']}
- Success Rate: {(self.stats['completed'] - self.stats['failed']) / max(1, self.stats['completed']) * 100:.1f}%

### Tool Usage
"""
        for tool, usage in self.stats["tool_calls"].items():
            if usage["total"] > 0:
                success_rate = usage["successful"] / usage["total"] * 100
                summary += f"- {tool}(): {usage['total']} calls ({success_rate:.0f}% success)\n"
        
        summary += f"""
### Performance
- Total Operations: {len(self.stats['performance']['operations'])}
- Average Response Time: {avg_time:.0f}ms
- Total Execution Time: {self.stats['performance']['total_time_ms']:.0f}ms

### Knowledge Growth
- Documents: +{self.stats['knowledge_growth']['documents']}
- Edges: +{self.stats['knowledge_growth']['edges']}
- Insights: +{self.stats['knowledge_growth']['insights']}
- Lessons: +{self.stats['knowledge_growth']['lessons']}

### Errors: {len(self.stats['errors'])}
"""
        return summary

# Usage example:
# updater = TestReportUpdater()
# updater.increment_tool_usage("query", True, 45.2)
# updater.update_scenario(1, "completed", {...})
# print(updater.generate_summary())