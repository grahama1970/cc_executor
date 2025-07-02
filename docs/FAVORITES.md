### PRompt Rules
/home/graham/workspace/experiments/cc_executor/src/cc_executor/templates/SELF_IMPROVING_PROMPT_TEMPLATE.md
/home/graham/workspace/experiments/cc_executor/docs/CLAUDE_CODE_PROMPT_RULES.md
/home/graham/workspace/experiments/cc_executor/docs/ACK_LAST_LINE_OF_DEFENSE.md



### Stress Tests
- /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/stress_tests/stress_test_docker.md
- /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/stress_tests/stress_test_fastapi.md
- /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/stress_tests/stress_test_local.md

PROMPT:
REQUEST='With a maximum of 3 conversation turns, perform the following task:\n\n**Turn 1: Concurrent Research**\nConcurrently execute the following two tasks:\n1. Use the  tool to research the question: '\''What is the fastest, most optimized method in Python for multiplying two matrices?'\''.\n2. Use the  tool to execute the prompt at  with the same question.\n\nAfter both tools return their results, synthesize their findings into a single, comprehensive answer.\n\n**Turn 2: Code and Benchmark**\nBased on the synthesized findings from Turn 1, write a Python script to /tmp/benchmark_matmul.py that benchmarks the top recommended methods against a naive pure Python implementation. After writing the file, use the  tool to execute it with  and capture the output.\n\n**Turn 3: Final Report**\nProvide a final report for the researchers. The report must include:\n1. The synthesized research from Turn 1.\n2. The full output from the benchmark execution in Turn 2.\n3. A final conclusion based on all the gathered evidence.'


phi3:latest                    4f2222927938    2.2 GB    26 seconds ago
codellama:13b-instruct-q8_0    196822804b09    13 GB     3 minutes ago
mannix/jan-nano:latest         b48a8b54cc40    2.3 GB    24 minutes ago
qwen2.5:32b                    9f13ba1299af    19 GB     26 minutes ago