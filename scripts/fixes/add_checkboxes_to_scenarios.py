#!/usr/bin/env python3
"""Add completion checkboxes to all scenarios in the test document."""

import re
from pathlib import Path

# Read the file
file_path = Path("/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/tests/arango_tools_20_scenarios.md")
content = file_path.read_text()

# Define the standard checkbox template
checkbox_template = """- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: {prompt}

**Expected Claude Actions:**
{actions}

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_"""

# Process scenarios 2-20
for i in range(2, 21):
    # Find the scenario pattern
    pattern = rf'### Scenario {i}: ([^\n]+)\n"([^"]+)"'
    match = re.search(pattern, content)
    
    if match:
        title = match.group(1)
        prompt = match.group(2)
        
        # Find the expected actions section
        actions_pattern = rf'(### Scenario {i}:.*?)\n\*\*Expected Claude Actions:\*\*\n(.*?)(?=\n---|\n### Scenario|\Z)'
        actions_match = re.search(actions_pattern, content, re.DOTALL)
        
        if actions_match:
            # Extract actions and format with checkboxes
            actions_text = actions_match.group(2).strip()
            # Add checkboxes to numbered items
            actions_with_boxes = re.sub(r'^(\d+\.)', r'- [ ] \1', actions_text, flags=re.MULTILINE)
            
            # Build the replacement
            replacement = f"""### Scenario {i}: {title}
{checkbox_template.format(prompt=prompt, actions=actions_with_boxes)}"""
            
            # Replace in content
            old_section = rf'### Scenario {i}:.*?(?=\n---|\n### Scenario|\Z)'
            content = re.sub(old_section, replacement, content, flags=re.DOTALL)

# Write back
file_path.write_text(content)
print("✅ Added checkboxes to all scenarios!")