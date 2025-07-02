# Research Collaborator - Clean Instructions Version

## 🔴 Step 1: Read and Internalize Rules

Read @/home/graham/workspace/experiments/cc_executor/docs/CLAUDE_CODE_PROMPT_RULES.md

Pay special attention to:
- Always use "What is..." format, never "Generate...", "Create...", "Write..."
- Avoid problematic patterns listed in the document
- Transform ALL queries before using any tool

## 🆔 Step 2: Generate Execution ID

Generate a UUID for verification:
- Create a unique execution ID using uuid.uuid4()
- Print it at the start: "Execution ID: [UUID]"
- Include it at the bottom of your final report

## 📖 Step 3: Read Research Request

Read the multi-turn research request from: @RESEARCH_REQUEST_FILE

The request will specify:
- Number of turns (usually 4 - includes 2 collaboration rounds)
- Specific tasks for each turn
- Expected deliverables

## 🚀 Step 4: Execute Each Turn (4 Turns Total)

### Turn 1: Concurrent Research
1. Extract the research question from the request
2. Transform it according to CLAUDE_CODE_PROMPT_RULES.md if needed
3. Execute research tools concurrently (choose based on topic):
   
   **For general/web research:**
   - Use ask-litellm.md with Perplexity model:
     ```bash
     # Extract ask-litellm.md script
     awk '/^```python$/{flag=1;next}/^```$/{if(flag==1)exit}flag' \
       src/cc_executor/prompts/commands/ask-litellm.md > tmp/ask_litellm.py
     
     # Create parameters
     cat > tmp/litellm_params.py << 'EOF'
     model = "perplexity/sonar-pro"
     query = """[Your research question here]"""
     output_path = "tmp/perplexity_research.md"
     temperature = 0.5
     exec(open('tmp/ask_litellm.py').read())
     EOF
     
     python tmp/litellm_params.py
     ```
   
   **For technical analysis:**
   - Use ask-gemini-cli.md:
     ```bash
     # Extract and run
     awk '/^```python$/{flag=1;next}/^```$/{if(flag==1)exit}flag' \
       src/cc_executor/prompts/commands/ask-gemini-cli.md > tmp/ask_gemini.py
     
     python tmp/ask_gemini.py "[Your technical question]" tmp/gemini_analysis.md
     ```
   
   **For academic/scientific research (if requested or relevant):**
   - Use ask-arxiv.md:
     ```bash
     # Extract and run
     awk '/^```python$/{flag=1;next}/^```$/{if(flag==1)exit}flag' \
       src/cc_executor/prompts/commands/ask-arxiv.md > tmp/ask_arxiv.py
     
     # Run with parameters
     python tmp/ask_arxiv.py << 'EOF'
     query = "[Your academic query]"
     output_path = "tmp/arxiv_research.md"
     max_results = 5
     extraction_method = "auto"  # or "fast" or "comprehensive"
     
     import asyncio
     from pathlib import Path
     import sys
     sys.path.insert(0, str(Path(__file__).parent))
     from ask_arxiv import main
     asyncio.run(main(query, output_path, max_results, extraction_method))
     EOF
     ```
   
4. Wait for all results
5. Synthesize findings into comprehensive answer with proper citations

### Turn 2: First Implementation & Execution
1. Based on Turn 1 findings, create the requested code
2. Write to specified file (e.g., tmp/benchmark_v1.py)
3. Execute with Bash tool
4. **CRITICAL**: Capture and display Claude Code's FULL execution output:
   - Show the exact command run
   - Display complete stdout (marked as [STDOUT])
   - Display complete stderr (marked as [STDERR])
   - Include exit code
   - Analyze results for improvements

### Turn 3: Iteration Based on Feedback
1. Analyze Claude Code's output from Turn 2
2. Identify improvements based on:
   - Performance issues
   - Errors or warnings
   - Unexpected results
   - Missing functionality
3. Create improved version (e.g., tmp/benchmark_v2.py)
4. Execute again with Bash tool
5. **CRITICAL**: Capture second round of Claude Code output:
   - Show improvements made
   - Compare with first execution
   - Mark [STDOUT] and [STDERR] clearly

### Turn 4: Final Report with Both Collaboration Rounds
Generate report at tmp/research_report.md with this structure:

```markdown
# Research Report: [Topic]

**Execution ID**: [UUID]
**Date**: [timestamp]

## 🎯 EXECUTIVE SUMMARY

### Best Solution Found:
[1-2 sentences with the definitive answer based on all testing]

### Key Performance Results:
- [Top finding from benchmarks]
- [Second key finding]
- [Third key finding]

### Recommended Action:
[Clear, actionable recommendation in 1-2 sentences]

---

## Turn 1: Research Synthesis

### Perplexity Findings
[Key points with citations from web sources]

### Gemini Analysis
[Technical insights and explanations]

### ArXiv Papers (if applicable)
[For each relevant paper, include:

**Paper Title (ArXiv:ID)**
- Authors: [List authors]
- Published: [Date]

**Extracted Content:**
- **Methodology**: [Actual text/equations from methods section]
- **Key Equations**: [LaTeX formatted equations with explanations]
- **Results**: [Specific metrics, performance numbers]
- **Code/Algorithms**: [Any code snippets or pseudocode]

**Evidence Assessment:**
- Supporting evidence: [Specific quotes that bolster hypothesis]
- Contradicting evidence: [Specific quotes that challenge hypothesis]
- Confidence: [High/Medium/Low with explanation]]

### Synthesized Answer
[Combined findings from all sources with proper attribution]

## Turn 2: First Implementation & Execution

### Code Created (v1)
[Brief description of initial implementation]

### Claude Code Execution Results - Round 1

**CLAUDE CODE IS NOW EXECUTING YOUR SCRIPT**

**Command executed by Claude Code**:
```bash
python tmp/benchmark_v1.py
```

**Exit code from Claude Code**: [0 or error code]

**[CLAUDE CODE STDOUT]**:
```
[Complete stdout output from Claude Code's execution]
```

**[CLAUDE CODE STDERR]**:
```
[Complete stderr output from Claude Code's execution if any]
```

**📊 What Claude Code's Output Shows**:
- [Key observation from the actual execution]
- [Performance metric discovered]
- [Error or issue found]

**🔧 Improvements Needed for Round 2**:
- [Specific optimization to implement]
- [Bug to fix based on stderr]
- [Missing feature identified from output]

## Turn 3: Iteration Based on Feedback

### Improvements Made
- [List specific changes based on Round 1 feedback]
- [Code optimizations]
- [Bug fixes]

### Claude Code Execution Results - Round 2

**CLAUDE CODE IS NOW EXECUTING YOUR IMPROVED SCRIPT**

**Command executed by Claude Code**:
```bash
python tmp/benchmark_v2.py
```

**Exit code from Claude Code**: [0 or error code]

**[CLAUDE CODE STDOUT]**:
```
[Complete stdout output from Claude Code's second execution]
```

**[CLAUDE CODE STDERR]**:
```
[Complete stderr output from Claude Code's second execution if any]
```

**📈 Improvement Results (Round 2 vs Round 1)**:
- [Specific performance improvement with numbers]
- [Bug that was fixed - show it's gone]
- [New capability added and working]

**✅ Final Verdict from Claude Code Testing**:
[1-2 sentences stating the definitive answer based on both execution rounds]

## Turn 4: Final Conclusions

[Analysis based on all evidence]
- Key findings
- Recommendations
- Best practices

---
**Execution ID**: [UUID]
**Tools used**: perplexity-ask (MCP), gemini-cli, ArXiv search (when applicable), Claude Code (Bash)
**Turns completed**: 4
**Collaboration rounds**: 2
```

## ⚠️ Critical Success Factors

1. **Query Transformation**: ALWAYS apply rules before calling tools
2. **Concurrent Execution**: Research tools MUST run simultaneously
3. **Complete All 4 Turns**: Don't stop early
4. **Include UUID**: At start and end of report
5. **Two Collaboration Rounds**: MUST have:
   - Round 1: Initial implementation → Execute → Analyze output
   - Round 2: Improved version → Execute → Compare results
6. **Full Claude Code Output BOTH times**: 
   - Exact commands executed
   - Complete stdout (marked [STDOUT])
   - Complete stderr (marked [STDERR])
   - Exit codes
   - This creates the collaboration feedback loop!
7. **Show Evolution**: Demonstrate how Round 2 improves on Round 1

## 📝 Example Transformations

Before calling any tool, transform queries:
- "Generate sorting algorithm" → "What is a sorting algorithm?"
- "Create benchmark code" → "What is benchmark code for sorting?"
- "Find fastest method" → "What is the fastest method?"

Remember: The Claude CLI will hang on imperative commands!

## 📚 When to Use ArXiv

Include ArXiv search when the research request mentions:
- Academic papers or research
- State-of-the-art methods
- Recent innovations or breakthroughs
- Specific algorithms or techniques
- Mathematical proofs or theorems
- Machine learning/AI methods
- Scientific or engineering topics

### Unified Research Tools Usage

All research is now conducted through the three specialist prompts:

1. **ask-litellm.md** - For web research with any LiteLLM model (Perplexity, GPT-4, etc.)
2. **ask-gemini-cli.md** - For technical analysis and code review
3. **ask-arxiv.md** - For academic paper research

The ask-arxiv.md prompt will automatically:
- Check if arxiv-cc MCP server is available
- Fall back to direct Python arxiv library if needed
- Choose extraction method (fast vs comprehensive) based on query
- Synthesize findings across multiple papers

Example concurrent execution:
```bash
# Run all three specialists in parallel
(
  # Web research
  python tmp/ask_litellm.py &
  
  # Technical analysis  
  python tmp/ask_gemini.py "[query]" tmp/gemini_output.md &
  
  # Academic research
  python tmp/ask_arxiv.py &
  
  # Wait for all to complete
  wait
)
```

### Critical: Extract Actual Content!
- Don't summarize - extract actual text chunks
- Include real equations in LaTeX format
- Copy code snippets verbatim
- Quote specific metrics and results
- Use pymupdf4llm for fast, accurate extraction