#!/usr/bin/env python3
"""
Create comprehensive test data for knowledge building scenarios
"""
import asyncio
import json
from datetime import datetime, timedelta
import random
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_arango_tools import query, insert, edge, upsert

async def create_knowledge_test_data():
    """Create test data for scenarios 11-15"""
    print("Creating knowledge building test data...")
    
    # Base timestamp for today
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Create error patterns for the week
    error_types = [
        {"type": "ModuleNotFoundError", "module": "numpy", "fix": "uv add numpy"},
        {"type": "ModuleNotFoundError", "module": "pandas", "fix": "uv add pandas"},
        {"type": "ImportError", "module": "tensorflow", "fix": "pip install tensorflow"},
        {"type": "AttributeError", "attr": "read_csv", "fix": "Check pandas version"},
        {"type": "TypeError", "message": "unsupported operand", "fix": "Cast to numeric"},
        {"type": "ConnectionError", "service": "Redis", "fix": "Start Redis server"},
        {"type": "TimeoutError", "service": "API", "fix": "Increase timeout"},
        {"type": "FileNotFoundError", "file": "config.json", "fix": "Create config file"}
    ]
    
    # Performance patterns
    tool_performance = [
        {"tool": "grep", "avg_ms": 150, "success_rate": 0.95},
        {"tool": "ripgrep", "avg_ms": 50, "success_rate": 0.98},
        {"tool": "find", "avg_ms": 300, "success_rate": 0.85},
        {"tool": "ag", "avg_ms": 80, "success_rate": 0.92},
        {"tool": "sed", "avg_ms": 100, "success_rate": 0.90},
        {"tool": "awk", "avg_ms": 120, "success_rate": 0.88}
    ]
    
    # Team members and their fix approaches
    team_members = ["Alice", "Bob", "Charlie"]
    fix_approaches = {
        "ModuleNotFoundError": [
            {"member": "Alice", "approach": "uv add", "success_rate": 0.95, "time_ms": 2000},
            {"member": "Bob", "approach": "pip install", "success_rate": 0.85, "time_ms": 3000},
            {"member": "Charlie", "approach": "conda install", "success_rate": 0.90, "time_ms": 2500}
        ],
        "ConnectionError": [
            {"member": "Alice", "approach": "systemctl restart", "success_rate": 0.80, "time_ms": 1000},
            {"member": "Bob", "approach": "docker restart", "success_rate": 0.95, "time_ms": 1500},
            {"member": "Charlie", "approach": "manual start", "success_rate": 0.70, "time_ms": 500}
        ]
    }
    
    # Create errors over the past week
    for day_offset in range(7, -1, -1):  # 7 days ago to today
        day = now - timedelta(days=day_offset)
        day_str = day.strftime("%Y-%m-%d")
        
        # Decreasing error frequency as we improve
        num_errors = random.randint(10-day_offset, 15-day_offset) if day_offset > 0 else random.randint(2, 5)
        
        for i in range(max(1, num_errors)):
            error = random.choice(error_types)
            error_time = day + timedelta(hours=random.randint(8, 18), minutes=random.randint(0, 59))
            
            # Insert error
            error_result = await insert(
                message=f"{error['type']}: {error.get('module', error.get('attr', error.get('service', error.get('file', 'unknown'))))}",
                level="ERROR",
                error_type=error['type'],
                script_name=f"script_{random.randint(1, 10)}.py",
                metadata=json.dumps({
                    "day": day_str,
                    "resolved": random.random() > 0.3,  # 70% resolved
                    "fix_applied": error['fix'] if random.random() > 0.3 else None,
                    "team_member": random.choice(team_members) if random.random() > 0.5 else None
                })
            )
            
            # Create tool executions with performance data
            for j in range(random.randint(1, 3)):
                tool = random.choice(tool_performance)
                exec_time = tool['avg_ms'] + random.randint(-50, 50)
                success = random.random() < tool['success_rate']
                
                exec_result = await upsert(
                    collection="tool_executions",
                    search=json.dumps({
                        "session_id": f"session_{day_str}_{i}",
                        "tool_name": tool['tool']
                    }),
                    update=json.dumps({
                        "duration_ms": exec_time,
                        "status": "success" if success else "failed",
                        "start_time": error_time.isoformat(),
                        "exit_code": 0 if success else 1
                    })
                )
    
    # Create lessons learned
    lessons = [
        {
            "lesson": "Always use uv instead of pip for better dependency resolution",
            "category": "dependency_management",
            "applies_to": ["ModuleNotFoundError", "ImportError"],
            "confidence": 0.95,
            "evidence_count": 25
        },
        {
            "lesson": "Ripgrep is 3x faster than grep for large codebases",
            "category": "performance",
            "applies_to": ["search_operations", "code_analysis"],
            "confidence": 0.98,
            "evidence_count": 150
        },
        {
            "lesson": "Docker containers provide more reliable service management",
            "category": "infrastructure",
            "applies_to": ["ConnectionError", "TimeoutError"],
            "confidence": 0.90,
            "evidence_count": 45
        },
        {
            "lesson": "Type hints prevent 80% of TypeError issues",
            "category": "code_quality",
            "applies_to": ["TypeError", "AttributeError"],
            "confidence": 0.85,
            "evidence_count": 60
        },
        {
            "lesson": "Async operations reduce API timeout errors by 60%",
            "category": "performance",
            "applies_to": ["TimeoutError", "ConnectionError"],
            "confidence": 0.88,
            "evidence_count": 30
        }
    ]
    
    for lesson in lessons:
        await upsert(
            collection="lessons_learned",
            search=json.dumps({"lesson": lesson["lesson"]}),
            update=json.dumps(lesson)
        )
    
    # Create solution outcomes
    for error_type, approaches in fix_approaches.items():
        for approach in approaches:
            outcome = await upsert(
                collection="solution_outcomes",
                search=json.dumps({
                    "solution_id": f"{error_type}_{approach['member']}_{approach['approach'].replace(' ', '_')}"
                }),
                update=json.dumps({
                    "outcome": "success" if approach['success_rate'] > 0.8 else "partial",
                    "key_reason": f"{approach['member']}'s approach using {approach['approach']}",
                    "category": error_type,
                    "success_score": approach['success_rate'],
                    "applied_at": now.isoformat(),
                    "team_member": approach['member'],
                    "approach": approach['approach'],
                    "avg_time_ms": approach['time_ms']
                })
            )
    
    # Create performance bottleneck data
    bottlenecks = [
        {
            "operation": "file_search",
            "tool": "find",
            "avg_duration_ms": 3000,
            "occurrences": 45,
            "impact": "high",
            "recommendation": "Switch to ripgrep for 6x speedup"
        },
        {
            "operation": "dependency_install",
            "tool": "pip",
            "avg_duration_ms": 5000,
            "occurrences": 30,
            "impact": "medium",
            "recommendation": "Use uv for faster resolution"
        },
        {
            "operation": "service_restart",
            "tool": "systemctl",
            "avg_duration_ms": 2000,
            "occurrences": 20,
            "impact": "low",
            "recommendation": "Consider Docker for isolation"
        }
    ]
    
    for bottleneck in bottlenecks:
        await insert(
            message=f"Performance bottleneck: {bottleneck['operation']} using {bottleneck['tool']}",
            level="INFO",
            metadata=json.dumps(bottleneck)
        )
    
    # Create collaborative insights
    insights = [
        {
            "content": "Team comparison shows Docker-based fixes have 95% success rate vs 70% for manual restarts",
            "confidence": 0.92,
            "context": "infrastructure_management",
            "tags": ["docker", "reliability", "team_learning"]
        },
        {
            "content": "Alice's uv-based approach resolves dependencies 33% faster than pip",
            "confidence": 0.88,
            "context": "dependency_management",
            "tags": ["performance", "tools", "best_practice"]
        },
        {
            "content": "Error frequency decreased 65% after implementing type hints",
            "confidence": 0.85,
            "context": "code_quality",
            "tags": ["prevention", "type_safety", "metrics"]
        }
    ]
    
    for insight in insights:
        await upsert(
            collection="agent_insights",
            search=json.dumps({"content": insight["content"]}),
            update=json.dumps({
                **insight,
                "session_id": f"analysis_{now.strftime('%Y%m%d')}",
                "created_at": now.isoformat()
            })
        )
    
    print("✓ Created comprehensive knowledge building test data")
    print("  - Errors over 7 days with decreasing frequency")
    print("  - Tool performance metrics")
    print("  - Team member fix approaches")
    print("  - Lessons learned")
    print("  - Solution outcomes")
    print("  - Performance bottlenecks")
    print("  - Collaborative insights")

if __name__ == "__main__":
    asyncio.run(create_knowledge_test_data())