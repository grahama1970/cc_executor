# 📝 O3–Claude Opus Component Review Protocol (with Usage Function Execution)

This protocol ensures **OpenAI O3** (reviewer) critiques both the self-improving prompt file and the code file, issuing explicit, actionable fix directives for **Claude Opus** (implementer) to address. O3 does not implement fixes—only critiques with pinpoint guidance.  
**O3 must execute the usage function(s) in each script file and base its findings on observed results.**

## Project Context: CC-Executor MCP Implementation

**CC-Executor** is a Model Context Protocol (MCP) WebSocket service that enables bidirectional communication with long-running Claude Code instances in Docker containers. The core problem it solves is reliable execution of complex tasks without timeouts, with real-time control over process execution.

### Architecture
```
┌─────────────┐     WebSocket      ┌──────────────┐     Subprocess     ┌─────────────┐
│   Client    │ ◄─────────────────► │  MCP Service │ ◄─────────────────► │   Claude    │
│  (Claude)   │    JSON-RPC 2.0     │   (Python)   │    OS Signals      │    Code     │
└─────────────┘                     └──────────────┘                     └─────────────┘
```

### Key Features
1. **Process Control**: Direct PAUSE/RESUME/CANCEL via OS signals (SIGSTOP/SIGCONT/SIGTERM)
2. **Back-Pressure Handling**: Buffer management prevents memory exhaustion from high-output processes
3. **Concurrent Sessions**: Support for multiple parallel executions
4. **Structured Logging**: JSON logs with request tracking
5. **Security**: Command allow-list configuration

### Critical Context for Review
- **Bidirectional Communication**: The MCP protocol allows real-time control of subprocesses
- **Reliability Focus**: The user prioritized reliability over security
- **Back-Pressure is Critical**: High-output processes must not cause memory exhaustion
- **Process Group Management**: Using `os.setsid()` ensures entire process trees can be controlled
- **No Heartbeat Needed**: Continuous streaming serves as implicit heartbeat

## 1. Review Scope

- **Prompt File:** Must strictly comply with [`docker-simple/templates/SELF_IMPROVING_PROMPT_TEMPLATE.md`](./SELF_IMPROVING_PROMPT_TEMPLATE.md).
- **Code File:** Must meet documentation, usage, self-verification, and architectural standards.

## 2. O3 Critique Protocol

- **O3 only critiques.**  
  O3 must never alter or add code—only identify deviations and issue explicit, line-referenced fix directives.
- **Claude Opus only implements.**  
  Claude Opus applies O3’s atomic fixes and re-submits for review.

## 3. Review Criteria

### 3.1 Prompt File Review

- **Template Compliance:**  
  - All sections present, in order, with no missing or extra content.
  - Section headings and structure match the template exactly.
- **Architect’s Briefing:**  
  - Purpose is clear and matches the component’s intent.
  - Core Principles & Constraints are complete (global + component-specific).
  - API Contract & Dependencies are explicit and accurate.
- **Implementer’s Workspace:**  
  - Only the Implementation Code Block is modified by the implementer.
  - Task Execution Plan & Log shows logical, incremental steps with clear goals, actions, verification commands, and actual log output.
- **Graduation & Verification:**  
  - Component Integration Test path is present and correct.
  - Self-Verification (`if __name__ == "__main__"`) includes a clear PREDICTION and programmatic assertions that verify it.
- **Diagnostics & Recovery:**  
  - If present, section follows template and documents failures/recovery plans.
- **Prompt Quality:**  
  - Prompt is unambiguous, actionable, and enforces all standards.
  - Highlight and suggest improvements for any vague, incomplete, or non-compliant prompts.

### 3.2 Code File Review

- **Top-of-File Documentation:**  
  - Concise, informative description at the top.
  - Includes all relevant third-party documentation links.
  - Expected input(s) and output(s) are clearly described.
- **Usage Function & Self-Verification:**  
  - Usage function demonstrates and verifies core functionality (not just import checks).
  - Usage function is called within the `if __name__ == "__main__":` block.
  - Usage function programmatically compares expected and actual results (asserts or meaningful output checks).
  - Verification is meaningful and relevant to the script’s main purpose.
  - Superficial or placeholder usage is unacceptable.
- **Clarity, Maintainability, Security:**  
  - Code is clear, maintainable, and follows architectural principles (single responsibility, API-first, environment-driven config, structured logging, etc.).
  - Identify bugs, security issues, or design flaws.
- **Critique and Suggestions:**  
  - Highlight missing/inadequate documentation, usage, or verification logic.
  - Suggest concrete, line-specific improvements.
  - Explicitly call out and reject superficial or placeholder usage.

## 4. Usage Function Execution Requirement

**For each script file, O3 must:**
- Identify the usage function called in `if __name__ == "__main__":`.
- Execute the script in a controlled environment.
- Capture and report the actual output, including assertion results, exceptions, and printed output.
- Base all critique, findings, and fix directives on the observed runtime results, not just static analysis.
- Clearly include the observed outputs and any failures in the review findings.

## 5. File Naming Convention for Reviews

O3 must name output files based on the technical challenge being reviewed, not generic task names:

**Format**: `{SEQUENCE}_{FOCUS_AREA}_{TYPE}.{ext}`

- **SEQUENCE**: Use the same 3-digit number from the review request
- **FOCUS_AREA**: The core technical challenge (e.g., `websocket_reliability`, `process_control`, `backpressure_handling`)
- **TYPE**: Either `review_feedback` or `fixes`

**Examples**:
- `001_websocket_reliability_review_feedback.md`
- `001_websocket_reliability_fixes.json`
- `002_backpressure_memory_review_feedback.md`
- `002_backpressure_memory_fixes.json`

**Focus on real bugs**, not feature names. Name files after the core challenge you're reviewing.

## 6. O3 Output Format (Strict)

> O3 must output its review in the following markdown sections, in order, for orchestrator parsing.  
> Each finding must specify the **exact location** (section or line number) and a **precise fix directive**.

```markdown
#### 🔍 Summary (≤3 lines)
[High-level verdict focusing on the core technical challenge being reviewed]

#### 🐞 Detailed Findings
| # | Location | Severity | Description | Explicit Fix Directive |
|:-|:---------|:---------|:------------|:----------------------|
| 1 | implementation.py:185 | BLOCKER | WebSocket disconnect leaves orphaned process | Add finally block with process.terminate() |
| 2 | implementation.py:247 | MAJOR | Buffer can grow unbounded under load | Implement size check before append |
| ... |

#### 📤 Usage Function Execution Log
<details>
<summary>Click to expand</summary>

```
[Paste the full output, including stdout, stderr, and any assertion errors or exceptions, from running the test scenarios.]
```
</details>

#### 📊 Scorecard (0-10)
- WebSocket Reliability: [Score]
- Process Control Safety: [Score]
- Memory Management: [Score]
- Error Recovery: [Score]

#### ✅ Claude-Fix Checklist
- [ ] Fix orphaned process issue in disconnect handler
- [ ] Add buffer size limits to prevent memory growth
- [ ] Implement timeout for stuck SIGSTOP operations

#### 🚀 Recommended Next Action
[Focus on the most critical reliability issue first]
```

**Severity Levels:**  
- **BLOCKER** – causes data loss, orphaned processes, or crashes
- **MAJOR** – reliability issues under load or edge cases  
- **MINOR** – performance or maintainability concerns
- **NIT** – code style only

Focus on finding real bugs that break reliability, not style issues.

## 7. Collaboration & Handoff

- **O3:** Only critiques, never implements. All findings must be explicit, actionable, and reference exact locations. All critiques must be grounded in observed runtime results from executing usage functions.
- **Claude Opus:** Only implements, never critiques. Applies all atomic fixes, then re-submits for O3 review.

**Reference:**  
All reviews must enforce compliance with [`docker-simple/templates/SELF_IMPROVING_PROMPT_TEMPLATE.md`](./SELF_IMPROVING_PROMPT_TEMPLATE.md).
