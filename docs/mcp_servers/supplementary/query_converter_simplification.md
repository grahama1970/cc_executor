# Query Converter Simplification

## The Problem with the Original

The original `query_converter.py` was overly complex with:
- 1000+ lines of code
- Complex regex patterns for intent detection
- Entity extraction logic
- QueryIntent enum with 8+ types
- Multiple parsing functions
- Hardcoded AQL generation logic

## The Simple Solution

The new approach is just ~200 lines and:
1. **Always provides schema retrieval code** (creates if missing)
2. **Shows natural language → AQL examples**
3. **Lets the LLM match patterns** instead of regex parsing

## Key Benefits

### 1. Simplicity
```python
# Old approach: Complex parsing
intent = self._detect_intent(natural_query)  # Regex patterns
entities = self._extract_entities(natural_query)  # More regex
constraints = self._extract_constraints(natural_query)  # Even more regex
aql = self._build_aql_for_intent(intent, entities, constraints)  # Complex logic

# New approach: Just show examples
prompt = f"""
Your query: "{natural_query}"

Examples:
- "Find similar bugs" → FOR doc IN search...
- "How was X fixed" → FOR error IN log_events...
"""
```

### 2. Schema Handling
The new version elegantly handles schema:
- Checks if schema exists
- Creates it automatically if missing
- Provides the code to do this
- No separate schema query handler needed

### 3. Flexibility
Instead of trying to understand every possible query pattern:
- Provides 7-8 common patterns
- Agent adapts them to specific needs
- Can combine patterns creatively

### 4. Maintainability
- No regex patterns to debug
- No entity extraction to maintain
- Just update examples when needed
- LLM handles variations naturally

## Example Comparison

### Complex Query: "Find unresolved Python errors in src/ from last week"

**Old Approach Would Need:**
- Detect intent: TIME_BASED + FIND_ERRORS
- Extract entities: 
  - time_range: "last week" → "7d"
  - file_pattern: "src/" → "src/%"
  - language: "Python" → ["SyntaxError", "IndentationError"]
  - status: "unresolved" → resolved != true
- Build complex AQL with all constraints

**New Approach:**
- Shows example #6 (Complex Filters)
- Agent sees the pattern and adapts it
- Natural understanding of "Python errors" and "last week"

## Implementation

The entire query converter becomes:

```python
def generate_agent_prompt(
    natural_query: str,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    file_path: Optional[str] = None,
    error_id: Optional[str] = None,
    include_schema_info: bool = True
) -> str:
    """Generate prompt with schema code and AQL examples."""
    
    prompt = f"""
# Natural Language to AQL Query Guide

## Your Query
"{natural_query}"

## Step 1: Get Database Schema
[Code to retrieve/create schema]

## Step 2: Natural Language to AQL Examples
[7-8 common patterns with AQL]

## Step 3: Execute Your Query
[Execution template]
"""
    return prompt
```

## Philosophy Alignment

This aligns perfectly with the tool philosophy:
1. **Returns a prompt** that guides the agent
2. **Provides patterns** not prescriptions  
3. **Empowers with examples** not constraints
4. **Trusts the LLM** to understand intent

## Migration Path

1. Keep the MCP tool interface the same
2. Replace the complex implementation with simple version
3. Remove all the regex/parsing code
4. Just return the prompt with examples

The agent gets better results with less code!