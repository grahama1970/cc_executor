# CC Executor Favorites

Quick reference links to frequently used documentation and resources.

## Prompt Rules and Guidelines
- [Self-Improving Prompt Template](/home/graham/workspace/experiments/cc_executor/docs/templates/SELF_IMPROVING_PROMPT_TEMPLATE.md)
- [Prompt Best Practices](/home/graham/workspace/experiments/cc_executor/docs/PROMPT_BEST_PRACTICES.md)
- [Timeout Management (ACK Pattern)](/home/graham/workspace/experiments/cc_executor/docs/technical/timeout_management.md)

## Stress Tests
- [Docker Stress Test](/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/stress_tests/stress_test_docker.md)
- [FastAPI Stress Test](/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/stress_tests/stress_test_fastapi.md)
- [Local Stress Test](/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/stress_tests/stress_test_local.md)

## Key Documentation
- [Operating the Service](/home/graham/workspace/experiments/cc_executor/docs/guides/OPERATING_THE_SERVICE.md)
- [Troubleshooting Guide](/home/graham/workspace/experiments/cc_executor/docs/guides/troubleshooting.md)
- [Hook System Overview](/home/graham/workspace/experiments/cc_executor/docs/hooks/README.md)
- [WebSocket MCP Protocol](/home/graham/workspace/experiments/cc_executor/docs/architecture/websocket_mcp_protocol.md)

## Example Commands

### Research Collaborator Example
```bash
REQUEST='With a maximum of 3 conversation turns, perform the following task:\n\n**Turn 1: Concurrent Research**\nConcurrently execute the following two tasks:\n1. Use the tool to research the question: '\''What is the fastest, most optimized method in Python for multiplying two matrices?'\''.\n2. Use the tool to execute the prompt at with the same question.\n\nAfter both tools return their results, synthesize their findings into a single, comprehensive answer.\n\n**Turn 2: Code and Benchmark**\nBased on the synthesized findings from Turn 1, write a Python script to /tmp/benchmark_matmul.py that benchmarks the top recommended methods against a naive pure Python implementation. After writing the file, use the tool to execute it with and capture the output.\n\n**Turn 3: Final Report**\nProvide a final report for the researchers. The report must include:\n1. The synthesized research from Turn 1.\n2. The full output from the benchmark execution in Turn 2.\n3. A final conclusion based on all the gathered evidence.'
```

### Quick WebSocket Test
```bash
python core/websocket_handler.py --serve --auto-demo --test-case simple
```

### Debug Mode
```bash
LOG_LEVEL=DEBUG python core/websocket_handler.py --serve
```

## Useful Paths
- Main entry point: `/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/websocket_handler.py`
- Client examples: `/home/graham/workspace/experiments/cc_executor/examples/`
- Test outputs: `/home/graham/workspace/experiments/cc_executor/test_outputs/`
- Logs: `/home/graham/workspace/experiments/cc_executor/logs/`

Last updated: 2025-07-02