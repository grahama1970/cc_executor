#!/usr/bin/env python3
"""
Execute the KV Store example with automatic UUID4 verification via hooks.
This demonstrates how hooks transparently add anti-hallucination measures.
"""
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add project to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

def main():
    """Execute task list with automatic UUID4 injection via hooks."""
    print("="*60)
    print("CC Executor - UUID4 Verification Example")
    print("Building a KV Store API with automatic anti-hallucination")
    print("="*60)
    
    # Set hook configuration path
    hook_config = Path(__file__).parent / '.claude-hooks.json'
    os.environ['CLAUDE_HOOKS_CONFIG'] = str(hook_config)
    
    print(f"\n📎 Hooks configured from: {hook_config}")
    print("   - Pre-hook will inject UUID4 requirements")
    print("   - Post-hook will verify UUID4 presence")
    print("   - Task descriptions remain clean and simple!")
    
    # Define tasks - NO UUID4 mentioned!
    tasks = [
        {
            'num': 1,
            'name': 'Create KV Store API',
            'desc': '''Create a FastAPI key-value store in folder `kv_store/` with file `main.py` containing:
- POST /set - Set a key-value pair
- GET /get/{key} - Get value by key
- DELETE /delete/{key} - Delete a key
- GET /keys - List all keys

Use a simple dictionary for in-memory storage.''',
            'timeout': 90
        },
        {
            'num': 2,
            'name': 'Add Persistence',
            'desc': '''How can I add file-based persistence to the KV store? Read `kv_store/main.py` and modify it to save the dictionary to `kv_store/data.json` after each modification. Load existing data on startup if the file exists.''',
            'timeout': 90
        },
        {
            'num': 3,
            'name': 'Write Tests',
            'desc': '''What tests should I write for the KV store API? Read the implementation in `kv_store/main.py` and create `kv_store/test_kv_store.py` with pytest tests covering all endpoints and persistence functionality.''',
            'timeout': 120
        }
    ]
    
    # Create output directories
    output_dir = Path("tmp/responses")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Execute each task
    results = []
    all_uuids = []
    
    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task {task['num']}: {task['name']}")
        print(f"{'='*60}")
        print(f"Original task (before hooks):")
        print(f"{task['desc'][:200]}...")
        print(f"\n🪝 Hooks will automatically add UUID4 requirements!")
        print(f"\nExecuting with {task['timeout']}s timeout...")
        
        # Execute task - hooks will modify it automatically
        result = execute_task_via_websocket(
            task=task['desc'],
            timeout=task['timeout'],
            tools=["Read", "Write", "Edit"],
            task_metadata={'task_number': task['num']}
        )
        
        # Save result
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"task_{task['num']}_{timestamp}.json"
        
        # Add task metadata to result
        result['task_metadata'] = {
            'number': task['num'],
            'name': task['name'],
            'timestamp': timestamp
        }
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        status = result.get('status', 'unknown')
        duration = result.get('duration', 0)
        
        # Check for UUID in result
        uuid_verified = False
        if 'post_hook_results' in result:
            for hook_result in result.get('post_hook_results', []):
                if 'verification_report' in hook_result:
                    report = hook_result['verification_report']
                    if report.get('uuid_found_in_output'):
                        uuid_verified = True
                        all_uuids.append(report.get('expected_uuid'))
        
        results.append({
            'task': task['name'],
            'status': status,
            'duration': duration,
            'uuid_verified': uuid_verified
        })
        
        print(f"\n✅ Task completed: {status} ({duration:.1f}s)")
        print(f"   UUID verified: {'✅ Yes' if uuid_verified else '❌ No'}")
        print(f"   Output saved to: {output_file}")
        
        if status != 'success':
            print(f"\n❌ Task failed. Check output file for details.")
            break
    
    # Summary Report
    print(f"\n{'='*60}")
    print("EXECUTION SUMMARY")
    print(f"{'='*60}")
    
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r['status'] == 'success' else "❌"
        uuid_icon = "🔐" if r['uuid_verified'] else "⚠️"
        print(f"{status_icon} Task {i}: {r['task']}")
        print(f"   Status: {r['status']} ({r['duration']:.1f}s)")
        print(f"   {uuid_icon} UUID: {'Verified' if r['uuid_verified'] else 'NOT VERIFIED'}")
    
    # UUID Verification Summary
    print(f"\n{'='*60}")
    print("UUID VERIFICATION SUMMARY")
    print(f"{'='*60}")
    
    if all_uuids:
        print(f"✅ {len(all_uuids)} UUIDs generated and tracked:")
        for i, uuid in enumerate(all_uuids, 1):
            print(f"   Task {i}: {uuid}")
        
        print("\nTo verify in transcripts:")
        print("```bash")
        for uuid in all_uuids:
            print(f'rg "{uuid}" ~/.claude/projects/*/\\*.jsonl')
        print("```")
    else:
        print("❌ No UUIDs were verified - possible hallucination!")
    
    # Final verification
    if all(r['status'] == 'success' and r['uuid_verified'] for r in results):
        print(f"\n{'='*60}")
        print("✅ ALL TASKS COMPLETED WITH UUID VERIFICATION")
        print(f"{'='*60}")
        
        # Create final report
        report = {
            "title": "KV Store API - UUID4 Verification Report",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tasks": len(results),
                "successful": sum(1 for r in results if r['status'] == 'success'),
                "uuid_verified": sum(1 for r in results if r['uuid_verified']),
                "all_uuids": all_uuids
            },
            "tasks": results,
            "verification_note": "All tasks executed with automatic UUID4 injection via hooks"
        }
        
        report_file = reports_dir / f"uuid_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Final report saved to: {report_file}")
        print("\n🎉 Success! The hooks automatically added anti-hallucination measures")
        print("   without requiring any changes to the task descriptions!")

if __name__ == "__main__":
    main()