# 🗒️ 000_tasks_list

> Each task below must be executed using the **SELF_IMPROVING_PROMPT_FLOW_TEMPLATE.md** (Architect → Implementer workflow).  
> Status boxes track real progress; do **not** tick a box until the Step-by-Step plan in the template has fully passed its verification for that task.

## 📋 Prerequisites & Setup

### Docker Image Build
The `cc-executor/claude-code-docker:latest` image must be built before running tests:
```bash
# Navigate to docker directory (find Dockerfile location first)
docker build -t cc-executor/claude-code-docker:latest .
```

### Template References
- **Workflow Template**: `/home/graham/workspace/experiments/cc_executor/src/cc_executor/templates/SELF_IMPROVING_PROMPT_TEMPLATE.md`
- **Project Blueprint**: `/home/graham/workspace/experiments/cc_executor/src/cc_executor/templates/PROJECT_BLUEPRINT_TEMPLATE.md`

### Working Directory
All task implementation files should be created in: `/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/`

## 📌 High-Level Roadmap

- [x] **T00 – Read & Understand**  
  *Complete the template's Step 0 Pre-Flight Check for the entire `cc_executor_mcp` context (README, implementation, tests).*  
  _Implementation Path:_ Create `T00_read_understand.md` using SELF_IMPROVING_PROMPT_TEMPLATE.md  
  _Owner:_ Implementer

- [x] **T01 – Robust Logging & Observability**  
  Goal: Replace `print` with structured `logging` using `python-json-logger` or `structlog`, add `/healthz` endpoint.  
  _Implementation Details:_
  - Use centralized logging configuration at application entry point
  - Direct logs to stdout/stderr for Docker compatibility
  - Include request IDs and timestamps in structured format
  - Avoid per-component logging implementations
  Verification: `pytest tests/test_healthz.py` should pass & logs must appear in JSON format.

- [x] **T02 – Back-Pressure Handling**  
  Goal: Prevent buffer bloat when streaming huge stdout/stderr; implement line throttling or `limit` handling.  
  _Implementation Details:_
  - Add configurable buffer size limits via environment variables
  - Implement async line-by-line processing with asyncio
  - Drop lines if buffer exceeds threshold with appropriate logging
  - Monitor memory usage during stress tests
  Verification: Stress test piping `yes | pv -qL 50000` for 60 s without memory blow-up (RSS < 100MB).

- [x] **T03 – WebSocket Long-Running Stress Tests**  
  Goal: Create/expand `stress_test.py` to open ≥3 concurrent sessions, PAUSE/RESUME/CANCEL a 90 s job.  
  _Implementation Details:_
  - Use `websockets` library or `locust` for concurrent connections
  - Test state transitions (PAUSE→RESUME→CANCEL sequences)
  - Verify process cleanup and resource release
  - Test resilience with network disconnects/reconnects
  - Measure latency and resource usage under load
  Verification: ≥95 % pass rate, zero orphan processes (`pgrep -f "yes | pv"` returns none).

- [ ] **T04 – CI Integration**  
  Goal: Ensure the new stress test runs in `tests/` via GitHub Actions; fail fast on regressions.  
  _Implementation Details:_
  - Add `.github/workflows/test.yml` if not exists
  - Include Docker build step in CI
  - Run stress tests with timeout limits
  - Generate test reports for visibility
  Verification: CI badge stays green after merge.

- [x] **T05 – Security Pass**  
  Goal: Document risks of arbitrary shell execution; add optional command allow-list in config.  
  _Implementation Details:_
  - Add `ALLOWED_COMMANDS` environment variable (comma-separated list)
  - Implement command validation before execution
  - Return proper JSON-RPC error with code -32602 for denied commands
  - Log all command execution attempts for audit trail
  Verification: Attempting disallowed command returns JSON-RPC error `SECURITY_DENIED`.

- [ ] **T06 – Documentation Update**  
  Goal: Extend component README with logging, stress-test usage, and security notes.  
  _Implementation Details:_
  - Document all environment variables
  - Add examples of structured log output
  - Include security best practices section
  - Provide Docker deployment examples
  Verification: `markdownlint` passes; reviewer approval.

- [ ] **T07 – Graduation Metrics Update**  
  Goal: Update Gamification metrics in the component prompt once ≥10:1 success ratio achieved.  
  _Implementation Details:_
  - Track success/failure in Evolution History table
  - Update metrics after each execution
  - Graduate to `core/` directory once 10:1 achieved
  - Archive prompt file with final metrics
  Verification: Metrics table in `cc_executor_mcp.md` reflects new counts.

---

### Progress Legend
- ☐ = Not started  
- ◔ = In progress (template Step 1-n underway)  
- ✅ = Verified & merged

> **Reminder:** Before moving a box from ☐ to ◔ or ✅, follow the template:
> 1. Architect defines/updates the step in the *ARCHITECT'S BRIEFING*.
> 2. Implementer asks clarifying questions (≤3) if needed.
> 3. Implementer edits code **only** in the Implementation Code Block.
> 4. Verification command passes & logs pasted.
> 5. Evolution History table updated.

### Implementation Notes

#### MCP Bridge Pattern (from Perplexity research)
- **Command passthrough**: Bridge should primarily handle protocol translation (WebSocket ↔ HTTP)
- **Basic retries**: Implement circuit breakers for transient HTTP failures only
- **Stateless operation**: Keep bridge lightweight and stateless for scaling
- **Delegate recovery**: Let downstream HTTP services handle complex recovery logic
- **Log everything**: Ensure comprehensive logging of errors, timeouts, and disconnections

#### Docker Build Requirements
1. Find the Dockerfile location (likely in a `docker/` subdirectory)
2. Ensure all dependencies are included in the image
3. Tag correctly as `cc-executor/claude-code-docker:latest`
4. Consider pushing to a registry for CI/CD workflows

#### Testing Best Practices
- Use dedicated WebSocket testing tools (JMeter, Locust, Artillery)
- Validate state transitions for control commands
- Monitor resource usage and process lifecycle
- Test network resilience and recovery scenarios