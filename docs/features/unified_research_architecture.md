# Unified Research Architecture for CC Executor

## Overview

The research-collaborator.md prompt now uses a unified architecture where each research source is handled by a specialized self-improving prompt:

1. **ask-litellm.md** - Universal LLM interface for web research (Perplexity, GPT-4, etc.)
2. **ask-gemini-cli.md** - Technical analysis and code review specialist
3. **ask-arxiv.md** - Academic paper research specialist

## Key Benefits

### 1. Consistency
All three collaborators follow the same execution pattern:
```bash
# Extract the prompt's code
awk '/^```python$/{flag=1;next}/^```$/{if(flag==1)exit}flag' \
  src/cc_executor/prompts/commands/ask-[tool].md > tmp/ask_[tool].py

# Execute with parameters
python tmp/ask_[tool].py [parameters]
```

### 2. Intelligence
Each specialist has built-in intelligence:
- **ask-arxiv.md** automatically chooses extraction methods (fast vs comprehensive)
- **ask-litellm.md** handles fallback models and provider-specific configurations
- **ask-gemini-cli.md** optimizes for code review and technical analysis

### 3. Self-Improvement
Each prompt tracks its own metrics and evolves independently:
- Success/failure ratios
- Evolution history
- Learned patterns

### 4. Modularity
Easy to add new specialists:
- ask-pubmed.md for medical research
- ask-wikipedia.md for general knowledge
- ask-github.md for code examples

## Usage in research-collaborator.md

### Turn 1: Concurrent Research

```bash
# Run all three specialists in parallel
(
  # Web research with Perplexity
  python tmp/ask_litellm.py &
  
  # Technical analysis with Gemini
  python tmp/ask_gemini.py "[query]" tmp/gemini_output.md &
  
  # Academic research with ArXiv
  python tmp/ask_arxiv.py &
  
  # Wait for all to complete
  wait
)
```

### Integration with MCP Tools

- **ask-arxiv.md** checks for arxiv-cc MCP server availability
- Falls back to direct Python libraries when MCP is not available
- Maintains compatibility with both approaches

## Architecture Diagram

```
research-collaborator.md
        |
        ├── ask-litellm.md (Web Research)
        │   ├── Perplexity API
        │   ├── OpenAI API
        │   └── Other LiteLLM providers
        │
        ├── ask-gemini-cli.md (Technical Analysis)
        │   └── Gemini CLI binary
        │
        └── ask-arxiv.md (Academic Research)
            ├── arxiv-cc MCP server (if available)
            └── Python arxiv library (fallback)
```

## Future Enhancements

1. **Automatic Specialist Selection**
   - Analyze query to determine which specialists to use
   - Skip irrelevant specialists for efficiency

2. **Cross-Specialist Communication**
   - Allow specialists to share findings
   - Build knowledge graphs across sources

3. **Extraction Method Intelligence**
   - ask-arxiv.md already has smart extraction selection
   - Could extend to other specialists

4. **Unified Reporting**
   - Merge outputs from all specialists
   - Identify contradictions and agreements
   - Synthesize comprehensive conclusions

## Implementation Status

✅ **Completed**:
- ask-arxiv.md created and tested
- ask-litellm.md graduated (10:0)
- ask-gemini-cli.md graduated (12:0)
- research-collaborator.md updated to use unified architecture
- All prompts follow self-improving patterns

🔄 **Optional Future Work**:
- Update ask-litellm.md and ask-gemini-cli.md to follow exact SELF_IMPROVING_PROMPT_TEMPLATE.md structure
- Add more specialist prompts as needed
- Implement cross-specialist communication