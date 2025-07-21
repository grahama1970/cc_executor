### **Slash Command**
`/review-contextual`

### **Description**
Context-aware two-phase code review that ensures recommendations are practical and compatible with your project's specific requirements:
1. **Phase 1: Contextual Analysis (O3-pro)** - Complete review with project constraints applied
2. **Phase 2: Validation & Synthesis (Gemini 2.5 Pro)** - Independent validation with context awareness

**IMPORTANT**: This workflow provides **analysis and recommendations only**. No code changes are written to files.

### **Arguments**
| Argument | Required | Description |
|----------|----------|-------------|
| `files` | Yes | Space-separated list of file paths. If first file is `.md` with "context" in name, it's used as context |
| `--context` | No | Inline context string (max 500 chars) |
| `--context-file` | No | Path to context file |
| `--focus` | No | Specific areas: `security`, `performance`, `maintainability`, `architecture` |
| `--severity` | No | Minimum level: `low`, `medium`, `high`, `critical` (default: `medium`) |

### **Smart Context Detection**
1. **First .md file** with "context", "constraints", or "readme" in name = context file
2. **Explicit context** via `--context` or `--context-file` overrides auto-detection
3. **Fallback** to `.kilocode/CONTEXT.md` if exists
4. **Auto-detection** based on imports, patterns, and `.mcp.json`

### **Usage Examples**

#### **Simple - Context File First**
```bash
/review-contextual .kilocode/CONTEXT.md src/servers/mcp_*.py
```

#### **Inline Context - Quick Reviews**
```bash
/review-contextual src/servers/mcp_*.py --context "MCP servers with subprocess tools. FastMCP needs JSON strings."
```

#### **Explicit Context File**
```bash
/review-contextual src/**/*.py --context-file .kilocode/contexts/cc_executor_mcp.txt
```

#### **Auto-Detection (Simplest)**
```bash
# If .kilocode/CONTEXT.md exists
/review-contextual src/servers/mcp_*.py
```

### **Context File Format**
```markdown
# Project Context

## Type
MCP Server for Claude Code

## Critical Constraints
1. Tools are subprocess scripts using sys.argv - NOT importable modules
2. FastMCP doesn't support Dict/List parameters - use JSON strings
3. Backward compatibility is mandatory
4. No duplicate files with similar names (e.g., tool_optimized.py)

## Design Decisions
- Subprocess execution is REQUIRED, not inefficient
- Embedded HTML templates are intentional (single-file deployment)
- Default passwords with warnings are acceptable for dev experience

## What NOT to "Fix"
- Don't convert subprocess tools to imports
- Don't split embedded templates into separate files
- Don't remove defaults that would break existing deployments
```

### **Workflow & Output**

1. **Context Processing**
   - Loads and validates context
   - Merges with auto-detected patterns
   - Creates context digest for both phases

2. **Phase 1: Contextual O3 Review**
   - Applies context constraints upfront
   - Flags incompatible suggestions
   - Generates `phase1_contextual_report.json`

3. **Phase 2: Contextual Validation**
   - Gemini independently reviews with same context
   - Validates context was properly applied
   - Creates final consolidated review

4. **Final Output Structure**
```
📁 docs/code_review/{timestamp}_{context_hash}/
├── 📄 context_applied.md           # Exact context used
├── 📄 phase1_contextual_report.json
├── 📄 phase2_validation.json
├── 📄 actionable_fixes.md          # Only context-compatible fixes
├── 📄 incompatible_suggestions.md  # What was rejected and why
└── 📄 review_summary.md           # Executive summary
```

### **Key Deliverables**

#### **actionable_fixes.md**
```markdown
# Actionable Fixes (Context-Compatible)

## Critical Issues (0)
*No critical issues that are compatible with context*

## High Priority (1)
### 1. Add Environment Variable Warning
**File:** src/servers/mcp_arango_tools.py:45
**Current:**
```python
password = os.getenv("ARANGO_PASSWORD", "openSesame")
```
**Fixed:**
```python
password = os.getenv("ARANGO_PASSWORD", "")
if not password:
    logger.warning("⚠️ ARANGO_PASSWORD not set - using insecure default")
    password = "openSesame"
```
**Rationale:** Maintains backward compatibility while alerting users
**Context:** ✅ Compatible - adds warning without breaking changes
```

#### **incompatible_suggestions.md**
```markdown
# Incompatible Suggestions (Rejected)

## Would Break MCP Compatibility
### 1. ❌ Convert subprocess tools to direct imports
**Why Rejected:** Tools in src/cc_executor/tools/*.py are CLI scripts that parse sys.argv. Direct import would break MCP protocol.

### 2. ❌ Use Dict parameters in FastMCP
**Why Rejected:** FastMCP has validation bugs with Dict/List types. Must use JSON strings.

### 3. ❌ Remove default password entirely
**Why Rejected:** Would break existing deployments. Context requires backward compatibility.
```

### **MCP Auto-Detection Rules**
When these patterns are found, MCP constraints are automatically applied:
- `from fastmcp import FastMCP`
- `.mcp.json` in directory
- Files matching `mcp_*.py`
- `#!/usr/bin/env -S uv run --script`

### **Context Validation**
The system validates context for:
- **Relevance**: Warns if context seems unrelated to files
- **Completeness**: Suggests missing constraints based on code patterns
- **Conflicts**: Identifies contradictory requirements

### **Best Practices**

1. **Project-Wide Context**
   ```bash
   # Create once
   cat > .kilocode/CONTEXT.md << 'EOF'
   # CC Executor Context
   MCP services with subprocess tools. FastMCP limitations. No breaking changes.
   EOF
   
   # Use everywhere
   /review-contextual src/**/*.py
   ```

2. **Component-Specific Context**
   ```bash
   /review-contextual src/api/API_CONTEXT.md src/api/**/*.py
   ```

3. **CI Integration**
   ```yaml
   - name: Contextual Code Review
     run: /review-contextual src/**/*.py --context-file .kilocode/CONTEXT.md
   ```

### **Pro Tips**

1. **Quick Context for One-Off Reviews**
   ```bash
   /review-contextual file.py --context "Legacy code. Minimal changes only."
   ```

2. **Combine Multiple Contexts**
   ```bash
   /review-contextual CONTEXT.md MCP_CONSTRAINTS.md src/**/*.py
   # Both .md files are merged as context
   ```

3. **Override Auto-Detection**
   ```bash
   /review-contextual src/api/*.py --context "Not an MCP server despite imports"
   ```

### **Error Handling**
- **Missing context**: Proceeds with auto-detection + warning
- **Invalid context file**: Shows error and halts
- **Conflicting contexts**: Shows conflicts and asks for clarification

---
**Runtime:** Up to 5 minutes per phase
**Quality Gates:** 
- Phase 1: Rejects suggestions violating explicit context
- Phase 2: Validates context was properly applied
- Both phases: Flag but include "general best practice" items for awareness