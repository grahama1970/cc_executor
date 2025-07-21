# AI Agent Memory System - 20 Realistic Usage Scenarios (UPDATED)

## Mission Statement

You are a Principal-level Software Engineer and Test Automation Specialist. Your primary mission is to systematically test, debug, and harden the ArangoDB tools for an AI agent's memory system by executing these 20 sophisticated usage scenarios.

**Your goal is not just to complete the scenarios, but to identify and fix bugs, ambiguities, and design flaws within the underlying Python tool code (`mcp_arango_tools.py`).**

## Context

The `script_logs` database is Claude's long-term memory system - a graph-based knowledge repository that tracks all interactions, errors, solutions, and learned patterns. This system enables Claude to:

- Remember past errors and their successful solutions
- Find similar problems using BM25 text search and graph relationships
- Learn from failures and build a knowledge base over time
- Track tool execution patterns and their outcomes
- Connect code artifacts to the problems they solve
- **NEW: Visualize data patterns and relationships with D3.js**
- **NEW: Detect anomalies and clusters in error patterns**
- **NEW: Convert natural language queries to AQL**
- **NEW: Track pattern evolution over time**

Think of it as Claude's "experience database" where every error encountered, every solution discovered, and every insight gained is stored and interconnected through graph relationships.

---

## Core Workflow: The "Test, Diagnose, Fix, Verify" Loop

**Do not move to the next scenario until the current one is successfully completed and all discovered issues are resolved.**

For each scenario, follow this loop:

### 1. Analyze the Scenario
- State the scenario number and title
- Describe the goal in your own words
- Identify which tools will be needed

### 2. Formulate a Plan
- Outline the sequence of arango-tools calls
- Include expected parameters for each tool
- Refer to `ARANGO_TOOLS_README.md` and tool docstrings
- Present the plan and **WAIT for approval**

### 3. Execute and Analyze

**If SUCCESS:**
- Show the expected outcome
- Update the test report
- Wait for "proceed to next scenario"

**If FAILURE or AMBIGUITY:**
- **STOP** and initiate Code Correction:
  - a. **Diagnose Root Cause**: Is it a bug in `mcp_arango_tools.py`? Misleading docstring? Logic flaw?
  - b. **Propose Fix**: Generate a code diff for `mcp_arango_tools.py`
  - c. **Explain Fix**: Justify why this solution is correct
  - d. **Wait for Approval**
  - e. **Verify**: Re-run the scenario to confirm it now works

### 4. Conclude and Proceed
- Summarize what was accomplished
- Document any fixes applied
- Update the incremental test report
- Wait for "proceed to next scenario"

### 🔴 CRITICAL REMINDER FOR EVERY SCENARIO 🔴
**BEFORE MOVING TO THE NEXT SCENARIO, YOU MUST:**
1. ✏️ **UPDATE mcp_arango_tools.py** with any fixes for ambiguities/bugs found
2. 📋 **UPDATE ARANGO_TOOLS_README.md** with corrected examples
3. 📊 **ADD to the test report** with failure patterns and solutions
4. 🔍 **VERIFY your fixes** by re-running failed operations

**Files to update after EACH scenario with issues:**
- `/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/mcp_arango_tools.py`
- `/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/ARANGO_TOOLS_README.md`
- Test report with tool chain analysis

---

## Resources

1. **Tool Implementation**: `/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/mcp_arango_tools.py`
2. **Documentation**: `ARANGO_TOOLS_README.md`
3. **Test Report**: `arango_tools_test_report.md` (update after each scenario)

---

## Progress Summary

### Overall Completion: 0/20 Scenarios
- [ ] Scenarios 1-5: Basic Operations & Recovery
- [ ] Scenarios 6-10: Pattern Analysis & Prediction  
- [ ] Scenarios 11-15: Knowledge Building & Analytics
- [ ] Scenarios 16-20: Advanced Integration & Learning

### Issues Fixed: 0
### Time Elapsed: Not started

---

## 20 Realistic Usage Scenarios

### Scenario 1: ModuleNotFoundError Pattern Recognition with Response Validation
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: "I'm getting 'ModuleNotFoundError: No module named numpy'. Have you seen this before? What worked?"

**Expected Claude Actions:**
- [ ] 1. schema() - Check available collections
- [ ] 2. english_to_aql("Find ModuleNotFoundError for numpy") - Use NLP to AQL
- [ ] 3. query() with generated AQL, check result['success']
- [ ] 4. If found: query graph traversal for solutions
- [ ] 5. If not found: 
   - [ ] a. Use perplexity-ask for research
   - [ ] b. Validate response with response-validator:
      ```
      await mcp__response_validator__validate_llm_response(
          response=perplexity_response,
          validation_type="content",
          expected_content=["numpy", "ModuleNotFoundError", "install", "pip"]
      )
      ```
   - [ ] c. Ensure validation_passed before proceeding
- [ ] 6. insert() solution and edge() to link
- [ ] 7. **NEW**: detect_anomalies() to check if this error is unusual
- [ ] 8. **VALIDATION**: Use response-validator to verify solution exists in corpus:
   ```
   await mcp__response_validator__validate_llm_response(
       response=solution_text,
       validation_type="quality",
       prompt="How to fix ModuleNotFoundError numpy"
   )
   ```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_

---

### Scenario 2: Tool Execution Performance Analysis with Visualization
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: My cc_execute tool keeps timing out. Can you analyze and visualize the pattern of failures?

**Expected Claude Actions:**
```
- [ ] 1. query("FOR t IN tool_executions FILTER t.tool_name == 'cc_execute' AND t.status == 'timeout' SORT t.start_time DESC LIMIT 20 RETURN t")
- [ ] 2. get_visualization_data("timeline", "tool_executions", filters='{"tool_name": "cc_execute", "status": "timeout"}')
- [ ] 3. analyze_time_series("tool_executions", "duration", group_by="hour")
- [ ] 4. prepare_graph_for_d3() to create visualization-ready data
- [ ] 5. insert() an insight about the pattern
- [ ] 6. edge() to link insight to affected tool executions
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 3: Code Change Impact Tracking with Graph Metrics
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: I just modified websocket_handler.py. What other files were typically modified together with this file in the past? Show me the dependency network.

**Expected Claude Actions:**
```
- [ ] 1. query("FOR c IN code_artifacts FILTER c.file_path =~ 'websocket_handler.py' RETURN c")
- [ ] 2. get_graph_metrics("artifact_lineage", start_node="code_artifacts/websocket_handler")
- [ ] 3. find_shortest_paths() between websocket_handler and related files
- [ ] 4. get_visualization_data("network", "code_artifacts")
- [ ] 5. calculate_page_rank() to find most influential files
- [ ] 6. upsert() current modification and create edges
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 4: Learning from Repeated Errors with Clustering
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: I keep getting the same Redis connection errors. Build a lesson from all instances and find clusters of similar errors.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find all Redis connection errors") 
- [ ] 2. query() with generated AQL
- [ ] 3. find_clusters("error_causality", algorithm="louvain")
- [ ] 4. For each cluster: analyze_graph_patterns()
- [ ] 5. insert() into lessons_learned with cluster analysis
- [ ] 6. track_pattern_evolution() to see how fixes evolved
- [ ] 7. detect_anomalies() to find outlier error patterns
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 5: Session Recovery with Visualization
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: My last session crashed. What was I working on and where did I leave off? Show me the workflow visually.

**Expected Claude Actions:**
```
- [ ] 1. query("FOR s IN agent_sessions FILTER s.status != 'completed' SORT s.start_time DESC LIMIT 1 RETURN s")
- [ ] 2. get_visualization_data("flow", "agent_flow", filters='{"session_id": "@id"}')
- [ ] 3. prepare_graph_for_d3() with session data
- [ ] 4. get_node_centrality() to find key decision points
- [ ] 5. Reconstruct session state from graph
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 6: Smart Error Prediction with Pattern Analysis
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: I'm about to run a data migration script. What errors should I watch out for based on similar past runs?

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find errors from migration scripts")
- [ ] 2. query() with generated AQL
- [ ] 3. analyze_graph_patterns("error_causality", pattern_type="sequential")
- [ ] 4. detect_cycles() in error chains
- [ ] 5. get_visualization_data("distribution", "errors_and_failures")
- [ ] 6. Create predictive insight document with risk scores
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 7: Research Cache Optimization with Time Analysis and Validation
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Check if we've already researched 'ArangoDB transaction timeout' errors before querying perplexity. Show research patterns over time.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find research about ArangoDB transaction timeout")
- [ ] 2. query() for research_cache, check result['success']
- [ ] 3. analyze_time_series("research_cache", "created_at", window="day")
- [ ] 4. track_pattern_evolution("research_topics", time_field="timestamp")
- [ ] 5. If not found: 
      a. Use perplexity-ask:
         perplexity_ask(messages=[{
             "role": "user",
             "content": "How to handle ArangoDB transaction timeout errors? Include specific error codes and solutions."
         }])
      b. Validate perplexity response:
         await mcp__response_validator__validate_llm_response(
             response=perplexity_response,
             validation_type="content",
             expected_content=["ArangoDB", "transaction", "timeout", "error"]
         )
      c. Check for quality:
         await mcp__response_validator__validate_llm_response(
             response=perplexity_response,
             validation_type="quality",
             prompt="ArangoDB transaction timeout errors"
         )
      d. Only if validation_passed: insert() into research_cache
- [ ] 6. Link research to relevant errors with confidence score based on validation
```

**Validation Requirements:**
- Response must contain specific ArangoDB error codes
- Must provide actionable solutions, not generic advice
- Quality score must indicate no hallucination phrases

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 8: Multi-Step Solution Validation with Metrics
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Apply the stored solution for ImportError but verify it actually works this time. Track success metrics.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find resolved ImportError with solutions")
- [ ] 2. Traverse to solution via error_causality
- [ ] 3. Apply solution and track outcome
- [ ] 4. insert() into solution_outcomes with success metrics
- [ ] 5. get_graph_metrics() for solution effectiveness
- [ ] 6. Update lesson confidence based on outcome
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 9: Dependency Chain Analysis with Visualization
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Show me the cascade of errors that resulted from the initial 'requests' module missing. Visualize the cascade.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find first error about requests module")
- [ ] 2. query() to find root error
- [ ] 3. get_visualization_data("hierarchy", "error_causality", start_node="@error_id")
- [ ] 4. find_shortest_paths() to all downstream errors
- [ ] 5. prepare_graph_for_d3() with cascade data
- [ ] 6. insert() insight about dependency chains
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 10: Tool Usage Patterns with Network Analysis
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Which tools do I typically use together? I want to optimize my workflow. Show me the tool network.

**Expected Claude Actions:**
```
- [ ] 1. get_visualization_data("network", "tool_dependencies")
- [ ] 2. find_clusters("tool_dependencies", algorithm="label_propagation")
- [ ] 3. calculate_page_rank() to find most central tools
- [ ] 4. get_node_centrality("betweenness") for bridge tools
- [ ] 5. analyze_graph_patterns() for common sequences
- [ ] 6. insert() workflow optimization suggestions
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 11: Glossary Enhancement with Semantic Analysis
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Define 'circular import' based on all the times we've encountered it. Find semantic clusters of related errors.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find all circular import errors")
- [ ] 2. query() for all occurrences
- [ ] 3. find_clusters() based on error message similarity
- [ ] 4. analyze_graph_patterns() for common contexts
- [ ] 5. upsert() glossary_terms with comprehensive definition
- [ ] 6. edge() to link term to all related errors
- [ ] 7. Add semantic relationships to other import errors
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 12: Time-to-Resolution Analytics Dashboard
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: How long does it typically take to fix ModuleNotFoundError vs SyntaxError? Create a comparison dashboard.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find resolved errors with fix times")
- [ ] 2. query() with aggregation by error type
- [ ] 3. analyze_time_series() for resolution trends
- [ ] 4. get_visualization_data("distribution", "error_causality")
- [ ] 5. detect_anomalies() for unusually long fixes
- [ ] 6. prepare_graph_for_d3() with comparative data
- [ ] 7. insert() performance insight
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 13: Context-Aware Search with Graph Context
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Find all errors related to 'async' but only in websocket contexts. Show the error network.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find async errors in websocket files")
- [ ] 2. query() with BM25 search
- [ ] 3. get_visualization_data("network") for error relationships
- [ ] 4. find_clusters() to group related async errors
- [ ] 5. analyze_graph_patterns() for common async patterns
- [ ] 6. Group by error patterns and contexts
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 14: Solution Effectiveness Tracking with Evolution
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**🔴 REMINDER: If ANY errors occur:**
1. ✏️ UPDATE mcp_arango_tools.py with fixes
2. 📋 UPDATE ARANGO_TOOLS_README.md 
3. 📊 ADD to test report
4. 🔍 VERIFY fixes work

**Prompt**: Which solutions have the highest success rate for fixing import errors? How have they evolved?

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find solutions for import errors with outcomes")
- [ ] 2. query() with success rate aggregation
- [ ] 3. track_pattern_evolution("solution_outcomes", group_by="solution_type")
- [ ] 4. get_visualization_data("timeline") for evolution
- [ ] 5. detect_anomalies() for solutions that stopped working
- [ ] 6. Update lessons_learned with best practices
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 15: Circular Dependency Detection with Visualization
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Check if fixing error A caused error B which was fixed by something that caused error A again. Visualize the cycle.

**Expected Claude Actions:**
```
- [ ] 1. detect_cycles("error_causality", max_depth=10)
- [ ] 2. For each cycle: get_visualization_data("network", nodes=cycle_nodes)
- [ ] 3. find_shortest_paths() within cycles
- [ ] 4. prepare_graph_for_d3() with cycle highlighting
- [ ] 5. insert() warning about circular fixes
- [ ] 6. Suggest cycle-breaking strategies
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 16: Session Handoff with Knowledge Graph
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Summarize everything I learned in this session for the next Claude instance. Create a knowledge graph.

**Expected Claude Actions:**
```
- [ ] 1. query("FOR s IN agent_sessions FILTER s.session_id == @current_session RETURN s")
- [ ] 2. get_visualization_data("network", "agent_flow", session_filter=true)
- [ ] 3. get_graph_metrics() for session complexity
- [ ] 4. find_clusters() in session activities
- [ ] 5. calculate_page_rank() for key insights
- [ ] 6. prepare_graph_for_d3() for handoff visualization
- [ ] 7. Create comprehensive handoff document
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 17: Proactive Error Prevention with ML
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: I'm about to work with pandas DataFrames. What errors should I avoid based on history? Use anomaly detection.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find all pandas and DataFrame errors")
- [ ] 2. query() for historical errors
- [ ] 3. detect_anomalies("errors_and_failures", features=["error_type", "context"])
- [ ] 4. find_clusters() for error groups
- [ ] 5. analyze_graph_patterns() for prevention strategies
- [ ] 6. track_pattern_evolution() for trending issues
- [ ] 7. Provide proactive guidance with risk scores
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 18: Knowledge Confidence with Network Analysis
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Which lessons have been validated most often and should be trusted? Show the validation network.

**Expected Claude Actions:**
```
- [ ] 1. query("FOR l IN lessons_learned SORT l.evidence_count DESC, l.confidence DESC LIMIT 10 RETURN l")
- [ ] 2. get_node_centrality("eigenvector") for lesson influence
- [ ] 3. get_visualization_data("network", "lesson_applications")
- [ ] 4. find_shortest_paths() from lessons to outcomes
- [ ] 5. calculate_page_rank() for most referenced lessons
- [ ] 6. Update confidence scores based on network position
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 19: Cross-Session Pattern Mining with Time Series
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: Find patterns in errors that occur across multiple sessions but in similar contexts. Show temporal patterns.

**Expected Claude Actions:**
```
- [ ] 1. english_to_aql("Find errors grouped by pattern and context")
- [ ] 2. query() with cross-session aggregation
- [ ] 3. analyze_time_series("errors_and_failures", "timestamp", group_by="pattern")
- [ ] 4. track_pattern_evolution() across sessions
- [ ] 5. find_clusters() in temporal patterns
- [ ] 6. get_visualization_data("timeline") for pattern trends
- [ ] 7. insert() discovered patterns as insights
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 20: Intelligent Debugging Assistant with Full Stack
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: I have a complex error with multiple potential causes. Guide me through systematic debugging with visualizations.

**Expected Claude Actions:**
```
- [ ] 1. insert() the complex error with full context
- [ ] 2. english_to_aql("Find similar complex errors") 
- [ ] 3. query() with advanced search
- [ ] 4. analyze_graph_patterns() for error signatures
- [ ] 5. find_clusters() for related issues
- [ ] 6. detect_anomalies() to identify unique aspects
- [ ] 7. get_visualization_data("network") for error ecosystem
- [ ] 8. calculate_page_rank() for root cause analysis
- [ ] 9. prepare_graph_for_d3() for interactive debugging
- [ ] 10. If no matches: use perplexity-ask
- [ ] 11. Create step-by-step debugging plan with visuals
- [ ] 12. Track each attempt in solution_outcomes
- [ ] 13. Build new lesson from successful resolution
```

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

### Scenario 21: LLM Response Validation Against Corpus
- [ ] **Started**
- [ ] **Plan Approved**
- [ ] **Executed Successfully**
- [ ] **Report Updated**
- [ ] **Completed**

**Prompt**: "Research best practices for handling asyncio timeouts in Python and validate the response against our knowledge base."

**🔴 CRITICAL: This scenario tests the new response-validator tool to prevent hallucinations**

**Expected Claude Actions:**
```
- [ ] 1. Query knowledge base for existing asyncio timeout information:
      query("FOR doc IN research_cache FILTER doc.topic =~ 'asyncio' AND doc.topic =~ 'timeout' RETURN doc")
      
- [ ] 2. Use universal-llm-executor to ask Gemini:
      execute_llm("gemini", "What are best practices for handling asyncio timeouts in Python?")
      
- [ ] 3. Parse Gemini's response:
      parse_llm_output(output_file=gemini_output_path)
      
- [ ] 4. Validate format and structure:
      await mcp__response_validator__validate_llm_response(
          response=gemini_response,
          validation_type="format"
      )
      
- [ ] 5. Validate content against corpus:
      await mcp__response_validator__validate_llm_response(
          response=gemini_response,
          validation_type="content",
          expected_content=["asyncio", "timeout", "wait_for", "TimeoutError"]
      )
      
- [ ] 6. Check for hallucination indicators:
      await mcp__response_validator__validate_llm_response(
          response=gemini_response,
          validation_type="quality",
          prompt="asyncio timeout best practices"
      )
      
- [ ] 7. If validation_passed for all checks:
      - Extract specific claims from response
      - For each claim, query corpus for supporting evidence:
        query("FOR doc IN knowledge_base FILTER doc.content =~ @claim RETURN doc")
      
- [ ] 8. Use perplexity-ask to verify uncertain claims:
      perplexity_ask(messages=[{
          "role": "user", 
          "content": f"Is this claim about asyncio timeouts correct: {uncertain_claim}?"
      }])
      
- [ ] 9. Validate perplexity response:
      await mcp__response_validator__validate_llm_response(
          response=perplexity_response,
          validation_type="content",
          expected_content=["asyncio", specific_function_names]
      )
      
- [ ] 10. Create validated knowledge entry:
       insert(
           message="Validated asyncio timeout best practices",
           metadata=json.dumps({
               "validation_scores": validation_results,
               "supported_claims": supported_claims,
               "unsupported_claims": unsupported_claims,
               "sources": ["gemini", "perplexity", "corpus"]
           })
       )
       
- [ ] 11. Use litellm-batch for multi-model validation:
       process_batch_requests([
           {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": asyncio_question}]},
           {"model": "claude-3-haiku-20240307", "messages": [{"role": "user", "content": asyncio_question}]}
       ])
       
- [ ] 12. Validate batch responses:
       for response in batch_results:
           await mcp__response_validator__validate_llm_response(
               response=response['response'],
               validation_type="litellm_batch"
           )
```

**Validation Checks to Implement:**
1. **Groundedness Check**: Every claim must trace back to corpus evidence
2. **Citation Validation**: Any code examples must be verifiable
3. **Consistency Check**: Multiple LLMs should agree on core facts
4. **Hallucination Detection**: Flag phrases like "as of my training data"
5. **Factual Accuracy**: Cross-reference with Python documentation

**Success Criteria:**
- All validation checks must pass with validation_passed=true
- At least 80% of claims must have corpus support
- No hallucination indicators detected
- Multiple LLMs agree on key recommendations

**Issues Found**: _None yet_
**Fixes Applied**: _None yet_
---

## Usage Instructions

These scenarios demonstrate how Claude's enhanced memory system enables:
- **Pattern Recognition**: Finding similar errors and proven solutions
- **Relationship Tracking**: Understanding cause-and-effect chains
- **Learning Accumulation**: Building knowledge that improves over time
- **Predictive Assistance**: Anticipating problems before they occur
- **Context-Aware Search**: Combining text search with graph relationships
- **Visual Analytics**: Creating interactive visualizations of patterns
- **Anomaly Detection**: Finding unusual behaviors and outliers
- **Natural Language Queries**: Converting English to AQL automatically
- **Temporal Analysis**: Understanding how patterns evolve over time
- **Network Analysis**: Finding influential nodes and communities

Each scenario uses multiple MCP tools in combination to provide intelligent, experience-based assistance.

---

## Final Report Generation

After completing all 20 scenarios, Claude will generate a comprehensive test report:

### Report Structure

```markdown
# Arango Tools MCP Test Report
Generated: [timestamp]

## Executive Summary
- Total Scenarios Tested: 20
- Successful Operations: X/Y
- Errors Encountered: Z
- Recovery Success Rate: X%
- New Patterns Discovered: N
- Visualizations Generated: V

## Tool Usage Statistics
- schema(): X calls (Y successful)
- query(): X calls (Y successful) 
- insert(): X calls (Y successful)
- edge(): X calls (Y successful)
- upsert(): X calls (Y successful)
- english_to_aql(): X calls (Y successful)
- get_visualization_data(): X calls (Y successful)
- find_clusters(): X calls (Y successful)
- detect_anomalies(): X calls (Y successful)
- analyze_time_series(): X calls (Y successful)
- track_pattern_evolution(): X calls (Y successful)

## Performance Metrics
- Average query response time: Xms
- Average visualization prep time: Xms
- Slowest operation: [details]
- Database growth: X documents, Y edges
- Patterns discovered: P

## Error Analysis
### Errors Encountered
1. [Error Type]: [Count]
   - Recovery method: [what worked]
   - Time to resolve: [duration]

### Unresolved Issues
- [Issue]: [attempted solutions]

## Knowledge Base Growth
### New Lessons Learned
1. [Lesson]: Evidence count: X, Confidence: Y%

### Enhanced Glossary Terms
- [Term]: [Definition based on X occurrences]

### Discovered Patterns
1. [Pattern]: Frequency: X, Context: [details]

### Detected Anomalies
1. [Anomaly]: Deviation: X%, Impact: [details]

## Graph Insights
### Most Connected Nodes
- [Node]: [Inbound: X, Outbound: Y, PageRank: Z]

### Longest Successful Solution Chains
1. [Error] → [Step 1] → [Step 2] → [Resolution]

### Circular Dependencies Detected
- [A] → [B] → [C] → [A]

### Community Detection Results
- Cluster 1: [Nodes], Theme: [description]
- Cluster 2: [Nodes], Theme: [description]

## Visualization Success
### Generated Visualizations
- Network diagrams: X
- Timeline charts: Y
- Distribution plots: Z
- Flow diagrams: N

### Most Insightful Visualizations
1. [Title]: [Key insight revealed]

## Natural Language Query Performance
### English to AQL Success Rate
- Total conversions: X
- Successful executions: Y%
- Most complex query: [example]

## Integration Success
### Perplexity-Ask Usage
- Times consulted: X
- Useful responses: Y
- Cached for future: Z

### Cross-Tool Patterns
- Most common sequence: [tool1] → [tool2] → [tool3]
- Success rate: X%

### D3 Visualizer Integration
- Successful pipelines: X
- Average render time: Yms
- Most effective layouts: [list]

## Recommendations
1. **Optimization Opportunities**
   - [Specific improvement]

2. **Missing Capabilities**
   - [Feature that would help]

3. **Best Practices Discovered**
   - [Practice]: [Why it works]

## Test Coverage Analysis
### Scenarios by Category
- Error Recovery: X/Y tested
- Performance Analysis: X/Y tested  
- Graph Traversal: X/Y tested
- Knowledge Building: X/Y tested
- Pattern Analysis: X/Y tested
- Visualization: X/Y tested

### Edge Cases Tested
✅ Empty results handling
✅ Non-existent collections
✅ Circular references
✅ Concurrent access
✅ Large result sets
✅ Invalid English queries
✅ Visualization data limits
❌ [Untested case]

## Database State Summary
### Before Testing
- Documents: 0
- Edges: 0
- Insights: 0

### After Testing
- Documents: X
- Edges: Y  
- Insights: Z
- Lessons: N
- Research Cache Entries: M
- Query Patterns: Q
- Detected Anomalies: A
- Identified Clusters: C

## Conclusion
[Summary of overall system readiness, key findings, and confidence level]

### Critical Findings
1. [Most important discovery]
2. [Key limitation found]
3. [Unexpected behavior]

### Success Metrics
- Can find similar errors: ✅/❌
- Can track solution effectiveness: ✅/❌
- Can prevent repeated mistakes: ✅/❌
- Can learn from patterns: ✅/❌
- Can handle errors gracefully: ✅/❌
- Can visualize relationships: ✅/❌
- Can detect anomalies: ✅/❌
- Can understand natural language: ✅/❌

### Next Steps
1. [Recommended action]
2. [Follow-up testing needed]
3. [Documentation updates required]
```

### Report Generation Code

Claude will execute this final analysis:

```python
# Aggregate all test results
results_query = '''
LET stats = {
  total_errors: LENGTH(FOR e IN errors_and_failures RETURN 1),
  resolved_errors: LENGTH(FOR e IN errors_and_failures FILTER e.resolved == true RETURN 1),
  total_insights: LENGTH(FOR i IN agent_insights RETURN 1),
  total_lessons: LENGTH(FOR l IN lessons_learned RETURN 1),
  total_edges: LENGTH(FOR e IN error_causality RETURN 1) + 
               LENGTH(FOR e IN agent_flow RETURN 1) +
               LENGTH(FOR e IN artifact_lineage RETURN 1),
  avg_fix_time: AVG(FOR e IN error_causality FILTER e.fix_time_minutes != null RETURN e.fix_time_minutes),
  tool_usage: (FOR t IN tool_executions 
               COLLECT tool = t.tool_name WITH COUNT INTO uses 
               RETURN {tool: tool, count: uses}),
  error_patterns: (FOR e IN errors_and_failures 
                   COLLECT type = e.error_type WITH COUNT INTO count 
                   FILTER count > 1 
                   RETURN {type: type, occurrences: count}),
  query_patterns: LENGTH(FOR q IN query_patterns RETURN 1),
  detected_anomalies: LENGTH(FOR a IN anomaly_detections RETURN 1),
  visualization_count: LENGTH(FOR v IN visualization_metadata RETURN 1)
}
RETURN stats
'''

# Execute comprehensive analysis queries
# Generate markdown report
# Save report as artifact
```

This comprehensive report will provide complete visibility into:
- What was tested
- What worked/failed  
- What was learned
- How the system performed
- What improvements are needed
- How well the new features integrate

---

## Expected Outcomes from This Process

By following the "Test, Diagnose, Fix, Verify" loop:

1. **Hardened Tool Code**: `mcp_arango_tools.py` will become more robust with:
   - Better parameter validation
   - Clearer error messages
   - Improved docstrings
   - Fixed edge cases
   - Optimized performance

2. **Knowledge Base**: Each fix becomes a lesson stored in the database itself

3. **Living Documentation**: The test report becomes a guide for future users

4. **Self-Improving System**: The AI agent learns to fix its own tools

5. **Visual Intelligence**: The system can now show, not just tell

Remember: **Success is not just completing scenarios, but improving the tools for all future users.**