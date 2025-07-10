"""
Execution receipt generator for cc_execute calls.

Creates a simple markdown receipt for every execution that proves it happened.
This is a lightweight alternative to full assessment reports.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def generate_execution_receipt(
    session_id: str,
    task: str,
    execution_uuid: str,
    response_file: Path,
    output: str,
    execution_time: float,
    exit_code: int
) -> Path:
    """
    Generate a simple execution receipt that proves the call happened.
    
    Returns:
        Path to the receipt file
    """
    timestamp = datetime.now()
    receipt_dir = response_file.parent / "receipts"
    receipt_dir.mkdir(exist_ok=True)
    
    receipt_file = receipt_dir / f"receipt_{session_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
    
    receipt = f"""# CC_EXECUTE Receipt

**Generated**: {timestamp.isoformat()}  
**Session ID**: `{session_id}`  
**Execution UUID**: `{execution_uuid}`  

## Task
```
{task}
```

## Result
- **Exit Code**: {exit_code} {"✅" if exit_code == 0 else "❌"}
- **Execution Time**: {execution_time:.2f}s
- **Output Length**: {len(output)} characters

## Output
```
{output[:500]}{"..." if len(output) > 500 else ""}
```

## Verification
- **Response File**: `{response_file.name}`
- **Full Path**: `{response_file}`

### Quick Verify Command
```bash
cat {response_file}
```

---
*This receipt proves the execution occurred and was not hallucinated.*
"""
    
    with open(receipt_file, 'w') as f:
        f.write(receipt)
    
    return receipt_file