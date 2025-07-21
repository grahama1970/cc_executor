```json
{
  "new_patterns": [
    {
      "id": 91,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR t IN tool_executions FILTER t.exit_code != 0 RETURN {tool: t.tool_name, exit_code: t.exit_code, command: t.command}",
      "description": "Find tool executions that did not exit successfully (exit code is not 0).",
      "english_variations": {
        "layperson": "Which tools had problems?",
        "mba": "Identify tool failures based on non-zero exit codes to assess operational friction.",
        "developer": "Get tools where exit_code is not 0.",
        "dba": "SELECT tool_name, exit_code, command FROM tool_executions WHERE exit_code <> 0"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 92,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR t IN tool_executions FILTER t.status == 'timeout' RETURN {tool: t.tool_name, command: t.command, duration_ms: t.duration_ms}",
      "description": "Find all tool executions that timed out.",
      "english_variations": {
        "layperson": "Which tools timed out?",
        "mba": "Identify tool timeouts affecting workflow completion and productivity.",
        "developer": "Get tool executions with status 'timeout'.",
        "dba": "SELECT tool_name, command, duration_ms FROM tool_executions WHERE status = 'timeout'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 93,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR s IN agent_sessions FILTER s.agent_name == 'gpt-engineer' RETURN s",
      "description": "Get all sessions for the 'gpt-engineer' agent.",
      "english_variations": {
        "layperson": "Show me what the gpt-engineer agent did.",
        "mba": "Review all sessions by the gpt-engineer agent for performance evaluation.",
        "developer": "Filter agent_sessions where agent_name is 'gpt-engineer'.",
        "dba": "SELECT * FROM agent_sessions WHERE agent_name = 'gpt-engineer'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 94,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR e IN log_events FILTER e.level IN ['CRITICAL', 'ERROR'] SORT e.timestamp DESC LIMIT 20 RETURN {timestamp: e.timestamp, level: e.level, message: e.message}",
      "description": "Get the 20 most recent critical and error logs.",
      "english_variations": {
        "layperson": "What are the latest big problems?",
        "mba": "Show the 20 most recent high-severity events for immediate review.",
        "developer": "Get recent logs where level is CRITICAL or ERROR.",
        "dba": "SELECT timestamp, level, message FROM log_events WHERE level IN ('CRITICAL', 'ERROR') ORDER BY timestamp DESC LIMIT 20"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 95,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR l IN lessons_learned FILTER l.confidence < 0.5 RETURN l",
      "description": "Find lessons learned that have a low confidence score (less than 0.5).",
      "english_variations": {
        "layperson": "What lessons are we not very sure about?",
        "mba": "Identify low-confidence knowledge entries for validation and review.",
        "developer": "Get lessons where confidence is less than 0.5.",
        "dba": "SELECT * FROM lessons_learned WHERE confidence < 0.5"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 96,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR s IN solution_outcomes FILTER s.outcome != 'success' RETURN s",
      "description": "Find all solution outcomes that were not fully successful.",
      "english_variations": {
        "layperson": "Which solutions didn't work out perfectly?",
        "mba": "Analyze partial or failed solution outcomes to improve future strategies.",
        "developer": "Get solution_outcomes where outcome is not 'success'.",
        "dba": "SELECT * FROM solution_outcomes WHERE outcome <> 'success'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 97,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR c IN code_artifacts FILTER c.operation == 'create' RETURN {file_path: c.file_path, language: c.language}",
      "description": "Find all code artifacts that represent newly created files.",
      "english_variations": {
        "layperson": "What new files were made?",
        "mba": "Track the creation of new code assets for project progress monitoring.",
        "developer": "Filter code_artifacts for 'create' operations.",
        "dba": "SELECT file_path, language FROM code_artifacts WHERE operation = 'create'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 98,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR e IN errors_and_failures FILTER e.resolved == true RETURN {error_type: e.error_type, resolution: e.resolution}",
      "description": "Find all errors that have been marked as resolved.",
      "english_variations": {
        "layperson": "Show me the problems we've already fixed.",
        "mba": "Review the log of resolved issues and their solutions.",
        "developer": "Get errors where the 'resolved' flag is true.",
        "dba": "SELECT error_type, resolution FROM errors_and_failures WHERE resolved = TRUE"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 99,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR g IN glossary_terms FILTER g.category == 'security' RETURN g.term",
      "description": "Find all glossary terms belonging to the 'security' category.",
      "english_variations": {
        "layperson": "What security terms do we have defined?",
        "mba": "List all defined terms under the 'security' category for compliance and training.",
        "developer": "Get glossary terms where category is 'security'.",
        "dba": "SELECT term FROM glossary_terms WHERE category = 'security'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 100,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR r IN research_cache FILTER r.status == 'failed' RETURN r",
      "description": "Find all research cache entries that have a 'failed' status.",
      "english_variations": {
        "layperson": "Which research tasks failed?",
        "mba": "Identify failures in the research caching process to ensure data availability.",
        "developer": "Get research_cache items with a 'failed' status.",
        "dba": "SELECT * FROM research_cache WHERE status = 'failed'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 101,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR i IN agent_insights FILTER i.priority > 3 RETURN i",
      "description": "Find agent insights with a priority level greater than 3.",
      "english_variations": {
        "layperson": "What are the most important insights from the agents?",
        "mba": "Surface high-priority agent insights for strategic decision-making.",
        "developer": "Filter agent_insights for priority > 3.",
        "dba": "SELECT * FROM agent_insights WHERE priority > 3"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 102,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR c IN code_artifacts FILTER c.language == 'JavaScript' AND c.size > 10000 RETURN {file_path: c.file_path, size: c.size}",
      "description": "Find JavaScript files that are larger than 10KB.",
      "english_variations": {
        "layperson": "Are there any big JavaScript files?",
        "mba": "Identify large JavaScript assets that could impact performance or maintenance overhead.",
        "developer": "Find JS artifacts with size over 10000 bytes.",
        "dba": "SELECT file_path, size FROM code_artifacts WHERE language = 'JavaScript' AND size > 10000"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 103,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR s IN agent_sessions FILTER s.status == 'completed' AND s.duration_ms < 60000 RETURN s.session_id",
      "description": "Find sessions that completed in under a minute.",
      "english_variations": {
        "layperson": "Any really quick work sessions?",
        "mba": "Identify short-duration completed sessions for efficiency analysis.",
        "developer": "Get completed sessions with duration under 60 seconds.",
        "dba": "SELECT session_id FROM agent_sessions WHERE status = 'completed' AND duration_ms < 60000"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 104,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR log IN log_events FILTER log.error_type == 'ValueError' RETURN log.message",
      "description": "Get the message for all logs where the error type is 'ValueError'.",
      "english_variations": {
        "layperson": "What caused the 'value' errors?",
        "mba": "Review messages for ValueError incidents to understand data input issues.",
        "developer": "Get messages from logs with error_type 'ValueError'.",
        "dba": "SELECT message FROM log_events WHERE error_type = 'ValueError'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 105,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR l IN lessons_learned FILTER 'api' IN l.applies_to RETURN l.lesson",
      "description": "Find all lessons learned that apply to 'api'.",
      "english_variations": {
        "layperson": "What have we learned about APIs?",
        "mba": "Collate all learned lessons related to API development and integration.",
        "developer": "Get lessons where 'api' is in the applies_to array.",
        "dba": "SELECT lesson FROM lessons_learned WHERE 'api' = ANY(applies_to)"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 106,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR g IN glossary_terms FILTER g.usage_count == 0 RETURN g",
      "description": "Find glossary terms that have never been used.",
      "english_variations": {
        "layperson": "Are there any terms we defined but never use?",
        "mba": "Identify unused glossary terms to streamline the knowledge base.",
        "developer": "Get glossary terms with a usage_count of 0.",
        "dba": "SELECT * FROM glossary_terms WHERE usage_count = 0"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 107,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR s IN solution_outcomes FILTER s.category == 'optimization' RETURN s",
      "description": "Get all solution outcomes related to 'optimization'.",
      "english_variations": {
        "layperson": "Show me the optimization solutions we tried.",
        "mba": "Review all optimization-focused solution outcomes.",
        "developer": "Filter solution_outcomes where category is 'optimization'.",
        "dba": "SELECT * FROM solution_outcomes WHERE category = 'optimization'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 108,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures FILTER e.stack_trace == null AND e.resolved == false RETURN e",
      "description": "Find unresolved errors that are missing a stack trace.",
      "english_variations": {
        "layperson": "Which unsolved problems have no details?",
        "mba": "Identify unresolved errors with incomplete diagnostic data.",
        "developer": "Find unresolved errors where stack_trace is null.",
        "dba": "SELECT * FROM errors_and_failures WHERE stack_trace IS NULL AND resolved = FALSE"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 109,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR t IN tool_executions FILTER t.tool_name == 'grep' RETURN t",
      "description": "Find all executions of the 'grep' tool.",
      "english_variations": {
        "layperson": "When was 'grep' used?",
        "mba": "Track usage of the 'grep' utility for operational analysis.",
        "developer": "Filter tool_executions for 'grep'.",
        "dba": "SELECT * FROM tool_executions WHERE tool_name = 'grep'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 110,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER log.script_name == 'data_processor.py' AND log.level == 'WARNING' RETURN log",
      "description": "Find all warnings from a specific script.",
      "english_variations": {
        "layperson": "What warnings did the data processor script give?",
        "mba": "Review warning-level events from the data_processor.py script.",
        "developer": "Get warnings from 'data_processor.py'.",
        "dba": "SELECT * FROM log_events WHERE script_name = 'data_processor.py' AND level = 'WARNING'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 111,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR artifact IN code_artifacts FILTER artifact.language == 'YAML' RETURN artifact.file_path",
      "description": "List the file paths of all YAML artifacts.",
      "english_variations": {
        "layperson": "Show me all the YAML files.",
        "mba": "Inventory all YAML configuration files for audit purposes.",
        "developer": "Get file paths for all YAML artifacts.",
        "dba": "SELECT file_path FROM code_artifacts WHERE language = 'YAML'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 112,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR session IN agent_sessions FILTER session.metadata.task_type == 'bug_fix' RETURN session",
      "description": "Find all agent sessions that were for a 'bug_fix' task.",
      "english_variations": {
        "layperson": "Which sessions were about fixing bugs?",
        "mba": "Analyze sessions dedicated to bug fixes to measure remediation efforts.",
        "developer": "Filter sessions where metadata.task_type is 'bug_fix'.",
        "dba": "SELECT * FROM agent_sessions WHERE metadata.task_type = 'bug_fix'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 113,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR s IN solution_outcomes FILTER s.success_score >= 0.9 RETURN s",
      "description": "Get highly successful solution outcomes (score of 0.9 or higher).",
      "english_variations": {
        "layperson": "Which solutions were very successful?",
        "mba": "Identify top-performing solutions to codify best practices.",
        "developer": "Filter solutions with success_score >= 0.9.",
        "dba": "SELECT * FROM solution_outcomes WHERE success_score >= 0.9"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 114,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR insight IN agent_insights RETURN insight.insight_text",
      "description": "List the text of all insights generated by agents.",
      "english_variations": {
        "layperson": "What insights have the agents found?",
        "mba": "Review all generated agent insights.",
        "developer": "Get the insight_text from all agent_insights.",
        "dba": "SELECT insight_text FROM agent_insights"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 115,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR term IN glossary_terms FILTER 'deprecated' IN term.tags RETURN term",
      "description": "Find all glossary terms that are tagged as 'deprecated'.",
      "english_variations": {
        "layperson": "Which terms are out of date?",
        "mba": "Identify deprecated terms in the knowledge base for archival.",
        "developer": "Find glossary terms with the 'deprecated' tag.",
        "dba": "SELECT * FROM glossary_terms WHERE 'deprecated' = ANY(tags)"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 116,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR log IN log_events FILTER log.level == 'DEBUG' LIMIT 50 RETURN log",
      "description": "Get up to 50 debug-level log events.",
      "english_variations": {
        "layperson": "Can I see some debug messages?",
        "mba": "Sample debug-level events for granular operational analysis.",
        "developer": "Get 50 logs with level DEBUG.",
        "dba": "SELECT * FROM log_events WHERE level = 'DEBUG' LIMIT 50"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 117,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR error IN errors_and_failures FILTER error.is_flaky == true RETURN error",
      "description": "Find all errors that have been marked as 'flaky'.",
      "english_variations": {
        "layperson": "Which errors are intermittent?",
        "mba": "Identify flaky errors to prioritize for stability improvements.",
        "developer": "Get errors where is_flaky is true.",
        "dba": "SELECT * FROM errors_and_failures WHERE is_flaky = TRUE"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 118,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR tool IN tool_executions FILTER tool.user_approved == false RETURN tool",
      "description": "Find tool executions that were run without user approval.",
      "english_variations": {
        "layperson": "Did the agent run any tools it wasn't supposed to?",
        "mba": "Audit for unapproved tool executions for security and compliance review.",
        "developer": "Find tools where user_approved is false.",
        "dba": "SELECT * FROM tool_executions WHERE user_approved = FALSE"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 119,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR lesson IN lessons_learned FILTER lesson.evidence_count < 3 RETURN lesson",
      "description": "Find lessons that are supported by little evidence (less than 3 instances).",
      "english_variations": {
        "layperson": "Which lessons are based on just a few examples?",
        "mba": "Identify lessons with a weak evidence base for further validation.",
        "developer": "Get lessons with an evidence_count less than 3.",
        "dba": "SELECT * FROM lessons_learned WHERE evidence_count < 3"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 120,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR s IN agent_sessions FILTER s.status == 'running' RETURN s",
      "description": "Find all agent sessions that are currently in a 'running' state.",
      "english_variations": {
        "layperson": "What agents are running right now?",
        "mba": "Monitor currently active agent sessions for real-time operational oversight.",
        "developer": "Get sessions with status 'running'.",
        "dba": "SELECT * FROM agent_sessions WHERE status = 'running'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 121,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR artifact IN code_artifacts FILTER artifact.operation == 'delete' RETURN artifact.file_path",
      "description": "List all files that have been deleted.",
      "english_variations": {
        "layperson": "What files got deleted?",
        "mba": "Track deleted code assets as part of change management.",
        "developer": "Find artifacts with the 'delete' operation.",
        "dba": "SELECT file_path FROM code_artifacts WHERE operation = 'delete'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 122,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR solution IN solution_outcomes FILTER solution.reverted == true RETURN solution",
      "description": "Find all solutions that were later reverted.",
      "english_variations": {
        "layperson": "Which fixes had to be undone?",
        "mba": "Analyze reverted solutions to understand failure modes of proposed fixes.",
        "developer": "Get solutions where the 'reverted' flag is true.",
        "dba": "SELECT * FROM solution_outcomes WHERE reverted = TRUE"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 123,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR e IN errors_and_failures FILTER e.error_type == 'PermissionError' RETURN e",
      "description": "Get all errors of type 'PermissionError'.",
      "english_variations": {
        "layperson": "Show me all the permission errors.",
        "mba": "Review all 'PermissionError' incidents to address access control issues.",
        "developer": "Filter errors_and_failures for 'PermissionError'.",
        "dba": "SELECT * FROM errors_and_failures WHERE error_type = 'PermissionError'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 124,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR log IN log_events FILTER log.session_id == 'session_001' RETURN log",
      "description": "Get all log events for a specific session ID.",
      "english_variations": {
        "layperson": "Show me everything that happened in session_001.",
        "mba": "Retrieve all log data for 'session_001' for a detailed audit.",
        "developer": "Get all logs for session_id 'session_001'.",
        "dba": "SELECT * FROM log_events WHERE session_id = 'session_001'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 125,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR tool IN tool_executions FILTER tool.duration_ms > 300000 RETURN tool",
      "description": "Find tool executions that took longer than 5 minutes.",
      "english_variations": {
        "layperson": "Which tools took a really long time to run?",
        "mba": "Identify exceptionally long-running tool executions that are outliers.",
        "developer": "Find tool runs with duration over 300,000 ms.",
        "dba": "SELECT * FROM tool_executions WHERE duration_ms > 300000"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 126,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR error IN errors_and_failures FILTER error.resolved == false AND error.severity == 'high' RETURN error",
      "description": "Find unresolved errors with a 'high' severity.",
      "english_variations": {
        "layperson": "What are the big unsolved problems?",
        "mba": "List all unresolved, high-severity errors for priority tasking.",
        "developer": "Get unresolved errors where severity is 'high'.",
        "dba": "SELECT * FROM errors_and_failures WHERE resolved = FALSE AND severity = 'high'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 127,
      "category": "basic_filtering",
      "difficulty": "beginner",
      "aql": "FOR lesson IN lessons_learned SORT lesson.created_at DESC LIMIT 1 RETURN lesson",
      "description": "Get the most recently added lesson.",
      "english_variations": {
        "layperson": "What's the newest lesson we learned?",
        "mba": "Show the latest entry in the knowledge base.",
        "developer": "Get the last lesson added, sorted by creation date.",
        "dba": "SELECT * FROM lessons_learned ORDER BY created_at DESC LIMIT 1"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 128,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR s IN agent_sessions FILTER s.goal.complexity > 8 RETURN s",
      "description": "Find agent sessions that were assigned highly complex goals (complexity > 8).",
      "english_variations": {
        "layperson": "Which sessions handled the hardest tasks?",
        "mba": "Analyze sessions with high goal complexity to assess agent capabilities.",
        "developer": "Filter sessions where goal.complexity is greater than 8.",
        "dba": "SELECT * FROM agent_sessions WHERE goal.complexity > 8"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 129,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR insight IN agent_insights FILTER insight.agent_name == 'claude-code' SORT insight.timestamp DESC LIMIT 5 RETURN insight",
      "description": "Get the 5 most recent insights from the 'claude-code' agent.",
      "english_variations": {
        "layperson": "What has the Claude agent observed recently?",
        "mba": "Review the latest insights from the 'claude-code' agent.",
        "developer": "Get the last 5 insights from 'claude-code'.",
        "dba": "SELECT * FROM agent_insights WHERE agent_name = 'claude-code' ORDER BY timestamp DESC LIMIT 5"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 130,
      "category": "basic_filtering",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER log.metrics.cpu_usage > 0.9 RETURN log",
      "description": "Find log events where CPU usage exceeded 90%.",
      "english_variations": {
        "layperson": "When was the computer working too hard?",
        "mba": "Identify instances of high CPU utilization for performance and capacity planning.",
        "developer": "Find logs with CPU usage over 90%.",
        "dba": "SELECT * FROM log_events WHERE metrics.cpu_usage > 0.9"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 131,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures FILTER CONTAINS(LOWER(e.message), 'permission denied') RETURN e",
      "description": "Find error messages containing 'permission denied', case-insensitively.",
      "english_variations": {
        "layperson": "Are there any 'permission denied' errors?",
        "mba": "Search for access control issues impacting system resources.",
        "developer": "Case-insensitive search for 'permission denied' in error messages.",
        "dba": "SELECT * FROM errors_and_failures WHERE LOWER(message) LIKE '%permission denied%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 132,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR c IN code_artifacts FILTER c.file_path =~ '/(test|spec)/i' RETURN c.file_path",
      "description": "Find code artifacts that are likely test files using a case-insensitive regex.",
      "english_variations": {
        "layperson": "Show me all the test files.",
        "mba": "Identify code artifacts related to testing for quality assurance metrics.",
        "developer": "Use regex to find file paths containing 'test' or 'spec' directories, case-insensitively.",
        "dba": "SELECT file_path FROM code_artifacts WHERE file_path ~* '/(test|spec)/'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 133,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER STARTS_WITH(log.message, 'User login') RETURN log",
      "description": "Find all log messages that start with the phrase 'User login'.",
      "english_variations": {
        "layperson": "Show me the login logs.",
        "mba": "Audit user login events for security and activity tracking.",
        "developer": "Get logs where the message starts with 'User login'.",
        "dba": "SELECT * FROM log_events WHERE message LIKE 'User login%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 134,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions FILTER LIKE(t.command, '%--verbose%') RETURN t",
      "description": "Find tool commands that were run with a 'verbose' flag.",
      "english_variations": {
        "layperson": "Which commands were run in verbose mode?",
        "mba": "Analyze tool executions that used verbose flags for debugging patterns.",
        "developer": "Find commands containing '--verbose'.",
        "dba": "SELECT * FROM tool_executions WHERE command LIKE '%--verbose%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 135,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR session IN agent_sessions FILTER session.agent_name =~ 'gpt|claude' RETURN session",
      "description": "Find agent sessions for agents whose names contain 'gpt' or 'claude'.",
      "english_variations": {
        "layperson": "Show sessions from GPT or Claude agents.",
        "mba": "Compare sessions from different large language model providers.",
        "developer": "Use regex to find sessions from 'gpt' or 'claude' agents.",
        "dba": "SELECT * FROM agent_sessions WHERE agent_name ~ 'gpt|claude'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 136,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR l IN lessons_learned FILTER CONTAINS(l.lesson, 'caching') RETURN l",
      "description": "Find all lessons learned that mention 'caching'.",
      "english_variations": {
        "layperson": "What have we learned about caching?",
        "mba": "Collate all learned best practices related to caching.",
        "developer": "Search lessons for the keyword 'caching'.",
        "dba": "SELECT * FROM lessons_learned WHERE lesson LIKE '%caching%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 137,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR s IN solution_outcomes FILTER s.key_reason =~ '(?i)retry logic' RETURN s",
      "description": "Find solution outcomes where the reason involves 'retry logic', case-insensitively.",
      "english_variations": {
        "layperson": "Which solutions involved retrying things?",
        "mba": "Analyze the application of retry logic in solution designs.",
        "developer": "Case-insensitive regex search for 'retry logic' in key_reason.",
        "dba": "SELECT * FROM solution_outcomes WHERE key_reason ~* 'retry logic'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 138,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR g IN glossary_terms FILTER CONTAINS(g.definition, 'asynchronous') RETURN g.term",
      "description": "Find glossary terms whose definitions mention 'asynchronous'.",
      "english_variations": {
        "layperson": "Which terms are related to asynchronous operations?",
        "mba": "Identify all concepts in the glossary related to 'asynchronous' processing.",
        "developer": "Find terms where the definition contains 'asynchronous'.",
        "dba": "SELECT term FROM glossary_terms WHERE definition LIKE '%asynchronous%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 139,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR a IN code_artifacts FILTER ENDS_WITH(a.file_path, '.md') RETURN a.file_path",
      "description": "Find all markdown files.",
      "english_variations": {
        "layperson": "Show me all the documentation files.",
        "mba": "Inventory all markdown-based documentation artifacts.",
        "developer": "Get artifacts where the file_path ends with '.md'.",
        "dba": "SELECT file_path FROM code_artifacts WHERE file_path LIKE '%.md'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 140,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures FILTER e.error_type =~ 'Error$' RETURN e.error_type",
      "description": "Find all error types that end with the word 'Error' using regex.",
      "english_variations": {
        "layperson": "What are all the 'Error' types?",
        "mba": "List all conventionally named error types for categorization.",
        "developer": "Get error_types ending with 'Error' via regex.",
        "dba": "SELECT error_type FROM errors_and_failures WHERE error_type ~ 'Error$'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 141,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER CONTAINS(log.message, 'deprecated') RETURN log",
      "description": "Find log messages warning about deprecated features.",
      "english_variations": {
        "layperson": "Are we using any old features?",
        "mba": "Identify usage of deprecated functionality to plan for technical debt reduction.",
        "developer": "Search logs for the word 'deprecated'.",
        "dba": "SELECT * FROM log_events WHERE message LIKE '%deprecated%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 142,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR r IN research_cache FILTER LIKE(r.cache_key, '%_config') RETURN r",
      "description": "Find research cache entries whose keys end with '_config'.",
      "english_variations": {
        "layperson": "Is there any cached research about configurations?",
        "mba": "Locate cached research data related to system configurations.",
        "developer": "Find cache_keys ending with '_config'.",
        "dba": "SELECT * FROM research_cache WHERE cache_key LIKE '%\\_config'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 143,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures FILTER e.stack_trace != null AND e.stack_trace =~ 'File \"/app/src/.*\\.py\"' RETURN e",
      "description": "Find stack traces originating from a specific source directory '/app/src/'.",
      "english_variations": {
        "layperson": "Which errors came from our main application code?",
        "mba": "Isolate errors originating from the core application source to focus debugging efforts.",
        "developer": "Regex search in stack traces for files in '/app/src/'.",
        "dba": "SELECT * FROM errors_and_failures WHERE stack_trace REGEXP 'File \"/app/src/.*\\.py\"'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 144,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR i IN agent_insights FILTER CONTAINS(i.insight_text, 'performance bottleneck') RETURN i",
      "description": "Find agent insights that specifically mention a 'performance bottleneck'.",
      "english_variations": {
        "layperson": "Did the agents find any performance problems?",
        "mba": "Surface agent-identified performance bottlenecks for optimization initiatives.",
        "developer": "Search insights for the phrase 'performance bottleneck'.",
        "dba": "SELECT * FROM agent_insights WHERE insight_text LIKE '%performance bottleneck%'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 145,
      "category": "string_search",
      "difficulty": "beginner",
      "aql": "FOR log IN log_events FILTER CONTAINS(log.message, 'session_002') RETURN log",
      "description": "Find log messages that mention a specific session ID.",
      "english_variations": {
        "layperson": "Find any logs that talk about session_002.",
        "mba": "Cross-reference log messages for mentions of a specific session ID.",
        "developer": "Search log messages for 'session_002'.",
        "dba": "SELECT * FROM log_events WHERE message LIKE '%session_002%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 146,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR g IN glossary_terms FILTER g.term =~ '^\\w{1,4}$' RETURN g",
      "description": "Find glossary terms that are short (1 to 4 letters, likely acronyms).",
      "english_variations": {
        "layperson": "Show me the short, acronym-like terms.",
        "mba": "List all defined acronyms (1-4 characters) for a terminology review.",
        "developer": "Regex for terms that are 1-4 word characters long.",
        "dba": "SELECT * FROM glossary_terms WHERE term REGEXP '^\\\\w{1,4}$'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 147,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR s IN solution_outcomes FILTER CONTAINS(s.tags, 'experimental') RETURN s",
      "description": "Find solutions that are tagged as 'experimental'.",
      "english_variations": {
        "layperson": "Which solutions were just experiments?",
        "mba": "Review outcomes of experimental solutions to evaluate innovative approaches.",
        "developer": "Filter solutions where the tags array contains 'experimental'.",
        "dba": "SELECT * FROM solution_outcomes WHERE 'experimental' = ANY(tags)"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 148,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions FILTER CONTAINS(LOWER(t.command), 'rm -rf') RETURN t",
      "description": "Find potentially dangerous 'rm -rf' commands.",
      "english_variations": {
        "layperson": "Did the agent try to delete everything?",
        "mba": "Audit for the use of high-risk, destructive commands for security oversight.",
        "developer": "Search for 'rm -rf' in tool commands, case-insensitively.",
        "dba": "SELECT * FROM tool_executions WHERE LOWER(command) LIKE '%rm -rf%'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 149,
      "category": "string_search",
      "difficulty": "beginner",
      "aql": "FOR s IN agent_sessions FILTER s.status == 'failed' AND CONTAINS(s.summary, 'compilation') RETURN s",
      "description": "Find failed sessions where the summary mentions 'compilation'.",
      "english_variations": {
        "layperson": "Which sessions failed because of compilation problems?",
        "mba": "Isolate session failures related to code compilation issues.",
        "developer": "Find failed sessions with 'compilation' in the summary.",
        "dba": "SELECT * FROM agent_sessions WHERE status = 'failed' AND summary LIKE '%compilation%'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 150,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR log IN log_events FILTER log.message =~ 'took \\\\d{4,} ms' RETURN log",
      "description": "Find log messages indicating long-running operations (4+ digit milliseconds).",
      "english_variations": {
        "layperson": "Which logs talk about slow things happening?",
        "mba": "Identify logs reporting operations exceeding a 1-second threshold for performance analysis.",
        "developer": "Regex search for logs reporting durations of 1000ms or more.",
        "dba": "SELECT * FROM log_events WHERE message REGEXP 'took \\\\d{4,} ms'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 151,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures FILTER LIKE(e.error_type, 'Database%') RETURN e",
      "description": "Find all error types that start with 'Database'.",
      "english_variations": {
        "layperson": "Show me all the database-related errors.",
        "mba": "Collate all error types related to database operations.",
        "developer": "Find error_types starting with 'Database'.",
        "dba": "SELECT * FROM errors_and_failures WHERE error_type LIKE 'Database%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 152,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR artifact IN code_artifacts FILTER CONTAINS(artifact.comments, 'TODO') RETURN artifact",
      "description": "Find code artifacts containing 'TODO' comments.",
      "english_variations": {
        "layperson": "Which files have 'TODO' notes in them?",
        "mba": "Identify outstanding tasks embedded in code comments to assess technical debt.",
        "developer": "Find artifacts with 'TODO' in their comments.",
        "dba": "SELECT * FROM code_artifacts WHERE comments LIKE '%TODO%'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 153,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR lesson IN lessons_learned FILTER CONTAINS(lesson.lesson, 'security') OR CONTAINS(lesson.category, 'security') RETURN lesson",
      "description": "Find all lessons related to security, either in the text or category.",
      "english_variations": {
        "layperson": "What have we learned about security?",
        "mba": "Aggregate all security-related lessons from the knowledge base.",
        "developer": "Find lessons mentioning 'security' or in the 'security' category.",
        "dba": "SELECT * FROM lessons_learned WHERE lesson LIKE '%security%' OR category = 'security'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 154,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR log IN log_events FILTER log.message =~ '(?i)invalid.*credentials' RETURN log",
      "description": "Find logs about 'invalid credentials' using a case-insensitive regex.",
      "english_variations": {
        "layperson": "Any logs about wrong passwords?",
        "mba": "Search for authentication failures due to invalid credentials.",
        "developer": "Regex search for 'invalid' followed by 'credentials', case-insensitively.",
        "dba": "SELECT * FROM log_events WHERE message ~* 'invalid.*credentials'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 155,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR tool IN tool_executions FILTER CONTAINS(tool.command, '> /dev/null') RETURN tool",
      "description": "Find tool commands that redirect output to /dev/null, potentially hiding errors.",
      "english_variations": {
        "layperson": "Which commands might be hiding their output?",
        "mba": "Audit for tool commands that suppress output, which could obscure operational issues.",
        "developer": "Find commands redirecting stdout to /dev/null.",
        "dba": "SELECT * FROM tool_executions WHERE command LIKE '%> /dev/null%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 156,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR artifact IN code_artifacts FILTER LIKE(artifact.file_path, '%.test.js') OR LIKE(artifact.file_path, '%.spec.js') RETURN artifact.file_path",
      "description": "Find JavaScript test files by common naming conventions.",
      "english_variations": {
        "layperson": "Show me the javascript test files.",
        "mba": "Inventory JavaScript test suites for code coverage analysis.",
        "developer": "Find files ending in '.test.js' or '.spec.js'.",
        "dba": "SELECT file_path FROM code_artifacts WHERE file_path LIKE '%.test.js' OR file_path LIKE '%.spec.js'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 157,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR log IN log_events FILTER log.message =~ '([0-9]{1,3}\\\\.){3}[0-9]{1,3}' RETURN log.message",
      "description": "Find log messages that contain an IPv4 address.",
      "english_variations": {
        "layperson": "Are there any IP addresses in the logs?",
        "mba": "Identify log entries containing IP addresses for network and security analysis.",
        "developer": "Use regex to find messages with an IPv4 address pattern.",
        "dba": "SELECT message FROM log_events WHERE message REGEXP '([0-9]{1,3}\\\\.){3}[0-9]{1,3}'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 158,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR error IN errors_and_failures FILTER CONTAINS(error.resolution, 'restarted') RETURN error",
      "description": "Find errors that were resolved by restarting something.",
      "english_variations": {
        "layperson": "Which problems were fixed by turning it off and on again?",
        "mba": "Analyze how many issues are resolved by restarts to identify stability problems.",
        "developer": "Find errors where the resolution text contains 'restarted'.",
        "dba": "SELECT * FROM errors_and_failures WHERE resolution LIKE '%restarted%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 159,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR g IN glossary_terms FILTER STARTS_WITH(g.term, 'TLA') RETURN g",
      "description": "Find glossary terms that seem to be about Three Letter Acronyms (TLAs).",
      "english_variations": {
        "layperson": "Do we have any TLAs defined?",
        "mba": "List all glossary terms prefixed with 'TLA'.",
        "developer": "Get terms starting with 'TLA'.",
        "dba": "SELECT * FROM glossary_terms WHERE term LIKE 'TLA%'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 160,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR session IN agent_sessions FILTER CONTAINS(session.summary, 'failed to parse') RETURN session",
      "description": "Find sessions that failed due to parsing issues.",
      "english_variations": {
        "layperson": "Which sessions had trouble understanding data?",
        "mba": "Isolate session failures caused by data parsing errors.",
        "developer": "Find sessions where the summary contains 'failed to parse'.",
        "dba": "SELECT * FROM agent_sessions WHERE summary LIKE '%failed to parse%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 161,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR s IN solution_outcomes FILTER CONTAINS(s.key_reason, 'rollback') RETURN s",
      "description": "Find solution outcomes that involved a rollback.",
      "english_variations": {
        "layperson": "Which solutions involved going back to an old version?",
        "mba": "Analyze instances where a rollback was the key component of a solution.",
        "developer": "Find solutions where 'rollback' is in the key_reason.",
        "dba": "SELECT * FROM solution_outcomes WHERE key_reason LIKE '%rollback%'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 162,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures FILTER e.stack_trace != null AND CONTAINS(e.stack_trace, 'concurrent.futures') RETURN e",
      "description": "Find errors that occurred within Python's concurrency library.",
      "english_variations": {
        "layperson": "Which errors are related to running things at the same time?",
        "mba": "Identify concurrency-related failures for stability analysis.",
        "developer": "Find stack traces that mention 'concurrent.futures'.",
        "dba": "SELECT * FROM errors_and_failures WHERE stack_trace LIKE '%concurrent.futures%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 163,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER CONTAINS(log.message, 'rate limit') RETURN log",
      "description": "Find log messages related to API rate limiting.",
      "english_variations": {
        "layperson": "Were we ever blocked for making too many requests?",
        "mba": "Identify instances of API rate limiting to manage external service usage.",
        "developer": "Search logs for 'rate limit'.",
        "dba": "SELECT * FROM log_events WHERE message LIKE '%rate limit%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 164,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR artifact IN code_artifacts FILTER LIKE(artifact.file_path, '%/config.%.json') RETURN artifact",
      "description": "Find all JSON configuration files named 'config'.",
      "english_variations": {
        "layperson": "Show me all the JSON config files.",
        "mba": "Inventory all JSON-based configuration files across the project.",
        "developer": "Find files matching the pattern '%/config.%.json'.",
        "dba": "SELECT * FROM code_artifacts WHERE file_path LIKE '%/config.%.json'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 165,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR lesson IN lessons_learned FILTER CONTAINS(lesson.lesson, 'environment variable') RETURN lesson",
      "description": "Find lessons learned about using environment variables.",
      "english_variations": {
        "layperson": "What have we learned about environment variables?",
        "mba": "Review best practices concerning the use of environment variables.",
        "developer": "Find lessons that mention 'environment variable'.",
        "dba": "SELECT * FROM lessons_learned WHERE lesson LIKE '%environment variable%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 166,
      "category": "string_search",
      "difficulty": "advanced",
      "aql": "FOR tool IN tool_executions FILTER tool.command =~ '\\\\s-p \\\\w+' RETURN tool",
      "description": "Find tool commands that use a '-p' flag followed by a password-like string.",
      "english_variations": {
        "layperson": "Are we putting passwords directly in commands?",
        "mba": "Audit for insecure command-line patterns, such as plaintext passwords.",
        "developer": "Regex search for commands with a '-p <word>' pattern.",
        "dba": "SELECT * FROM tool_executions WHERE command REGEXP '\\\\s-p \\\\w+'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 167,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR error IN errors_and_failures FILTER CONTAINS(LOWER(error.message), 'not found') RETURN error",
      "description": "Find all error messages that contain 'not found', case-insensitively.",
      "english_variations": {
        "layperson": "Show me all 'not found' errors.",
        "mba": "Analyze all 'not found' type errors to identify resource availability issues.",
        "developer": "Case-insensitive search for 'not found' in error messages.",
        "dba": "SELECT * FROM errors_and_failures WHERE LOWER(message) LIKE '%not found%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 168,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR session IN agent_sessions FILTER LIKE(session.metadata.model_name, '%-turbo') RETURN session",
      "description": "Find sessions that used a 'turbo' version of a model.",
      "english_variations": {
        "layperson": "Which sessions used a 'turbo' model?",
        "mba": "Analyze the usage and performance of 'turbo' class models.",
        "developer": "Find sessions where metadata.model_name ends with '-turbo'.",
        "dba": "SELECT * FROM agent_sessions WHERE metadata.model_name LIKE '%-turbo'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 169,
      "category": "string_search",
      "difficulty": "beginner",
      "aql": "FOR g IN glossary_terms FILTER CONTAINS(g.term, 'SQL') RETURN g",
      "description": "Find all glossary terms that contain 'SQL'.",
      "english_variations": {
        "layperson": "Do we have any SQL-related terms?",
        "mba": "List all glossary entries related to SQL.",
        "developer": "Find glossary terms containing 'SQL'.",
        "dba": "SELECT * FROM glossary_terms WHERE term LIKE '%SQL%'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 170,
      "category": "string_search",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER log.level == 'INFO' AND CONTAINS(log.message, 'successfully') RETURN log",
      "description": "Find informational logs that indicate a successful operation.",
      "english_variations": {
        "layperson": "Show me the success messages.",
        "mba": "Track key successful operation milestones from the event logs.",
        "developer": "Find INFO logs with the word 'successfully'.",
        "dba": "SELECT * FROM log_events WHERE level = 'INFO' AND message LIKE '%successfully%'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 171,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR log IN log_events COLLECT hour = DATE_HOUR(log.timestamp) WITH COUNT INTO count SORT hour RETURN {hour: hour, count: count}",
      "description": "Count log events by the hour of the day to find peak activity times.",
      "english_variations": {
        "layperson": "When is the system busiest during the day?",
        "mba": "Analyze hourly system activity patterns to identify peak usage times for resource allocation.",
        "developer": "Group logs by hour and count them.",
        "dba": "SELECT HOUR(timestamp) as hour, COUNT(*) as count FROM log_events GROUP BY hour ORDER BY hour"
      },
      "expected_result_type": "aggregated",
      "visualization": "heatmap"
    },
    {
      "id": 172,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR s IN agent_sessions FILTER s.end_time < s.start_time RETURN s",
      "description": "Find sessions with inconsistent start/end times (end time is before start time).",
      "english_variations": {
        "layperson": "Are there any sessions with weird timestamps?",
        "mba": "Identify data integrity issues in session time tracking.",
        "developer": "Find sessions where end_time is before start_time.",
        "dba": "SELECT * FROM agent_sessions WHERE end_time < start_time"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 173,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions FILTER t.start_time >= DATE_SUBTRACT(DATE_NOW(), 7, 'day') AND t.status == 'failed' RETURN t",
      "description": "Find all failed tool executions from the last 7 days.",
      "english_variations": {
        "layperson": "Which tools failed this past week?",
        "mba": "Review all tool failures over the last week to identify recurring issues.",
        "developer": "Get failed tool runs from the last 7 days.",
        "dba": "SELECT * FROM tool_executions WHERE start_time >= NOW() - INTERVAL 7 DAY AND status = 'failed'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 174,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures COLLECT date = DATE_TRUNC(e.timestamp, 'day') WITH COUNT INTO errorCount SORT date RETURN { date: DATE_FORMAT(date, '%YYYY-%mm-%dd'), errorCount }",
      "description": "Count the number of errors per day.",
      "english_variations": {
        "layperson": "How many errors happen each day?",
        "mba": "Track the daily error rate trend to measure system stability over time.",
        "developer": "Group errors by day and count them.",
        "dba": "SELECT DATE(timestamp) as date, COUNT(*) as errorCount FROM errors_and_failures GROUP BY DATE(timestamp) ORDER BY date"
      },
      "expected_result_type": "aggregated",
      "visualization": "line_chart"
    },
    {
      "id": 175,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR s IN solution_outcomes FILTER s.applied_at >= DATE_SUBTRACT(DATE_NOW(), 1, 'month') RETURN s",
      "description": "Get all solution outcomes that were applied in the last month.",
      "english_variations": {
        "layperson": "What solutions have we tried recently?",
        "mba": "Review all solutions implemented over the past month.",
        "developer": "Get solution_outcomes from the last month.",
        "dba": "SELECT * FROM solution_outcomes WHERE applied_at >= NOW() - INTERVAL 1 MONTH"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 176,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER DATE_DAYOFWEEK(log.timestamp) IN [0, 6] RETURN log",
      "description": "Find all log events that occurred on a weekend (Sunday or Saturday).",
      "english_variations": {
        "layperson": "Did anything happen over the weekend?",
        "mba": "Analyze system activity during off-peak weekend hours.",
        "developer": "Get logs where day of the week is 0 or 6.",
        "dba": "SELECT * FROM log_events WHERE DAYOFWEEK(timestamp) IN (1, 7)"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 177,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "LET start_time = '2025-06-20T10:00:00.000Z' LET end_time = '2025-06-20T11:00:00.000Z' FOR tool IN tool_executions FILTER tool.start_time >= start_time AND tool.start_time <= end_time RETURN tool",
      "description": "Find all tool executions within a specific one-hour window.",
      "english_variations": {
        "layperson": "What tools were used between 10 and 11 AM on June 20th?",
        "mba": "Audit tool usage during a specific time window for incident analysis.",
        "developer": "Get tools executed between two specific timestamps.",
        "dba": "SELECT * FROM tool_executions WHERE start_time BETWEEN '2025-06-20T10:00:00Z' AND '2025-06-20T11:00:00Z'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 178,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR c IN code_artifacts FILTER c.timestamp < DATE_SUBTRACT(DATE_NOW(), 6, 'month') RETURN c",
      "description": "Find code artifacts that haven't been modified in over 6 months.",
      "english_variations": {
        "layperson": "Show me the old, untouched files.",
        "mba": "Identify stale code artifacts for potential archival or refactoring.",
        "developer": "Find artifacts with a timestamp older than 6 months.",
        "dba": "SELECT * FROM code_artifacts WHERE timestamp < NOW() - INTERVAL 6 MONTH"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 179,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR session IN agent_sessions LET startHour = DATE_HOUR(session.start_time) FILTER startHour >= 0 AND startHour <= 6 RETURN session",
      "description": "Find agent sessions that started during overnight hours (midnight to 6 AM).",
      "english_variations": {
        "layperson": "Did any agents work overnight?",
        "mba": "Analyze overnight agent activity for unattended operations.",
        "developer": "Find sessions where the start hour is between 0 and 6.",
        "dba": "SELECT * FROM agent_sessions WHERE HOUR(start_time) BETWEEN 0 AND 6"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 180,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR g IN glossary_terms FILTER g.created_at >= DATE_FORMAT(DATE_NOW(), '%Y-01-01') RETURN g",
      "description": "Find all glossary terms added this year.",
      "english_variations": {
        "layperson": "What new terms were added this year?",
        "mba": "Review all new knowledge base entries for the current year.",
        "developer": "Get glossary terms created since the beginning of the current year.",
        "dba": "SELECT * FROM glossary_terms WHERE YEAR(created_at) = YEAR(CURDATE())"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 181,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR t IN tool_executions RETURN DATE_DIFF(t.end_time, t.start_time, 'seconds')",
      "description": "Calculate the duration of each tool execution in seconds.",
      "english_variations": {
        "layperson": "How many seconds did each tool run for?",
        "mba": "Calculate tool execution durations for performance metric analysis.",
        "developer": "Get the time difference in seconds between end_time and start_time for each tool.",
        "dba": "SELECT DATEDIFF(second, start_time, end_time) FROM tool_executions"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 182,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER LIKE(log.timestamp, '2025-07-04%') RETURN log",
      "description": "Find all log events that occurred on a specific date.",
      "english_variations": {
        "layperson": "What happened on July 4th, 2025?",
        "mba": "Retrieve all log data for a specific date for an incident report.",
        "developer": "Get logs with a timestamp prefix of '2025-07-04'.",
        "dba": "SELECT * FROM log_events WHERE DATE(timestamp) = '2025-07-04'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 183,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures COLLECT errorType = e.error_type, year = DATE_YEAR(e.timestamp) WITH COUNT INTO count RETURN {errorType, year, count}",
      "description": "Count error types per year.",
      "english_variations": {
        "layperson": "How did errors change from year to year?",
        "mba": "Analyze year-over-year error trends by type.",
        "developer": "Group errors by type and year, then count them.",
        "dba": "SELECT error_type, YEAR(timestamp), COUNT(*) FROM errors_and_failures GROUP BY error_type, YEAR(timestamp)"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 184,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER DATE_IN_RANGE(log.timestamp, '2025-01-01', '2025-03-31', true, true) RETURN log",
      "description": "Find all log events from the first quarter of 2025.",
      "english_variations": {
        "layperson": "What happened in the first quarter of 2025?",
        "mba": "Retrieve all log data for Q1 2025 for a quarterly review.",
        "developer": "Get logs within the date range for Q1 2025.",
        "dba": "SELECT * FROM log_events WHERE timestamp BETWEEN '2025-01-01' AND '2025-03-31'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 185,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR session IN agent_sessions FILTER DATE_DIFF(DATE_NOW(), session.start_time, 'hours') > 24 AND session.status == 'running' RETURN session",
      "description": "Find 'running' agent sessions that have been active for more than 24 hours.",
      "english_variations": {
        "layperson": "Are any agents stuck on a task?",
        "mba": "Identify potentially stalled agent sessions for operational intervention.",
        "developer": "Find running sessions that started more than 24 hours ago.",
        "dba": "SELECT * FROM agent_sessions WHERE status = 'running' AND start_time < NOW() - INTERVAL 24 HOUR"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 186,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR t1 IN tool_executions FOR t2 IN tool_executions FILTER t1.session_id == t2.session_id AND t1.start_time < t2.start_time AND DATE_DIFF(t2.start_time, t1.end_time, 'seconds') < 5 RETURN { first_tool: t1.tool_name, second_tool: t2.tool_name }",
      "description": "Find pairs of tools that are executed in quick succession (less than 5 seconds apart) within the same session.",
      "english_variations": {
        "layperson": "Which tools are often used back-to-back?",
        "mba": "Analyze tool chaining patterns to understand user workflows.",
        "developer": "Find tool pairs with less than a 5-second gap between them in a session.",
        "dba": "Self-join tool_executions to find sequential tool usage patterns."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 187,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR e in errors_and_failures SORT e.timestamp ASC LIMIT 1 RETURN e.timestamp",
      "description": "Find the timestamp of the very first error recorded.",
      "english_variations": {
        "layperson": "When did the first error happen?",
        "mba": "Determine the inception date of the first recorded system error.",
        "developer": "Get the timestamp of the earliest error.",
        "dba": "SELECT MIN(timestamp) FROM errors_and_failures"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 188,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER DATE_LEAPYEAR(log.timestamp) RETURN log",
      "description": "Find log events that occurred in a leap year.",
      "english_variations": {
        "layperson": "What happened during leap years?",
        "mba": "Isolate data from leap years for specific temporal analysis.",
        "developer": "Get logs from leap years.",
        "dba": "SELECT * FROM log_events WHERE IS_LEAP_YEAR(timestamp) = TRUE"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 189,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures COLLECT dayOfWeek = DATE_DAYOFWEEK(e.timestamp), hour = DATE_HOUR(e.timestamp) WITH COUNT INTO count RETURN { day: dayOfWeek, hour: hour, count: count }",
      "description": "Create a heatmap of errors by day of the week and hour.",
      "english_variations": {
        "layperson": "When do errors usually happen during the week?",
        "mba": "Visualize error frequency by day and hour to identify high-risk periods.",
        "developer": "Generate a count of errors grouped by day-of-week and hour.",
        "dba": "SELECT DAYOFWEEK(timestamp) as day, HOUR(timestamp) as hour, COUNT(*) FROM errors_and_failures GROUP BY day, hour"
      },
      "expected_result_type": "aggregated",
      "visualization": "heatmap"
    },
    {
      "id": 190,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR a IN agent_sessions FILTER DATE_MONTH(a.start_time) == 12 RETURN a",
      "description": "Find all agent sessions that started in December.",
      "english_variations": {
        "layperson": "What work was done in December?",
        "mba": "Analyze agent activity during the month of December.",
        "developer": "Get sessions that started in the 12th month.",
        "dba": "SELECT * FROM agent_sessions WHERE MONTH(start_time) = 12"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 191,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR e1 IN errors_and_failures LET t_res = (FOR e2 IN errors_and_failures FILTER e2.error_type == e1.error_type AND e2.resolved == true RETURN e2.timestamp)[0] FILTER t_res != null RETURN { error_type: e1.error_type, time_to_resolve: DATE_DIFF(t_res, e1.timestamp, 'hours') }",
      "description": "Estimate the time-to-resolve for different error types.",
      "english_variations": {
        "layperson": "How long does it take to fix different kinds of errors?",
        "mba": "Calculate the average Mean Time to Resolution (MTTR) for various error categories.",
        "developer": "Estimate time-to-resolve by finding the gap between first occurrence and first resolution.",
        "dba": "Complex query to calculate time difference between unresolved and resolved errors of the same type."
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 192,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR l IN lessons_learned FILTER l.created_at >= DATE_TRUNC(DATE_NOW(), 'week') RETURN l",
      "description": "Find all lessons that were learned this week.",
      "english_variations": {
        "layperson": "What did we learn this week?",
        "mba": "Review the current week's additions to the knowledge base.",
        "developer": "Get lessons created since the start of the current week.",
        "dba": "SELECT * FROM lessons_learned WHERE created_at >= DATE_TRUNC('week', NOW())"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 193,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR r IN research_cache FILTER r.timestamp < DATE_SUBTRACT(DATE_NOW(), 30, 'day') RETURN r.cache_key",
      "description": "Find research cache keys for items older than 30 days.",
      "english_variations": {
        "layperson": "What's in our old research cache?",
        "mba": "Identify stale items in the research cache for potential pruning.",
        "developer": "Get cache keys for items older than 30 days.",
        "dba": "SELECT cache_key FROM research_cache WHERE timestamp < NOW() - INTERVAL 30 DAY"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 194,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR log IN log_events FILTER log.level == 'ERROR' COLLECT date = DATE_TRUNC(log.timestamp, 'day') INTO group LET first_error_time = MIN(group[*].log.timestamp) RETURN { date, first_error_time }",
      "description": "For each day, find the time of the first error.",
      "english_variations": {
        "layperson": "When did things first go wrong each day?",
        "mba": "Track the time of the first daily error to analyze incident start patterns.",
        "developer": "For each day, find the timestamp of the first error log.",
        "dba": "SELECT DATE(timestamp), MIN(timestamp) FROM log_events WHERE level = 'ERROR' GROUP BY DATE(timestamp)"
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 195,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR session IN agent_sessions FILTER DATE_QUARTER(session.start_time) == 2 RETURN session",
      "description": "Find all agent sessions that started in the second quarter of any year.",
      "english_variations": {
        "layperson": "What happened in the second quarter?",
        "mba": "Analyze agent activity across all Q2 periods.",
        "developer": "Get sessions that started in Q2.",
        "dba": "SELECT * FROM agent_sessions WHERE QUARTER(start_time) = 2"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 196,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "LET last_error_time = MAX(FOR e IN errors_and_failures RETURN e.timestamp) RETURN DATE_DIFF(DATE_NOW(), last_error_time, 'days')",
      "description": "Calculate the number of days since the last recorded error.",
      "english_variations": {
        "layperson": "How long has it been since the last error?",
        "mba": "Report the 'days without a major incident' metric.",
        "developer": "Get the number of days since the last error.",
        "dba": "SELECT DATEDIFF(day, MAX(timestamp), NOW()) FROM errors_and_failures"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 197,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR i IN agent_insights FILTER i.timestamp >= DATE_SUBTRACT(DATE_NOW(), 60, 'minute') RETURN i",
      "description": "Get all agent insights generated in the last hour.",
      "english_variations": {
        "layperson": "What have the agents figured out in the last hour?",
        "mba": "Review real-time agent insights from the past hour.",
        "developer": "Get insights from the last 60 minutes.",
        "dba": "SELECT * FROM agent_insights WHERE timestamp >= NOW() - INTERVAL 60 MINUTE"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 198,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR e IN log_events FILTER e.timestamp >= '2025-06-21T17:00:00Z' AND e.timestamp < '2025-06-21T18:00:00Z' RETURN e",
      "description": "Retrieve all log events from a specific hour on a specific day.",
      "english_variations": {
        "layperson": "What happened between 5 PM and 6 PM yesterday?",
        "mba": "Audit log activity for a specific hour for an incident investigation.",
        "developer": "Get logs for the 17:00 hour on June 21, 2025.",
        "dba": "SELECT * FROM log_events WHERE timestamp >= '2025-06-21 17:00:00' AND timestamp < '2025-06-21 18:00:00'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 199,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR s IN agent_sessions FILTER s.status == 'completed' COLLECT agent = s.agent_name INTO g RETURN { agent, avg_duration: AVERAGE(g[*].s.duration_ms) }",
      "description": "Calculate the average duration for completed sessions, grouped by agent.",
      "english_variations": {
        "layperson": "On average, how long does each agent take to finish a task?",
        "mba": "Compare the average task completion time across different agents to measure efficiency.",
        "developer": "Get the average duration for completed sessions per agent.",
        "dba": "SELECT agent_name, AVG(duration_ms) FROM agent_sessions WHERE status = 'completed' GROUP BY agent_name"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 200,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures FILTER e.resolved_at != null RETURN DATE_DIFF(e.resolved_at, e.timestamp, 'minutes')",
      "description": "For resolved errors, calculate how many minutes it took to resolve them.",
      "english_variations": {
        "layperson": "How long did it take to fix each problem?",
        "mba": "Calculate the Time to Resolution (TTR) for individual incidents.",
        "developer": "Get the difference in minutes between resolved_at and timestamp for errors.",
        "dba": "SELECT DATEDIFF(minute, timestamp, resolved_at) FROM errors_and_failures WHERE resolved_at IS NOT NULL"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 201,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions FILTER DATE_DAYOFYEAR(t.start_time) == 1 RETURN t",
      "description": "Find tool executions that happened on the first day of the year.",
      "english_variations": {
        "layperson": "What happened on New Year's Day?",
        "mba": "Analyze system activity on January 1st.",
        "developer": "Get tools run on the first day of the year.",
        "dba": "SELECT * FROM tool_executions WHERE DAYOFYEAR(start_time) = 1"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 202,
      "category": "time_based",
      "difficulty": "expert",
      "aql": "FOR t IN tool_executions COLLECT date = DATE_TRUNC(t.start_time, 'day') INTO group LET durations = group[*].t.duration_ms RETURN { date: DATE_FORMAT(date, 'YYYY-MM-DD'), p95_duration: PERCENTILE(durations, 95) }",
      "description": "Calculate the 95th percentile of tool duration per day.",
      "english_variations": {
        "layperson": "What was the typical 'slow' tool runtime each day?",
        "mba": "Track the p95 tool execution duration as a key performance indicator for system responsiveness.",
        "developer": "Calculate the daily 95th percentile for tool duration.",
        "dba": "SELECT DATE(start_time), PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) FROM tool_executions GROUP BY DATE(start_time)"
      },
      "expected_result_type": "aggregated",
      "visualization": "line_chart"
    },
    {
      "id": 203,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR s IN agent_sessions FILTER s.start_time >= '2025-01-01T00:00:00Z' AND s.start_time < '2026-01-01T00:00:00Z' RETURN s",
      "description": "Get all agent sessions that started in the year 2025.",
      "english_variations": {
        "layperson": "Show me all the work done in 2025.",
        "mba": "Retrieve all agent session data for the 2025 fiscal year.",
        "developer": "Filter sessions with a start_time in the year 2025.",
        "dba": "SELECT * FROM agent_sessions WHERE YEAR(start_time) = 2025"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 204,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR error IN errors_and_failures FILTER DATE_DIFF(DATE_NOW(), error.timestamp, 'minutes') < 10 RETURN error",
      "description": "Find all errors that occurred in the last 10 minutes.",
      "english_variations": {
        "layperson": "What has gone wrong very recently?",
        "mba": "Monitor for new errors in near real-time (10-minute window).",
        "developer": "Get errors from the last 10 minutes.",
        "dba": "SELECT * FROM errors_and_failures WHERE timestamp >= NOW() - INTERVAL 10 MINUTE"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 205,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "LET week_ago = DATE_SUBTRACT(DATE_NOW(), 7, 'day') LET errors_this_week = LENGTH(FOR e IN errors_and_failures FILTER e.timestamp >= week_ago RETURN 1) LET errors_last_week = LENGTH(FOR e IN errors_and_failures FILTER e.timestamp < week_ago AND e.timestamp >= DATE_SUBTRACT(week_ago, 7, 'day') RETURN 1) RETURN { errors_this_week, errors_last_week }",
      "description": "Compare the number of errors this week to the number of errors last week.",
      "english_variations": {
        "layperson": "Are we getting more or fewer errors this week compared to last week?",
        "mba": "Perform a week-over-week comparison of error counts to track stability trends.",
        "developer": "Compare error counts for the last 7 days vs the 7 days prior.",
        "dba": "Two separate COUNT queries with different time windows to compare weekly errors."
      },
      "expected_result_type": "aggregated",
      "visualization": "text"
    },
    {
      "id": 206,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR a IN code_artifacts FILTER DATE_FORMAT(a.timestamp, '%H') == '03' RETURN a",
      "description": "Find code artifacts that were modified at 3 AM.",
      "english_variations": {
        "layperson": "Who is changing code in the middle of the night?",
        "mba": "Audit code modifications during off-hours.",
        "developer": "Get artifacts modified during the 3 AM hour.",
        "dba": "SELECT * FROM code_artifacts WHERE HOUR(timestamp) = 3"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 207,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR s IN solution_outcomes SORT s.applied_at DESC LIMIT 5 RETURN s",
      "description": "Get the 5 most recently applied solution outcomes.",
      "english_variations": {
        "layperson": "What are the last 5 solutions we tried?",
        "mba": "Review the five most recently implemented solutions.",
        "developer": "Get the top 5 solutions ordered by applied_at descending.",
        "dba": "SELECT * FROM solution_outcomes ORDER BY applied_at DESC LIMIT 5"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 208,
      "category": "time_based",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures RETURN { error_id: e._key, is_recent: e.timestamp > DATE_SUBTRACT(DATE_NOW(), 1, 'day') }",
      "description": "For each error, determine if it occurred in the last 24 hours.",
      "english_variations": {
        "layperson": "Which of these errors are recent?",
        "mba": "Tag errors based on whether they occurred within the last 24 hours.",
        "developer": "For each error, return a boolean indicating if it's from the last 24 hours.",
        "dba": "SELECT _key, (timestamp > NOW() - INTERVAL 1 DAY) as is_recent FROM errors_and_failures"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 209,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions FILTER t.start_time > '2026-01-01T00:00:00Z' RETURN t",
      "description": "Find tool executions with a start time in the future (likely bad data).",
      "english_variations": {
        "layperson": "Are there any tool runs from the future?",
        "mba": "Perform a data integrity check for future-dated tool execution records.",
        "developer": "Find tools with a start_time after Jan 1, 2026.",
        "dba": "SELECT * FROM tool_executions WHERE start_time > '2026-01-01'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 210,
      "category": "time_based",
      "difficulty": "intermediate",
      "aql": "FOR l in log_events SORT l.timestamp DESC LIMIT 1 RETURN l.timestamp",
      "description": "Get the timestamp of the most recent log event.",
      "english_variations": {
        "layperson": "When was the last time anything happened?",
        "mba": "Determine the time of the last recorded system event.",
        "developer": "Get the timestamp of the very last log.",
        "dba": "SELECT MAX(timestamp) FROM log_events"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 211,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions COLLECT tool = t.tool_name INTO group RETURN { tool: tool, avg_duration: AVERAGE(group[*].t.duration_ms) }",
      "description": "Calculate the average execution duration for each tool.",
      "english_variations": {
        "layperson": "Which tools are the slowest on average?",
        "mba": "Analyze average tool performance to identify optimization opportunities.",
        "developer": "Get the average duration_ms for each tool, grouped by tool_name.",
        "dba": "SELECT tool_name, AVG(duration_ms) as avg_duration FROM tool_executions GROUP BY tool_name"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 212,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "LET successful_solutions = LENGTH(FOR s IN solution_outcomes FILTER s.outcome == 'success' RETURN 1) LET total_solutions = LENGTH(solution_outcomes) RETURN (successful_solutions / total_solutions) * 100",
      "description": "Calculate the overall solution success rate percentage.",
      "english_variations": {
        "layperson": "What percentage of our solutions work?",
        "mba": "Determine the overall solution success rate KPI.",
        "developer": "Calculate the percentage of solutions with 'success' outcome.",
        "dba": "SELECT (CAST(SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)) * 100 FROM solution_outcomes"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 213,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR a IN agent_sessions COLLECT agent = a.agent_name WITH COUNT INTO session_count SORT session_count DESC RETURN { agent: agent, session_count: session_count }",
      "description": "Count the number of sessions for each agent.",
      "english_variations": {
        "layperson": "Which agent has done the most work sessions?",
        "mba": "Measure agent activity by counting the number of sessions per agent.",
        "developer": "Count sessions grouped by agent_name.",
        "dba": "SELECT agent_name, COUNT(*) as session_count FROM agent_sessions GROUP BY agent_name ORDER BY session_count DESC"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 214,
      "category": "aggregation",
      "difficulty": "beginner",
      "aql": "RETURN LENGTH(code_artifacts)",
      "description": "Count the total number of code artifacts.",
      "english_variations": {
        "layperson": "How many code files are there in total?",
        "mba": "Get the total count of code artifacts for project size assessment.",
        "developer": "Count all documents in the code_artifacts collection.",
        "dba": "SELECT COUNT(*) FROM code_artifacts"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 215,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions COLLECT status = t.status WITH COUNT INTO count RETURN { status: status, count: count }",
      "description": "Count the number of tool executions by their final status.",
      "english_variations": {
        "layperson": "How many tools succeeded, failed, or timed out?",
        "mba": "Get the distribution of tool execution outcomes (success, failed, etc.).",
        "developer": "Count tool executions grouped by status.",
        "dba": "SELECT status, COUNT(*) as count FROM tool_executions GROUP BY status"
      },
      "expected_result_type": "aggregated",
      "visualization": "pie_chart"
    },
    {
      "id": 216,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR s IN agent_sessions COLLECT agent = s.agent_name LET failed_count = COUNT(FOR t IN tool_executions FILTER t.session_id == s.session_id AND t.status == 'failed' RETURN 1) RETURN { agent, total_failed_tools: SUM(failed_count) }",
      "description": "Calculate the total number of failed tools for each agent across all their sessions.",
      "english_variations": {
        "layperson": "Which agent has the most tool failures?",
        "mba": "Aggregate tool failure counts per agent to assess agent reliability.",
        "developer": "For each agent, sum the count of failed tools from their sessions.",
        "dba": "Complex join and aggregation to sum failed tools per agent."
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 217,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "LET artifact_sizes = (FOR a IN code_artifacts FILTER a.language == 'Python' RETURN a.size) RETURN { min_size: MIN(artifact_sizes), max_size: MAX(artifact_sizes), avg_size: AVERAGE(artifact_sizes) }",
      "description": "Get the min, max, and average size of Python code artifacts.",
      "english_variations": {
        "layperson": "How big are the Python files?",
        "mba": "Get key size metrics for Python code artifacts for code base analysis.",
        "developer": "Calculate min, max, and average size for Python artifacts.",
        "dba": "SELECT MIN(size), MAX(size), AVG(size) FROM code_artifacts WHERE language = 'Python'"
      },
      "expected_result_type": "aggregated",
      "visualization": "text"
    },
    {
      "id": 218,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures COLLECT type = e.error_type WITH COUNT INTO count SORT count DESC LIMIT 1 RETURN {most_common_error: type, count: count}",
      "description": "Find the single most common error type.",
      "english_variations": {
        "layperson": "What's our number one most common problem?",
        "mba": "Identify the top error type by frequency to prioritize root cause analysis.",
        "developer": "Find the most frequent error_type.",
        "dba": "SELECT error_type, COUNT(*) as count FROM errors_and_failures GROUP BY error_type ORDER BY count DESC LIMIT 1"
      },
      "expected_result_type": "aggregated",
      "visualization": "text"
    },
    {
      "id": 219,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR l IN lessons_learned COLLECT category = l.category INTO g RETURN { category: category, avg_confidence: AVERAGE(g[*].l.confidence) }",
      "description": "Calculate the average confidence score for lessons in each category.",
      "english_variations": {
        "layperson": "Which lesson categories are we most confident about?",
        "mba": "Assess the average confidence level of knowledge across different categories.",
        "developer": "Get the average confidence for lessons, grouped by category.",
        "dba": "SELECT category, AVG(confidence) as avg_confidence FROM lessons_learned GROUP BY category"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 220,
      "category": "aggregation",
      "difficulty": "beginner",
      "aql": "RETURN SUM(FOR t IN tool_executions RETURN t.duration_ms)",
      "description": "Calculate the total time spent by all tool executions combined.",
      "english_variations": {
        "layperson": "How much total time have tools spent running?",
        "mba": "Aggregate the total tool execution time to measure computational resource consumption.",
        "developer": "Sum the duration_ms of all tool executions.",
        "dba": "SELECT SUM(duration_ms) FROM tool_executions"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 221,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "RETURN COUNT(DISTINCT log.script_name FOR log IN log_events)",
      "description": "Count the number of unique script names that have produced logs.",
      "english_variations": {
        "layperson": "How many different scripts are creating logs?",
        "mba": "Measure the breadth of script logging across the system.",
        "developer": "Count the distinct script_names in log_events.",
        "dba": "SELECT COUNT(DISTINCT script_name) FROM log_events"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 222,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR s IN agent_sessions LET tool_count = LENGTH(FOR t IN tool_executions FILTER t.session_id == s.session_id RETURN 1) FILTER tool_count > 0 RETURN { session_id: s.session_id, tool_count: tool_count, avg_tool_duration: AVERAGE(FOR t IN tool_executions FILTER t.session_id == s.session_id RETURN t.duration_ms) }",
      "description": "For each session, list its tool count and the average duration of tools used in it.",
      "english_variations": {
        "layperson": "In each session, how many tools were used and how long did they take on average?",
        "mba": "Analyze session-level metrics on tool usage and average tool performance.",
        "developer": "For each session, calculate the tool count and average tool duration.",
        "dba": "SELECT s.session_id, COUNT(t.tool_name), AVG(t.duration_ms) FROM agent_sessions s JOIN tool_executions t ON s.session_id = t.session_id GROUP BY s.session_id"
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 223,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures COLLECT is_resolved = e.resolved WITH COUNT INTO count RETURN { is_resolved, count }",
      "description": "Count the number of resolved vs. unresolved errors.",
      "english_variations": {
        "layperson": "How many problems are fixed versus still open?",
        "mba": "Get the breakdown of resolved vs. unresolved errors for backlog management.",
        "developer": "Count errors grouped by the 'resolved' boolean.",
        "dba": "SELECT resolved, COUNT(*) FROM errors_and_failures GROUP BY resolved"
      },
      "expected_result_type": "aggregated",
      "visualization": "pie_chart"
    },
    {
      "id": 224,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "LET durations = (FOR t IN tool_executions RETURN t.duration_ms) RETURN { median: MEDIAN(durations), p90: PERCENTILE(durations, 90), p99: PERCENTILE(durations, 99) }",
      "description": "Calculate the median, 90th, and 99th percentile for all tool execution durations.",
      "english_variations": {
        "layperson": "What are the typical and worst-case runtimes for tools?",
        "mba": "Analyze key percentile metrics for tool execution duration to understand performance SLAs.",
        "developer": "Calculate median, p90, and p99 for tool durations.",
        "dba": "SELECT PERCENTILE_CONT(0.5), PERCENTILE_CONT(0.9), PERCENTILE_CONT(0.99) FROM tool_executions"
      },
      "expected_result_type": "aggregated",
      "visualization": "text"
    },
    {
      "id": 225,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR g IN glossary_terms COLLECT category = g.category WITH COUNT INTO count RETURN { category, count }",
      "description": "Count the number of glossary terms in each category.",
      "english_variations": {
        "layperson": "How many terms do we have for each category?",
        "mba": "Get the distribution of knowledge base terms across categories.",
        "developer": "Count glossary terms grouped by category.",
        "dba": "SELECT category, COUNT(*) FROM glossary_terms GROUP BY category"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 226,
      "category": "aggregation",
      "difficulty": "beginner",
      "aql": "RETURN COUNT(lessons_learned)",
      "description": "Count the total number of lessons learned.",
      "english_variations": {
        "layperson": "How many lessons have we learned in total?",
        "mba": "Get the total count of entries in the knowledge base.",
        "developer": "Count all documents in the lessons_learned collection.",
        "dba": "SELECT COUNT(*) FROM lessons_learned"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 227,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR error IN errors_and_failures LET session_status = (FOR s IN agent_sessions FILTER s.session_id == error.session_id RETURN s.status)[0] COLLECT status = session_status WITH COUNT INTO error_count RETURN { session_status: status, error_count: error_count }",
      "description": "Count how many errors occurred in successful, failed, and timed-out sessions.",
      "english_variations": {
        "layperson": "Do more errors happen in failed sessions?",
        "mba": "Correlate error counts with the final status of the session.",
        "developer": "Group errors by the status of their parent session and count them.",
        "dba": "SELECT s.status, COUNT(e._key) FROM errors_and_failures e JOIN agent_sessions s ON e.session_id = s.session_id GROUP BY s.status"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 228,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR c IN code_artifacts COLLECT op = c.operation WITH COUNT INTO count RETURN { operation: op, count: count }",
      "description": "Count the number of code artifacts by operation type (create, modify, delete).",
      "english_variations": {
        "layperson": "How many files were created vs. modified vs. deleted?",
        "mba": "Analyze the distribution of code modification operations (create, modify, delete).",
        "developer": "Count artifacts grouped by operation.",
        "dba": "SELECT operation, COUNT(*) FROM code_artifacts GROUP BY operation"
      },
      "expected_result_type": "aggregated",
      "visualization": "pie_chart"
    },
    {
      "id": 229,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "RETURN STDDEV(FOR t IN tool_executions RETURN t.duration_ms)",
      "description": "Calculate the standard deviation of tool execution durations.",
      "english_variations": {
        "layperson": "How much does the runtime of tools vary?",
        "mba": "Measure the variability in tool execution time to assess performance consistency.",
        "developer": "Calculate the standard deviation of duration_ms.",
        "dba": "SELECT STDDEV(duration_ms) FROM tool_executions"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 230,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR s IN solution_outcomes COLLECT category = s.category INTO group RETURN { category: category, success_rate: (SUM(g.s.outcome == 'success' ? 1 : 0) / COUNT(g)) * 100 }",
      "description": "Calculate the success rate for solutions within each category.",
      "english_variations": {
        "layperson": "What type of solutions are most successful?",
        "mba": "Analyze solution success rates by category to guide strategic focus.",
        "developer": "Calculate success percentage for solutions, grouped by category.",
        "dba": "SELECT category, (SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) / COUNT(*)) * 100 FROM solution_outcomes GROUP BY category"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 231,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "RETURN COUNT(DISTINCT tool.session_id FOR tool IN tool_executions)",
      "description": "Count the number of unique sessions that used at least one tool.",
      "english_variations": {
        "layperson": "How many sessions actually used tools?",
        "mba": "Measure the number of sessions with tool interaction.",
        "developer": "Count distinct session_ids in tool_executions.",
        "dba": "SELECT COUNT(DISTINCT session_id) FROM tool_executions"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 232,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events FILTER log.error_type != null COLLECT script = log.script_name WITH COUNT INTO error_count SORT error_count DESC RETURN { script, error_count }",
      "description": "Count the number of errors generated by each script.",
      "english_variations": {
        "layperson": "Which scripts are the most error-prone?",
        "mba": "Identify scripts with the highest error counts to prioritize for review.",
        "developer": "Count errors grouped by script_name.",
        "dba": "SELECT script_name, COUNT(*) FROM log_events WHERE error_type IS NOT NULL GROUP BY script_name ORDER BY COUNT(*) DESC"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 233,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR tool IN tool_executions COLLECT name = tool.tool_name INTO g RETURN { name, success_rate: (COUNT(g[* FILTER CURRENT.t.status == 'success']) / COUNT(g)) * 100 }",
      "description": "Calculate the success rate for each individual tool.",
      "english_variations": {
        "layperson": "Which tools are the most reliable?",
        "mba": "Measure the success rate of each tool to evaluate toolchain reliability.",
        "developer": "Calculate the success percentage for each tool, grouped by tool_name.",
        "dba": "SELECT tool_name, (SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*)) * 100 FROM tool_executions GROUP BY tool_name"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 234,
      "category": "aggregation",
      "difficulty": "beginner",
      "aql": "RETURN COUNT(agent_sessions)",
      "description": "Count the total number of agent sessions.",
      "english_variations": {
        "layperson": "How many work sessions have there been in total?",
        "mba": "Get the total count of agent sessions for overall activity reporting.",
        "developer": "Count all documents in agent_sessions.",
        "dba": "SELECT COUNT(*) FROM agent_sessions"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 235,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR a in code_artifacts COLLECT lang = a.language WITH COUNT INTO file_count RETURN {language: lang, file_count: file_count}",
      "description": "Count the number of code files for each programming language.",
      "english_variations": {
        "layperson": "How many files of each language do we have?",
        "mba": "Get the breakdown of the codebase by programming language.",
        "developer": "Count artifacts grouped by language.",
        "dba": "SELECT language, COUNT(*) as file_count FROM code_artifacts GROUP BY language"
      },
      "expected_result_type": "aggregated",
      "visualization": "pie_chart"
    },
    {
      "id": 236,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "LET total_size = SUM(FOR a IN code_artifacts RETURN a.size) FOR a IN code_artifacts COLLECT lang = a.language INTO g LET lang_size = SUM(g[*].a.size) RETURN { language: lang, percentage_of_total: (lang_size / total_size) * 100 }",
      "description": "Calculate the percentage of total code size for each language.",
      "english_variations": {
        "layperson": "What percentage of our code is Python vs JavaScript?",
        "mba": "Analyze the codebase composition by language as a percentage of total size.",
        "developer": "Calculate the percentage of total size for each language.",
        "dba": "Complex query to calculate percentage of total size by language."
      },
      "expected_result_type": "aggregated",
      "visualization": "pie_chart"
    },
    {
      "id": 237,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures WHERE e.resolution != null RETURN COUNT(DISTINCT e.resolution)",
      "description": "Count the number of unique resolutions that have been applied to errors.",
      "english_variations": {
        "layperson": "How many different kinds of fixes have we used?",
        "mba": "Measure the diversity of error resolution strategies.",
        "developer": "Count the distinct resolution strings for errors.",
        "dba": "SELECT COUNT(DISTINCT resolution) FROM errors_and_failures WHERE resolution IS NOT NULL"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 238,
      "category": "aggregation",
      "difficulty": "expert",
      "aql": "FOR s IN agent_sessions LET error_types_in_session = UNIQUE(FOR e IN errors_and_failures FILTER e.session_id == s.session_id RETURN e.error_type) FILTER LENGTH(error_types_in_session) > 2 RETURN { session_id: s.session_id, unique_error_types: error_types_in_session }",
      "description": "Find sessions that had more than two unique types of errors.",
      "english_variations": {
        "layperson": "Which sessions had many different kinds of problems?",
        "mba": "Identify sessions with a high diversity of error types, indicating complex failures.",
        "developer": "Find sessions with more than 2 unique error types.",
        "dba": "SELECT s.session_id, ARRAY_AGG(DISTINCT e.error_type) FROM agent_sessions s JOIN errors_and_failures e ON s.session_id = e.session_id GROUP BY s.session_id HAVING COUNT(DISTINCT e.error_type) > 2"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 239,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "RETURN MAX(FOR l IN lessons_learned RETURN l.evidence_count)",
      "description": "Find the highest evidence count for any single lesson learned.",
      "english_variations": {
        "layperson": "What's the most-proven lesson we have?",
        "mba": "Identify the lesson with the strongest evidence base.",
        "developer": "Get the max evidence_count from lessons_learned.",
        "dba": "SELECT MAX(evidence_count) FROM lessons_learned"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 240,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR log IN log_events COLLECT level = log.level WITH COUNT INTO count RETURN {level, count}",
      "description": "Count the number of log events for each severity level.",
      "english_variations": {
        "layperson": "How many logs of each type are there?",
        "mba": "Get the distribution of log events by severity level.",
        "developer": "Count logs grouped by level.",
        "dba": "SELECT level, COUNT(*) FROM log_events GROUP BY level"
      },
      "expected_result_type": "aggregated",
      "visualization": "pie_chart"
    },
    {
      "id": 241,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR tool IN UNIQUE(FOR t IN tool_executions RETURN t.tool_name) LET sessions_using_tool = COUNT(DISTINCT FOR t IN tool_executions FILTER t.tool_name == tool RETURN t.session_id) RETURN { tool, session_count: sessions_using_tool }",
      "description": "For each tool, count how many unique sessions it was used in.",
      "english_variations": {
        "layperson": "How many different work sessions used each tool?",
        "mba": "Measure the adoption of each tool by counting its usage across unique sessions.",
        "developer": "For each tool, count the number of distinct sessions it appeared in.",
        "dba": "SELECT tool_name, COUNT(DISTINCT session_id) FROM tool_executions GROUP BY tool_name"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 242,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "RETURN SUM(FOR a IN code_artifacts RETURN a.size)",
      "description": "Calculate the total size of all code artifacts combined.",
      "english_variations": {
        "layperson": "What's the total size of all our code?",
        "mba": "Determine the total size of the codebase for infrastructure planning.",
        "developer": "Sum the size of all code artifacts.",
        "dba": "SELECT SUM(size) FROM code_artifacts"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 243,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions FILTER t.exit_code != 0 COLLECT tool = t.tool_name WITH COUNT INTO failure_count SORT failure_count DESC RETURN { tool, failure_count }",
      "description": "Count the number of failures (non-zero exit code) for each tool.",
      "english_variations": {
        "layperson": "Which tools fail the most often?",
        "mba": "Identify the tools with the highest failure counts to prioritize for replacement or fixing.",
        "developer": "Count non-zero exit codes, grouped by tool_name.",
        "dba": "SELECT tool_name, COUNT(*) FROM tool_executions WHERE exit_code != 0 GROUP BY tool_name ORDER BY COUNT(*) DESC"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 244,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR session IN agent_sessions LET duration_hours = session.duration_ms / 3600000.0 COLLECT agent = session.agent_name INTO g RETURN { agent, total_hours: SUM(g[*].duration_hours) }",
      "description": "Calculate the total number of hours each agent has been active.",
      "english_variations": {
        "layperson": "How many hours has each agent worked in total?",
        "mba": "Aggregate the total active hours per agent for resource utilization and cost analysis.",
        "developer": "Sum the session durations in hours for each agent.",
        "dba": "SELECT agent_name, SUM(duration_ms / 3600000.0) FROM agent_sessions GROUP BY agent_name"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 245,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "RETURN COUNT(DISTINCT e.session_id FOR e IN errors_and_failures)",
      "description": "Count the number of unique sessions that have at least one error.",
      "english_variations": {
        "layperson": "How many sessions had errors?",
        "mba": "Measure the number of sessions impacted by errors.",
        "developer": "Count the distinct session_ids in the errors collection.",
        "dba": "SELECT COUNT(DISTINCT session_id) FROM errors_and_failures"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 246,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR s IN solution_outcomes COLLECT category = s.category INTO g RETURN { category, avg_success_score: AVERAGE(g[*].s.success_score) }",
      "description": "Calculate the average success score for solutions in each category.",
      "english_variations": {
        "layperson": "On average, how well do solutions in each category work?",
        "mba": "Analyze the average success score by solution category to identify areas of strength.",
        "developer": "Get the average success_score, grouped by category.",
        "dba": "SELECT category, AVG(success_score) FROM solution_outcomes GROUP BY category"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 247,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "RETURN MIN(FOR s IN agent_sessions FILTER s.status == 'completed' RETURN s.duration_ms)",
      "description": "Find the duration of the fastest completed agent session.",
      "english_variations": {
        "layperson": "What's the quickest a task has ever been finished?",
        "mba": "Identify the minimum completion time for any session as a performance benchmark.",
        "developer": "Get the minimum duration_ms for completed sessions.",
        "dba": "SELECT MIN(duration_ms) FROM agent_sessions WHERE status = 'completed'"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 248,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "LET total_errors = LENGTH(errors_and_failures) LET resolved_errors = LENGTH(FOR e IN errors_and_failures FILTER e.resolved == true RETURN 1) RETURN (resolved_errors / total_errors) * 100",
      "description": "Calculate the overall percentage of errors that have been resolved.",
      "english_variations": {
        "layperson": "What percentage of our problems are solved?",
        "mba": "Determine the overall error resolution rate KPI.",
        "developer": "Calculate the percentage of errors where resolved is true.",
        "dba": "SELECT (CAST(SUM(CASE WHEN resolved = true THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)) * 100 FROM errors_and_failures"
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 249,
      "category": "aggregation",
      "difficulty": "intermediate",
      "aql": "FOR g IN glossary_terms SORT g.usage_count DESC LIMIT 10 RETURN {term: g.term, usage_count: g.usage_count}",
      "description": "List the top 10 most used glossary terms.",
      "english_variations": {
        "layperson": "What are the 10 most popular terms?",
        "mba": "Identify the top 10 most referenced concepts in the knowledge base.",
        "developer": "Get the top 10 glossary terms by usage_count.",
        "dba": "SELECT term, usage_count FROM glossary_terms ORDER BY usage_count DESC LIMIT 10"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 250,
      "category": "aggregation",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures LET day_of_week = DATE_DAYOFWEEK(e.timestamp) COLLECT day = day_of_week WITH COUNT INTO count SORT day RETURN {day, count}",
      "description": "Count the number of errors that occur on each day of the week.",
      "english_variations": {
        "layperson": "On which day of the week do most errors happen?",
        "mba": "Analyze the distribution of errors across the days of the week to find patterns.",
        "developer": "Count errors grouped by day of the week.",
        "dba": "SELECT DAYOFWEEK(timestamp), COUNT(*) FROM errors_and_failures GROUP BY DAYOFWEEK(timestamp)"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 251,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR session IN agent_sessions FILTER session.session_id == 'session_001' FOR v, e IN 1..1 OUTBOUND session agent_flow RETURN v",
      "description": "Get all direct artifacts and errors for a specific session.",
      "english_variations": {
        "layperson": "What did session_001 produce or cause?",
        "mba": "Audit the direct outputs and incidents of a specific session.",
        "developer": "Traverse 1 hop outbound from 'session_001' on the agent_flow graph.",
        "dba": "Show all nodes connected via one outbound 'agent_flow' edge from session_001."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 252,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR artifact IN code_artifacts FILTER artifact.file_path == '/project/src/main.py' FOR v, e, p IN 1..5 INBOUND artifact artifact_lineage RETURN p.vertices[*].file_path",
      "description": "Trace the full upstream history of a specific file.",
      "english_variations": {
        "layperson": "Show me the history of how 'main.py' was made.",
        "mba": "Conduct a full provenance audit for a critical code artifact.",
        "developer": "Trace the artifact_lineage graph backwards from 'main.py' up to 5 hops.",
        "dba": "Perform a recursive traversal to find the ancestry of a specific artifact."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 253,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR error IN errors_and_failures FILTER error.error_type == 'TimeoutError' FOR v, e, p IN 1..2 OUTBOUND error error_causality RETURN p",
      "description": "Show the 2-hop downstream impact of all TimeoutErrors.",
      "english_variations": {
        "layperson": "What other problems are caused by timeouts?",
        "mba": "Analyze the cascading failure impact of timeout-related incidents.",
        "developer": "Trace the error_causality graph 2 hops outbound from all TimeoutErrors.",
        "dba": "Show the 2-level outbound traversal path from all 'TimeoutError' nodes."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 254,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR tool IN tool_executions FILTER tool.tool_name == 'git' FOR v, e IN 1..1 INBOUND tool tool_dependencies RETURN v",
      "description": "Find which tools directly depend on the 'git' tool.",
      "english_variations": {
        "layperson": "Which tools need 'git' to work?",
        "mba": "Identify direct dependencies on the 'git' tool for toolchain analysis.",
        "developer": "Find nodes with an inbound edge to 'git' on the tool_dependencies graph.",
        "dba": "Show all nodes with a 1-hop inbound 'tool_dependencies' connection to 'git'."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 255,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR term IN glossary_terms FILTER term.term == 'API' FOR v, e, p IN 1..3 ANY term term_relationships RETURN p",
      "description": "Explore the semantic neighborhood of the term 'API' up to 3 hops away.",
      "english_variations": {
        "layperson": "Show me all terms related to 'API'.",
        "mba": "Map the conceptual cluster around the 'API' term in the knowledge base.",
        "developer": "Traverse the term_relationships graph 3 hops in any direction from 'API'.",
        "dba": "Display the 3-hop bidirectional traversal path from the 'API' glossary term."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 256,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR session IN agent_sessions FILTER session.status == 'failed' FOR v, e IN 1..1 OUTBOUND session agent_flow FILTER IS_SAME_COLLECTION('errors_and_failures', v) RETURN { session_id: session.session_id, error: v }",
      "description": "For all failed sessions, get the specific errors directly linked to them.",
      "english_variations": {
        "layperson": "What errors caused sessions to fail?",
        "mba": "Correlate failed sessions directly with their resulting error records.",
        "developer": "For failed sessions, get the adjacent error nodes via the agent_flow graph.",
        "dba": "Join failed sessions to their errors via the 'agent_flow' edge collection."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 257,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "SHORTEST_PATH 'errors_and_failures/error_A' TO 'errors_and_failures/error_Z' IN error_causality RETURN p",
      "description": "Find the shortest causality path between two specific errors.",
      "english_variations": {
        "layperson": "How did error A lead to error Z?",
        "mba": "Determine the most direct root cause path between two key incidents.",
        "developer": "Find the shortest path between two error nodes on the error_causality graph.",
        "dba": "Execute a SHORTEST_PATH query on the 'error_causality' graph."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 258,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR artifact IN code_artifacts FILTER artifact.language == 'Python' FOR v, e IN 1..1 INBOUND artifact agent_flow FILTER IS_SAME_COLLECTION('agent_sessions', v) RETURN v.session_id",
      "description": "Find the sessions that created or modified Python artifacts.",
      "english_variations": {
        "layperson": "Which sessions worked on Python files?",
        "mba": "Identify all sessions involving modifications to Python code assets.",
        "developer": "Get sessions that have an outbound edge to a Python artifact.",
        "dba": "Find 'agent_sessions' nodes connected to 'Python' artifacts via an inbound 'agent_flow' edge."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 259,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR start_node IN errors_and_failures FILTER NOT(HAS(start_node, 'resolved')) FOR v, e, p IN 1..* INBOUND start_node error_causality RETURN p",
      "description": "For an unresolved error, trace its entire chain of causes back to the root.",
      "english_variations": {
        "layperson": "What's the full story behind this unsolved problem?",
        "mba": "Perform a complete root cause analysis for an unresolved incident.",
        "developer": "Trace the error_causality graph backwards from an unresolved error to its origin.",
        "dba": "Perform a full inbound traversal from an unresolved node to find its root cause(s)."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 260,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR t IN tool_executions FOR v,e IN 1..1 OUTBOUND t tool_dependencies RETURN {user: t.tool_name, dependency: v.tool_name}",
      "description": "List all direct, first-level tool dependencies.",
      "english_variations": {
        "layperson": "Show me what tools depend on what other tools.",
        "mba": "Map the first-level dependencies within the toolchain.",
        "developer": "List all one-hop outbound edges in the tool_dependencies graph.",
        "dba": "Show all pairs of nodes connected by the 'tool_dependencies' edges."
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 261,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR tool IN tool_executions LET downstream_count = LENGTH(FOR v IN 1..10 OUTBOUND tool tool_dependencies RETURN 1) FILTER downstream_count == 0 RETURN tool",
      "description": "Find tools that are at the end of a dependency chain (have no downstream dependencies).",
      "english_variations": {
        "layperson": "Which tools don't rely on anything else?",
        "mba": "Identify foundational, non-dependent tools in the technology stack.",
        "developer": "Find leaf nodes in the tool_dependencies graph.",
        "dba": "Find all nodes in 'tool_executions' with an outbound degree of 0 in the 'tool_dependencies' graph."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 262,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR term IN glossary_terms FOR v, e IN 1..1 OUTBOUND term term_relationships FILTER v.category != term.category RETURN {from: term.term, to: v.term}",
      "description": "Find glossary terms that are related to terms in a different category.",
      "english_variations": {
        "layperson": "Show me connections between different topics.",
        "mba": "Identify inter-disciplinary links within the knowledge base.",
        "developer": "Find edges in term_relationships that cross category boundaries.",
        "dba": "Find 'term_relationships' edges where the source and target nodes have different 'category' attributes."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 263,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures FOR v, e_edge IN 1..1 INBOUND e agent_flow RETURN v",
      "description": "For each error, find the session it belongs to.",
      "english_variations": {
        "layperson": "Which session did each error happen in?",
        "mba": "Attribute each error incident to its originating session.",
        "developer": "For each error, traverse inbound on agent_flow to find the parent session.",
        "dba": "For each 'errors_and_failures' node, find its parent 'agent_sessions' node."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 264,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR session IN agent_sessions LET artifacts = (FOR v IN 1..1 OUTBOUND session agent_flow FILTER IS_SAME_COLLECTION('code_artifacts', v) RETURN v) FILTER LENGTH(artifacts) > 5 RETURN session",
      "description": "Find sessions that produced more than 5 code artifacts.",
      "english_variations": {
        "layperson": "Which sessions created a lot of files?",
        "mba": "Identify highly productive sessions based on the volume of code artifacts generated.",
        "developer": "Find sessions with an outbound degree greater than 5 to code_artifacts nodes.",
        "dba": "Find 'agent_sessions' nodes with more than 5 outbound 'agent_flow' edges to 'code_artifacts' nodes."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 265,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR path IN K_SHORTEST_PATHS 'errors_and_failures/A' TO 'errors_and_failures/Z' IN error_causality LIMIT 3 RETURN path",
      "description": "Find the top 3 shortest paths of causality between two errors.",
      "english_variations": {
        "layperson": "What are the different ways error A could have led to error Z?",
        "mba": "Analyze primary and secondary causal pathways between two key incidents.",
        "developer": "Find the 3-shortest-paths between two nodes on the error_causality graph.",
        "dba": "Execute a K_SHORTEST_PATHS query on the 'error_causality' graph."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 266,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR c IN code_artifacts FOR v, e, p IN 1..2 OUTBOUND c artifact_lineage COLLECT root = p.vertices[0]._id INTO paths RETURN { root, count: LENGTH(paths) }",
      "description": "For each code artifact, count how many other artifacts it influences within 2 hops.",
      "english_variations": {
        "layperson": "Which files have the biggest impact on other files?",
        "mba": "Identify highly influential code artifacts based on their downstream dependency count.",
        "developer": "For each artifact, count its 2-hop downstream descendants.",
        "dba": "Calculate the size of the 2-hop outbound neighborhood for each 'code_artifacts' node."
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 267,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR tool IN tool_executions FILTER tool.status == 'failed' FOR v,e IN 1..1 INBOUND tool agent_flow RETURN v",
      "description": "Find the sessions in which a tool execution failed.",
      "english_variations": {
        "layperson": "Which sessions had tool failures?",
        "mba": "Identify sessions impacted by tool execution failures.",
        "developer": "For failed tools, find their parent session via an inbound graph traversal.",
        "dba": "Find the parent 'agent_sessions' node for each 'tool_executions' node with status 'failed'."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 268,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR term IN glossary_terms LET related_errors_count = LENGTH(FOR v IN 1..1 OUTBOUND term term_relationships FILTER IS_SAME_COLLECTION('errors_and_failures', v) RETURN 1) FILTER related_errors_count > 0 RETURN term",
      "description": "Find glossary terms that are directly linked to error documents.",
      "english_variations": {
        "layperson": "Which terms are connected to actual errors?",
        "mba": "Identify knowledge base concepts that are directly relevant to known system errors.",
        "developer": "Find glossary terms that have edges pointing to nodes in the errors collection.",
        "dba": "Find 'glossary_terms' nodes with at least one outbound edge to an 'errors_and_failures' node."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 269,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR e IN errors_and_failures LET causing_errors = (FOR v IN 1..1 INBOUND e error_causality RETURN v) FILTER LENGTH(causing_errors) == 0 RETURN e",
      "description": "Find errors that are root causes (have no inbound causality edges).",
      "english_variations": {
        "layperson": "Which errors are the start of a problem chain?",
        "mba": "Identify root cause incidents that are not triggered by other errors.",
        "developer": "Find error nodes with an in-degree of 0 in the error_causality graph.",
        "dba": "Find 'errors_and_failures' nodes with no inbound 'error_causality' edges."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 270,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR a1 IN code_artifacts FOR a2 IN code_artifacts FILTER a1._id != a2._id FOR p IN ALL_SHORTEST_PATHS a1 TO a2 IN artifact_lineage RETURN p",
      "description": "Find all shortest lineage paths between any two code artifacts (computationally expensive).",
      "english_variations": {
        "layperson": "How are any two files connected?",
        "mba": "Perform a comprehensive analysis of all direct lineage connections in the codebase.",
        "developer": "Find all shortest paths between all pairs of artifact nodes.",
        "dba": "Execute an all-pairs shortest path query on the 'artifact_lineage' graph."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 271,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR session IN agent_sessions FOR v, e, p IN 2..2 OUTBOUND session agent_flow RETURN p",
      "description": "Find all 2nd-degree connections from agent sessions (e.g., tools used by a tool in a session).",
      "english_variations": {
        "layperson": "What is connected to the things that are connected to a session?",
        "mba": "Analyze the secondary impacts and dependencies of agent sessions.",
        "developer": "Perform a 2-hop outbound traversal from all agent sessions.",
        "dba": "Show all paths of length 2 originating from 'agent_sessions' nodes."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 272,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR a IN code_artifacts FILTER a.file_path == 'deleted_file.py' FOR v, e IN 1..1 ANY a artifact_lineage RETURN v",
      "description": "Find what a deleted file was connected to.",
      "english_variations": {
        "layperson": "What was connected to 'deleted_file.py'?",
        "mba": "Analyze the dependencies and dependents of a deleted artifact for impact assessment.",
        "developer": "Find all neighbors of the 'deleted_file.py' artifact node.",
        "dba": "Show all adjacent nodes to 'deleted_file.py' in the 'artifact_lineage' graph."
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 273,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR v, e IN aql_dependencies FILTER e.type == 'read' RETURN { reader: e._from, readee: e._to }",
      "description": "Specifically find 'read' dependencies between AQL queries.",
      "english_variations": {
        "layperson": "Which queries read from each other?",
        "mba": "Map out the read-dependency relationships in the AQL query library.",
        "developer": "Filter edges in the aql_dependencies graph for type 'read'.",
        "dba": "SELECT _from, _to FROM aql_dependencies WHERE type = 'read'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 274,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR tool IN tool_executions LET dependencies = (FOR v IN 1..* OUTBOUND tool tool_dependencies RETURN v.tool_name) FILTER 'compiler' IN dependencies RETURN tool",
      "description": "Find all tools that have 'compiler' as a downstream dependency.",
      "english_variations": {
        "layperson": "Which tools end up using a compiler?",
        "mba": "Identify all parts of the toolchain that have a dependency on a compiler.",
        "developer": "Find tools that have 'compiler' in their dependency tree.",
        "dba": "Find all nodes from which the 'compiler' node is reachable."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 275,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR t IN glossary_terms FOR v,e IN 1..1 OUTBOUND t term_relationships COLLECT source=t.term, target=v.term RETURN {source, target}",
      "description": "List all direct relationships between glossary terms.",
      "english_variations": {
        "layperson": "Show me all the term connections.",
        "mba": "Generate an edge list of all direct relationships in the knowledge graph.",
        "developer": "List all one-hop outbound edges in the term_relationships graph.",
        "dba": "SELECT t1.term, t2.term FROM term_relationships r JOIN glossary_terms t1 ON r._from = t1._id JOIN glossary_terms t2 ON r._to = t2._id"
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 276,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR c IN cycles IN tool_dependencies RETURN c",
      "description": "Find any circular dependencies in the toolchain.",
      "english_variations": {
        "layperson": "Are there any tools that depend on each other in a circle?",
        "mba": "Detect circular dependencies in the toolchain, which represent a significant architectural risk.",
        "developer": "Find cycles in the tool_dependencies graph.",
        "dba": "Execute a cycle detection query on the 'tool_dependencies' graph."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 277,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR error IN errors_and_failures LET path_count = COUNT(FOR p IN ALL_SHORTEST_PATHS 'errors_and_failures/root_cause' TO error IN error_causality RETURN 1) FILTER path_count > 1 RETURN error",
      "description": "Find errors that can be reached from a known root cause via multiple different paths.",
      "english_variations": {
        "layperson": "Which problems have multiple causes stemming from one root issue?",
        "mba": "Identify incidents with multiple causal pathways from a single root cause.",
        "developer": "Find nodes reachable from a start node by more than one shortest path.",
        "dba": "Find nodes with multiple shortest paths from a given source node."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 278,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR session IN agent_sessions FILTER session.agent_name == 'cursor-ai' FOR v, e IN 1..1 OUTBOUND session agent_flow FILTER IS_SAME_COLLECTION('code_artifacts', v) RETURN v.file_path",
      "description": "List all files modified by the 'cursor-ai' agent.",
      "english_variations": {
        "layperson": "What files did the cursor-ai agent change?",
        "mba": "Audit all code modifications made by the 'cursor-ai' agent.",
        "developer": "Get artifacts created by 'cursor-ai' sessions.",
        "dba": "Find 'code_artifacts' nodes connected from 'cursor-ai' sessions."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 279,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR v, e, p IN 1..5 OUTBOUND 'code_artifacts/main_module.py' artifact_lineage OPTIONS {uniqueVertices: 'path'} RETURN p",
      "description": "Trace the downstream lineage of a module, ensuring no cycles are followed in the path.",
      "english_variations": {
        "layperson": "What does the main module affect, without getting into loops?",
        "mba": "Map the acyclic downstream impact of a core module.",
        "developer": "Trace artifact lineage with the uniqueVertices path option.",
        "dba": "Perform a traversal with the 'uniqueVertices' option to avoid cycles."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 280,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR v,e IN NEIGHBORS('glossary_terms/term_A', 'term_relationships', {includeData: true}) RETURN {neighbor: v.term, edge_type: e.type}",
      "description": "Get the immediate neighbors of a glossary term and the type of relationship.",
      "english_variations": {
        "layperson": "What's directly related to term A and how?",
        "mba": "Analyze the immediate, typed relationships of a key concept.",
        "developer": "Use the NEIGHBORS function to get adjacent nodes and connecting edge data.",
        "dba": "Execute the NEIGHBORS AQL function to get 1-hop neighbors and edges."
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 281,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR err IN errors_and_failures FOR sess, edge, path IN 1..1 INBOUND err agent_flow LET tools = (FOR t IN tool_executions FILTER t.session_id == sess.session_id SORT t.start_time DESC LIMIT 1 RETURN t.tool_name) RETURN {error: err.error_type, last_tool_used: tools[0]}",
      "description": "For each error, find the last tool that was used in the session before the error occurred.",
      "english_variations": {
        "layperson": "What tool was used right before each error?",
        "mba": "Correlate errors with the immediately preceding tool usage to identify potential causes.",
        "developer": "For each error, find its session and the last tool used in that session.",
        "dba": "Complex graph traversal and subquery to find the last tool used before an error."
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 282,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR v, e IN 1..1 OUTBOUND 'agent_sessions/s1' agent_flow RETURN v._id",
      "description": "Get the _id of all nodes directly connected from session 's1'.",
      "english_variations": {
        "layperson": "Show me what's connected to session s1.",
        "mba": "List the database IDs of all artifacts and errors for session s1.",
        "developer": "Get the _id of all 1-hop outbound neighbors of session 's1'.",
        "dba": "SELECT _to FROM agent_flow WHERE _from = 'agent_sessions/s1'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 283,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "WITH errors_and_failures, tool_executions FOR v, e, p IN 1..5 OUTBOUND 'tool_executions/t1' tool_dependencies, error_causality RETURN p",
      "description": "Trace a mixed path of dependencies and errors from a starting tool.",
      "english_variations": {
        "layperson": "Follow the chain of tool dependencies and errors from tool t1.",
        "mba": "Conduct a multi-graph traversal to analyze combined tool and error propagation.",
        "developer": "Traverse across both the tool_dependencies and error_causality graphs.",
        "dba": "Perform a traversal over a named graph combining multiple edge collections."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 284,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR sess IN agent_sessions LET connected_errors = (FOR v IN 1..1 OUTBOUND sess agent_flow FILTER IS_SAME_COLLECTION(v, 'errors_and_failures') RETURN v) FILTER LENGTH(connected_errors) == 0 RETURN sess",
      "description": "Find all agent sessions that have no errors directly connected to them.",
      "english_variations": {
        "layperson": "Show me the error-free sessions.",
        "mba": "Identify sessions with no recorded errors to analyze successful execution patterns.",
        "developer": "Find sessions with no outbound edges to the errors_and_failures collection.",
        "dba": "Find 'agent_sessions' nodes with an outbound degree of 0 to 'errors_and_failures'."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 285,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR v, e IN 1..1 INBOUND 'code_artifacts/a1' artifact_lineage RETURN v.file_path",
      "description": "Find the direct parents of a given code artifact.",
      "english_variations": {
        "layperson": "What file(s) was this file made from?",
        "mba": "Identify the direct source artifacts for a given code file.",
        "developer": "Get the 1-hop inbound neighbors for artifact 'a1'.",
        "dba": "SELECT v.file_path FROM artifact_lineage e JOIN code_artifacts v ON e._from = v._id WHERE e._to = 'code_artifacts/a1'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 286,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR v, e, p IN 1..10 OUTBOUND 'tool_executions/t1' tool_dependencies PRUNE p.edges[0].type == 'legacy' RETURN p.vertices[*].tool_name",
      "description": "Trace tool dependencies, but stop exploring a path if it involves a 'legacy' dependency type.",
      "english_variations": {
        "layperson": "Show me tool dependencies, but ignore the old stuff.",
        "mba": "Map the modern tool dependency chain, excluding legacy connections.",
        "developer": "Traverse the dependency graph, pruning paths that go through a 'legacy' edge.",
        "dba": "Perform a graph traversal with a PRUNE condition on an edge attribute."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 287,
      "category": "graph_traversal",
      "difficulty": "expert",
      "aql": "FOR v, e IN EDGES(term_relationships, 'glossary_terms/t1', 'outbound') RETURN { to: e._to, type: e.type }",
      "description": "Using the EDGES function, get all outbound relationships and their types for a glossary term.",
      "english_variations": {
        "layperson": "What terms does t1 point to, and how?",
        "mba": "List all typed, outbound relationships for a specific knowledge base concept.",
        "developer": "Use the EDGES function to get outbound edges and their data.",
        "dba": "Execute the EDGES AQL function for a specific start node."
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 288,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR v,e IN 1..1 ANY 'errors_and_failures/e1' error_causality RETURN v",
      "description": "Find all errors that either caused or were caused by error 'e1'.",
      "english_variations": {
        "layperson": "What errors are immediately connected to e1?",
        "mba": "Analyze the immediate causal neighborhood of incident 'e1'.",
        "developer": "Get all 1-hop neighbors of error 'e1' in any direction.",
        "dba": "Show all nodes adjacent to 'e1' in the 'error_causality' graph."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 289,
      "category": "graph_traversal",
      "difficulty": "advanced",
      "aql": "FOR v, e, p IN 1..* OUTBOUND 'agent_sessions/s1' agent_flow FILTER p.vertices[-1].status == 'completed' RETURN p",
      "description": "From a session, trace paths that end in a 'completed' node.",
      "english_variations": {
        "layperson": "Follow the work from session s1 until it leads to something marked 'completed'.",
        "mba": "Map the workflow from a session to its successful conclusion.",
        "developer": "Traverse from a session, filtering for paths that end at a 'completed' node.",
        "dba": "Perform a graph traversal with a FILTER condition on the last vertex in the path."
      },
      "expected_result_type": "graph_nodes",
      "visualization": "network_graph"
    },
    {
      "id": 290,
      "category": "graph_traversal",
      "difficulty": "intermediate",
      "aql": "FOR v, e IN 1..1 OUTBOUND 'errors_and_failures/e1' error_causality RETURN COUNT(v)",
      "description": "Count how many other errors were directly caused by error 'e1'.",
      "english_variations": {
        "layperson": "How many problems did error e1 cause?",
        "mba": "Quantify the immediate downstream impact of incident e1.",
        "developer": "Count the 1-hop outbound neighbors of error 'e1'.",
        "dba": "Get the outbound degree of node 'e1' in the 'error_causality' graph."
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 291,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS('database connection', 'text_en'), 'text_en') AND doc.level == 'ERROR' SORT BM25(doc) DESC LIMIT 10 RETURN doc",
      "description": "Find the most relevant ERROR logs about 'database connection'.",
      "english_variations": {
        "layperson": "Show me the most important errors about database connections.",
        "mba": "Prioritize critical database connectivity incidents based on relevance.",
        "developer": "Ranked full-text search for 'database connection' within ERROR level logs.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('database connection') AND level = 'ERROR' ORDER BY score DESC LIMIT 10"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 292,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN errors_search_view SEARCH ANALYZER(doc.message IN TOKENS('file not found', 'text_en'), 'text_en') RETURN doc",
      "description": "Search error messages for 'file not found'.",
      "english_variations": {
        "layperson": "Find errors about missing files.",
        "mba": "Search for incidents related to 'file not found' errors.",
        "developer": "Full-text search on error messages for 'file not found'.",
        "dba": "SELECT * FROM errors_search_view WHERE MATCH(message) AGAINST('file not found')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 293,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN lessons_search_view SEARCH PHRASE(doc.lesson, 'race condition', 'text_en') RETURN doc",
      "description": "Find lessons that contain the exact phrase 'race condition'.",
      "english_variations": {
        "layperson": "What have we learned about race conditions?",
        "mba": "Retrieve all knowledge base entries for the specific term 'race condition'.",
        "developer": "Phrase search for 'race condition' in lessons.",
        "dba": "SELECT * FROM lessons_search_view WHERE MATCH(lesson) AGAINST('\\\"race condition\\\"')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 294,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN all_text_view SEARCH ANALYZER(doc.text IN TOKENS('security', 'text_en'), 'text_en') AND doc.collection == 'errors_and_failures' RETURN doc",
      "description": "Search for 'security' specifically within error documents in a combined view.",
      "english_variations": {
        "layperson": "What security problems have we had?",
        "mba": "Isolate security-related incidents from the error logs.",
        "developer": "FTS for 'security' but filter results to the errors collection.",
        "dba": "SELECT * FROM all_text_view WHERE MATCH(text) AGAINST('security') AND collection = 'errors_and_failures'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 295,
      "category": "fulltext_search",
      "difficulty": "expert",
      "aql": "FOR doc IN log_search_view SEARCH BOOST(ANALYZER(doc.message IN TOKENS('timeout', 'text_en'), 'text_en'), 2) OR ANALYZER(doc.message IN TOKENS('connection', 'text_en'), 'text_en') SORT BM25(doc) DESC RETURN doc",
      "description": "Search for 'timeout' or 'connection', but give more weight to 'timeout'.",
      "english_variations": {
        "layperson": "Find connection problems, especially timeouts.",
        "mba": "Search for connectivity issues, prioritizing timeouts in the relevance ranking.",
        "developer": "FTS for 'timeout' or 'connection', boosting 'timeout'.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('timeout^2 connection') ORDER BY score DESC"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 296,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN definitions_view SEARCH STARTS_WITH(doc.definition, 'A pattern') RETURN doc",
      "description": "Find glossary definitions that start with the phrase 'A pattern'.",
      "english_variations": {
        "layperson": "Which terms describe a pattern?",
        "mba": "List all defined design patterns from the knowledge base.",
        "developer": "Prefix search for definitions starting with 'A pattern'.",
        "dba": "SELECT * FROM definitions_view WHERE MATCH(definition) AGAINST('A pattern*')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 297,
      "category": "fulltext_search",
      "difficulty": "expert",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS('disk', 'text_en'), 'text_en') AND NOT ANALYZER(doc.message IN TOKENS('virtual', 'text_en'), 'text_en') RETURN doc",
      "description": "Search for logs mentioning 'disk' but not 'virtual disk'.",
      "english_variations": {
        "layperson": "Find problems with physical disks, not virtual ones.",
        "mba": "Isolate logs related to physical disk issues by excluding mentions of 'virtual'.",
        "developer": "FTS for 'disk' but exclude 'virtual'.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('+disk -virtual' IN BOOLEAN MODE)"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 298,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN stack_trace_view SEARCH NGRAM_MATCH(doc.trace, 'NullPointerException', 0.8, 'trigram') RETURN doc",
      "description": "Find stack traces that are a close match to 'NullPointerException', allowing for typos.",
      "english_variations": {
        "layperson": "Find 'Null Pointer' errors, even if misspelled.",
        "mba": "Use fuzzy matching to find all instances of NullPointerExceptions, accommodating variations.",
        "developer": "Use NGRAM_MATCH for fuzzy search on stack traces.",
        "dba": "Perform a fuzzy search for 'NullPointerException' on the stack trace view."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 299,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN log_search_view SEARCH doc.level == 'CRITICAL' RETURN doc",
      "description": "Use the search view to filter for all CRITICAL logs.",
      "english_variations": {
        "layperson": "Show me all the critical alerts.",
        "mba": "Use the search index to retrieve all critical-level events.",
        "developer": "Filter on the 'level' attribute within the search view.",
        "dba": "SELECT * FROM log_search_view WHERE level = 'CRITICAL'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 300,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS('request failed', 'text_en'), 'text_en') SORT TFIDF(doc) DESC RETURN doc",
      "description": "Search for 'request failed' and rank by TF-IDF score.",
      "english_variations": {
        "layperson": "Find the most relevant 'request failed' logs.",
        "mba": "Prioritize 'request failed' incidents using TF-IDF relevance scoring.",
        "developer": "TF-IDF ranked search for 'request failed'.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('request failed') ORDER BY score(TFIDF) DESC"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 301,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN lessons_search_view SEARCH ANALYZER(doc.tags IN TOKENS('optimization', 'text_en'), 'text_en') RETURN doc",
      "description": "Search for lessons that have the 'optimization' tag.",
      "english_variations": {
        "layperson": "What lessons have we learned about optimization?",
        "mba": "Retrieve all knowledge base entries tagged with 'optimization'.",
        "developer": "FTS for the 'optimization' tag in lessons.",
        "dba": "SELECT * FROM lessons_search_view WHERE MATCH(tags) AGAINST('optimization')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 302,
      "category": "fulltext_search",
      "difficulty": "expert",
      "aql": "FOR doc IN all_text_view SEARCH IN_RANGE(doc.timestamp, '2025-06-01', '2025-06-30') AND ANALYZER(doc.text IN TOKENS('error', 'text_en'), 'text_en') RETURN doc",
      "description": "Search for the word 'error' in any text field, but only for documents created in June 2025.",
      "english_variations": {
        "layperson": "Find all mentions of 'error' from June.",
        "mba": "Isolate all 'error' mentions within the logs from June 2025.",
        "developer": "FTS for 'error' combined with a timestamp range filter.",
        "dba": "SELECT * FROM all_text_view WHERE MATCH(text) AGAINST('error') AND timestamp BETWEEN '2025-06-01' AND '2025-06-30'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 303,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.script_name == 'db_manager.py', 'text_en') RETURN doc",
      "description": "Use the search view to find all logs from a specific script.",
      "english_variations": {
        "layperson": "Find logs from the db_manager script.",
        "mba": "Use the search index to retrieve all logs from 'db_manager.py'.",
        "developer": "Exact match search on the script_name field in the view.",
        "dba": "SELECT * FROM log_search_view WHERE script_name = 'db_manager.py'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 304,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "LET keywords = ['performance', 'slow', 'bottleneck'] FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS(keywords, 'text_en'), 'text_en') RETURN doc",
      "description": "Search for any log message containing a list of performance-related keywords.",
      "english_variations": {
        "layperson": "Find any logs about performance issues.",
        "mba": "Search for logs indicating performance degradation using a set of keywords.",
        "developer": "FTS for any keyword in a predefined list.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('performance slow bottleneck')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 305,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN solutions_view SEARCH ANALYZER(doc.key_reason IN TOKENS('cache', 'text_en'), 'text_en') AND doc.outcome == 'success' RETURN doc",
      "description": "Find successful solutions that involved a 'cache'.",
      "english_variations": {
        "layperson": "Which successful solutions used a cache?",
        "mba": "Identify successful solution implementations involving caching.",
        "developer": "FTS for 'cache' in the reason, filtered by successful outcomes.",
        "dba": "SELECT * FROM solutions_view WHERE MATCH(key_reason) AGAINST('cache') AND outcome = 'success'"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 306,
      "category": "fulltext_search",
      "difficulty": "expert",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS('user', 'text_en'), 'text_en') AND ANALYZER(doc.message IN TOKENS('login', 'text_en'), 'text_en') AND ANALYZER(doc.message IN TOKENS('failed', 'text_en'), 'text_en') RETURN doc",
      "description": "Find logs that contain all three words: 'user', 'login', and 'failed'.",
      "english_variations": {
        "layperson": "Show me the failed user login logs.",
        "mba": "Search for logs indicating failed user login attempts.",
        "developer": "FTS for 'user' AND 'login' AND 'failed'.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('+user +login +failed' IN BOOLEAN MODE)"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 307,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN commands_view SEARCH ANALYZER(doc.command IN TOKENS('git push', 'text_en'), 'text_en') RETURN doc",
      "description": "Search for tool commands involving 'git push'.",
      "english_variations": {
        "layperson": "When did we 'git push'?",
        "mba": "Audit all instances of 'git push' commands.",
        "developer": "FTS for 'git push' in tool commands.",
        "dba": "SELECT * FROM commands_view WHERE MATCH(command) AGAINST('git push')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 308,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN all_text_view SEARCH doc.numeric_value > 5000 RETURN doc",
      "description": "Find any document in a view where a numeric field is over a certain threshold.",
      "english_variations": {
        "layperson": "Show me things with a value over 5000.",
        "mba": "Isolate all records with a key metric exceeding 5000.",
        "developer": "Filter by a numeric range within a search view.",
        "dba": "SELECT * FROM all_text_view WHERE numeric_value > 5000"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 309,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN error_search_view SEARCH ANALYZER(doc.message IN TOKENS('OOM', 'text_en'), 'text_en') OR ANALYZER(doc.message IN TOKENS('out of memory', 'text_en'), 'text_en') RETURN doc",
      "description": "Search for errors mentioning either 'OOM' or 'out of memory'.",
      "english_variations": {
        "layperson": "Find any memory errors.",
        "mba": "Search for all 'Out of Memory' related error incidents.",
        "developer": "FTS for 'OOM' OR 'out of memory'.",
        "dba": "SELECT * FROM error_search_view WHERE MATCH(message) AGAINST('OOM \\\"out of memory\\\"')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 310,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN log_search_view SEARCH PHRASE(doc.message, 'API key missing', 'text_en') RETURN doc",
      "description": "Find logs with the exact phrase 'API key missing'.",
      "english_variations": {
        "layperson": "Any logs about missing API keys?",
        "mba": "Search for authentication errors caused by missing API keys.",
        "developer": "Phrase search for 'API key missing'.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('\\\"API key missing\\\"')"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 311,
      "category": "fulltext_search",
      "difficulty": "expert",
      "aql": "FOR doc IN code_search_view SEARCH LEVENSHTEIN_MATCH(doc.content, 'autentication', 2, false) RETURN doc",
      "description": "Find the common misspelling 'autentication' in code, allowing for a Levenshtein distance of 2.",
      "english_variations": {
        "layperson": "Find typos of the word 'authentication'.",
        "mba": "Audit the codebase for common misspellings of critical terms.",
        "developer": "Use LEVENSHTEIN_MATCH to find misspellings of 'authentication'.",
        "dba": "Perform a Levenshtein distance search for 'autentication' in the code search view."
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 312,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS('404', 'text_en'), 'text_en') RETURN doc",
      "description": "Search for logs containing '404', which usually indicates a 'Not Found' error.",
      "english_variations": {
        "layperson": "Any 404 not found errors?",
        "mba": "Search for logs related to 404 HTTP errors.",
        "developer": "FTS for '404' in log messages.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('404')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 313,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN all_text_view SEARCH GEO_DISTANCE(doc.location, [-122.4, 37.7], 1000) RETURN doc",
      "description": "Find any document with a location within 1km of a specific geo-coordinate.",
      "english_variations": {
        "layperson": "Anything happen near this location?",
        "mba": "Perform a geo-spatial search for records within a 1km radius.",
        "developer": "Use a GEO_DISTANCE search in a view with a geo-index.",
        "dba": "SELECT * FROM all_text_view WHERE GEO_DISTANCE(location, [-122.4, 37.7]) < 1000"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 314,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS('shutdown', 'text_en'), 'text_en') AND doc.level == 'INFO' RETURN doc",
      "description": "Find all informational logs about system shutdowns.",
      "english_variations": {
        "layperson": "When were shutdowns announced?",
        "mba": "Audit all planned shutdown notifications from the logs.",
        "developer": "FTS for 'shutdown' in INFO level logs.",
        "dba": "SELECT * FROM log_search_view WHERE level = 'INFO' AND MATCH(message) AGAINST('shutdown')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 315,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN commands_view SEARCH ANALYZER(doc.command IN TOKENS('docker', 'text_en'), 'text_en') AND ANALYZER(doc.command IN TOKENS('build', 'text_en'), 'text_en') SORT BM25(doc) DESC RETURN doc",
      "description": "Search for 'docker build' commands and rank them by relevance.",
      "english_variations": {
        "layperson": "Show me the most relevant docker build commands.",
        "mba": "Analyze the usage of 'docker build' commands, ranked by relevance.",
        "developer": "Ranked FTS for 'docker' and 'build' in commands.",
        "dba": "SELECT * FROM commands_view WHERE MATCH(command) AGAINST('docker build') ORDER BY score DESC"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 316,
      "category": "fulltext_search",
      "difficulty": "expert",
      "aql": "FOR doc IN all_docs_view SEARCH ANALYZER(doc.content IN TOKENS('alpha', 'text_en'), 'text_en') OR ANALYZER(doc.content IN TOKENS('beta', 'text_en'), 'text_en') MIN_MATCH 1 RETURN doc",
      "description": "Search for documents containing 'alpha' or 'beta' using MIN_MATCH.",
      "english_variations": {
        "layperson": "Find anything about alpha or beta versions.",
        "mba": "Search for mentions of pre-release software versions ('alpha' or 'beta').",
        "developer": "FTS for 'alpha' OR 'beta' using MIN_MATCH.",
        "dba": "SELECT * FROM all_docs_view WHERE MATCH(content) AGAINST('alpha beta' WITH MIN_MATCH 1)"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 317,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS('throttling', 'text_en'), 'text_en') RETURN doc",
      "description": "Find logs that mention 'throttling'.",
      "english_variations": {
        "layperson": "Were we ever slowed down on purpose?",
        "mba": "Identify logs related to system throttling for performance analysis.",
        "developer": "FTS for 'throttling' in logs.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('throttling')"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 318,
      "category": "fulltext_search",
      "difficulty": "advanced",
      "aql": "FOR doc IN errors_search_view SEARCH ANALYZER(doc.error_type == 'SEGFAULT', 'text_en') RETURN doc",
      "description": "Find errors with the exact type 'SEGFAULT'.",
      "english_variations": {
        "layperson": "Any segmentation fault errors?",
        "mba": "Search for critical segmentation fault incidents.",
        "developer": "Exact match search for error_type 'SEGFAULT' in the view.",
        "dba": "SELECT * FROM errors_search_view WHERE error_type = 'SEGFAULT'"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 319,
      "category": "fulltext_search",
      "difficulty": "intermediate",
      "aql": "FOR doc IN solution_search_view SEARCH ANALYZER(doc.key_reason IN TOKENS('manual intervention', 'text_en'), 'text_en') RETURN doc",
      "description": "Find solutions that required 'manual intervention'.",
      "english_variations": {
        "layperson": "Which problems had to be fixed by a person?",
        "mba": "Identify solutions that required manual intervention, indicating automation gaps.",
        "developer": "FTS for 'manual intervention' in solution reasons.",
        "dba": "SELECT * FROM solution_search_view WHERE MATCH(key_reason) AGAINST('manual intervention')"
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 320,
      "category": "fulltext_search",
      "difficulty": "expert",
      "aql": "FOR doc IN log_search_view SEARCH ANALYZER(doc.message IN TOKENS('config', 'text_en'), 'text_en') AND ANALYZER(doc.message IN TOKENS('invalid', 'text_en'), 'text_en') AND doc.level IN ['ERROR', 'CRITICAL'] RETURN doc",
      "description": "Find high-severity logs about invalid configurations.",
      "english_variations": {
        "layperson": "Show me the critical errors about bad configs.",
        "mba": "Isolate high-severity incidents caused by invalid configurations.",
        "developer": "FTS for 'config' and 'invalid' in ERROR or CRITICAL logs.",
        "dba": "SELECT * FROM log_search_view WHERE MATCH(message) AGAINST('+config +invalid') AND level IN ['ERROR', 'CRITICAL']"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 321,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR agent IN agent_sessions COLLECT agentName = agent.agent_name WITH COUNT INTO sessionCount LET totalDuration = SUM(FOR s IN agent_sessions FILTER s.agent_name == agentName RETURN s.duration_ms) FILTER sessionCount > 1 RETURN { agentName, sessionCount, avgDuration: totalDuration / sessionCount }",
      "description": "For each agent with more than one session, calculate their average session duration.",
      "english_variations": {
        "layperson": "Which agents have the longest average work time?",
        "mba": "Analyze agent efficiency by calculating average session duration for agents with significant activity.",
        "developer": "Calculate average session duration per agent, for agents with multiple sessions.",
        "dba": "SELECT agent_name, COUNT(*), AVG(duration_ms) FROM agent_sessions GROUP BY agent_name HAVING COUNT(*) > 1"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 322,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR tool IN tool_executions FILTER tool.status == 'failed' LET error_messages = (FOR e IN errors_and_failures FILTER e.session_id == tool.session_id RETURN e.message) FILTER LENGTH(error_messages) > 0 RETURN { tool_name: tool.tool_name, command: tool.command, associated_errors: error_messages }",
      "description": "For each failed tool, list the error messages from the same session.",
      "english_variations": {
        "layperson": "When a tool failed, what were the error messages?",
        "mba": "Correlate failed tool executions with associated error messages for root cause analysis.",
        "developer": "Join failed tools with errors from the same session and list the messages.",
        "dba": "SELECT t.tool_name, t.command, ARRAY_AGG(e.message) FROM tool_executions t JOIN errors_and_failures e ON t.session_id = e.session_id WHERE t.status = 'failed' GROUP BY t._key"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 323,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR l IN lessons_learned LET related_solutions = (FOR s IN solution_outcomes FILTER CONTAINS(s.key_reason, l.lesson) AND s.outcome == 'success' RETURN s._key) FILTER LENGTH(related_solutions) > 0 RETURN { lesson: l.lesson, successful_applications: LENGTH(related_solutions) }",
      "description": "Find lessons that have been cited in the reason for successful solutions.",
      "english_variations": {
        "layperson": "Which lessons have led to successful fixes?",
        "mba": "Validate the effectiveness of learned lessons by correlating them with successful solution outcomes.",
        "developer": "Join lessons to successful solutions where the lesson text is in the solution's reason.",
        "dba": "Find lessons whose text appears in the key_reason of successful solution_outcomes."
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 324,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR session IN agent_sessions LET python_artifacts = (FOR a IN code_artifacts FILTER a.session_id == session.session_id AND a.language == 'Python' RETURN a.size) LET js_artifacts = (FOR a IN code_artifacts FILTER a.session_id == session.session_id AND a.language == 'JavaScript' RETURN a.size) FILTER LENGTH(python_artifacts) > 0 AND LENGTH(js_artifacts) > 0 RETURN { session_id: session.session_id, total_python_size: SUM(python_artifacts), total_js_size: SUM(js_artifacts) }",
      "description": "Find sessions that produced both Python and JavaScript code, and show the total size for each.",
      "english_variations": {
        "layperson": "Which sessions worked on both Python and JavaScript?",
        "mba": "Analyze polyglot sessions involving both Python and JavaScript development.",
        "developer": "Find sessions that produced artifacts in both Python and JS, and sum the sizes.",
        "dba": "Complex join to find sessions with artifacts in two different languages."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 325,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR error in errors_and_failures FILTER error.resolved == false LET session_agent = (FOR s IN agent_sessions FILTER s.session_id == error.session_id RETURN s.agent_name)[0] RETURN { error_message: error.message, agent: session_agent }",
      "description": "For each unresolved error, show which agent was running the session.",
      "english_variations": {
        "layperson": "Which agents are responsible for the current open problems?",
        "mba": "Attribute unresolved errors to the responsible agent for performance tracking.",
        "developer": "Join unresolved errors with their session to get the agent's name.",
        "dba": "SELECT e.message, s.agent_name FROM errors_and_failures e JOIN agent_sessions s ON e.session_id = s.session_id WHERE e.resolved = FALSE"
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 326,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR g IN glossary_terms LET error_types = UNIQUE(FOR e IN errors_and_failures FILTER g.term IN e.tags RETURN e.error_type) FILTER LENGTH(error_types) > 0 RETURN { term: g.term, related_error_types: error_types }",
      "description": "For each glossary term, list all the unique error types it has been tagged with.",
      "english_variations": {
        "layperson": "What kinds of errors are related to each term?",
        "mba": "Map knowledge base concepts to the error types they are associated with.",
        "developer": "For each term, find all unique error types from errors tagged with that term.",
        "dba": "Join glossary terms to errors via a shared tag and aggregate the unique error types."
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 327,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "LET slow_sessions = (FOR t IN tool_executions FILTER t.duration_ms > 10000 RETURN DISTINCT t.session_id) FOR session_id IN slow_sessions FOR s IN agent_sessions FILTER s.session_id == session_id RETURN { session: s, reason: 'Contained a slow tool execution' }",
      "description": "Get full session details for any session that contained at least one tool execution longer than 10 seconds.",
      "english_variations": {
        "layperson": "Show me the sessions that had slow tools in them.",
        "mba": "Analyze sessions impacted by slow tool performance.",
        "developer": "Find sessions containing a tool run longer than 10s.",
        "dba": "Find sessions whose IDs are in the set of sessions with slow tools."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 328,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR s IN solution_outcomes FILTER s.outcome == 'failed' LET session_info = DOCUMENT('agent_sessions', s.session_id) LET errors_in_session = (FOR e IN errors_and_failures FILTER e.session_id == s.session_id RETURN e.message) RETURN { solution_reason: s.key_reason, agent: session_info.agent_name, errors: errors_in_session }",
      "description": "For failed solutions, show the agent involved and the errors that occurred in that session.",
      "english_variations": {
        "layperson": "When a solution failed, who was involved and what went wrong?",
        "mba": "Conduct a post-mortem on failed solutions by correlating them with session agent and error data.",
        "developer": "For failed solutions, join to sessions and errors to get related data.",
        "dba": "Join failed solutions to sessions and errors using DOCUMENT() and a subquery."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 329,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR tool IN tool_executions COLLECT tool_name = tool.tool_name INTO g LET total_duration = SUM(g[*].tool.duration_ms) LET total_runs = COUNT(g) FILTER total_runs > 5 RETURN { tool_name, avg_duration: total_duration / total_runs }",
      "description": "Calculate the average run time for tools that have been used more than 5 times.",
      "english_variations": {
        "layperson": "What's the average speed of our frequently used tools?",
        "mba": "Analyze the average performance of commonly used tools.",
        "developer": "Calculate average duration for tools with more than 5 executions.",
        "dba": "SELECT tool_name, AVG(duration_ms) FROM tool_executions GROUP BY tool_name HAVING COUNT(*) > 5"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 330,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR a IN agent_sessions LET errors = (FOR e IN errors_and_failures FILTER e.session_id == a.session_id RETURN 1) LET tools = (FOR t IN tool_executions FILTER t.session_id == a.session_id RETURN 1) FILTER LENGTH(errors) > 0 RETURN { session_id: a.session_id, error_to_tool_ratio: LENGTH(errors) / LENGTH(tools) }",
      "description": "For sessions with errors, calculate the ratio of errors to tool executions.",
      "english_variations": {
        "layperson": "In sessions with problems, how many errors happen per tool run?",
        "mba": "Calculate the error-to-tool-usage ratio as a KPI for session stability.",
        "developer": "For each session, calculate the ratio of its error count to its tool count.",
        "dba": "Complex join and calculation of error/tool ratio per session."
      },
      "expected_result_type": "aggregated",
      "visualization": "scatter_plot"
    },
    {
      "id": 331,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR artifact IN code_artifacts LET session_status = (FOR s IN agent_sessions FILTER s.session_id == artifact.session_id RETURN s.status)[0] COLLECT language = artifact.language, status = session_status WITH COUNT INTO count RETURN { language, session_status: status, count }",
      "description": "Count how many artifacts of each language were produced in successful vs. failed sessions.",
      "english_variations": {
        "layperson": "Do successful sessions produce more of a certain type of file?",
        "mba": "Correlate artifact language with session outcome status.",
        "developer": "Group artifacts by language and their session's status, then count.",
        "dba": "Join artifacts to sessions, then group by language and status to get counts."
      },
      "expected_result_type": "aggregated",
      "visualization": "heatmap"
    },
    {
      "id": 332,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR tool_name IN (FOR t IN tool_executions RETURN DISTINCT t.tool_name) LET success_durations = (FOR t IN tool_executions FILTER t.tool_name == tool_name AND t.status == 'success' RETURN t.duration_ms) LET failed_durations = (FOR t IN tool_executions FILTER t.tool_name == tool_name AND t.status == 'failed' RETURN t.duration_ms) RETURN { tool_name, avg_success_duration: AVERAGE(success_durations), avg_failed_duration: AVERAGE(failed_durations) }",
      "description": "For each tool, compare the average duration of its successful runs vs. its failed runs.",
      "english_variations": {
        "layperson": "Do tools take longer when they are about to fail?",
        "mba": "Compare average execution times for successful vs. failed tool runs to find performance indicators of failure.",
        "developer": "For each tool, calculate average duration for success and fail statuses separately.",
        "dba": "Use conditional aggregation to get average durations for different statuses for each tool."
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 333,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR e IN errors_and_failures WHERE e.resolved == true AND e.resolution != null LET lesson = (FOR l in lessons_learned FILTER CONTAINS(e.resolution, l.lesson) RETURN l) FILTER LENGTH(lesson) > 0 RETURN { error: e.message, applied_lesson: lesson[0].lesson }",
      "description": "Find resolved errors where the resolution matches a known lesson.",
      "english_variations": {
        "layperson": "Which problems were fixed using a lesson we already learned?",
        "mba": "Identify instances where the knowledge base was successfully applied to resolve errors.",
        "developer": "Join resolved errors to lessons where the resolution text contains the lesson text.",
        "dba": "Find errors whose resolution text contains text from the lessons_learned collection."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 334,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR day IN 0..6 LET target_date = DATE_FORMAT(DATE_SUBTRACT(DATE_NOW(), day, 'day'), '%Y-%m-%d') LET daily_errors = COUNT(FOR e IN errors_and_failures FILTER DATE_FORMAT(e.timestamp, '%Y-%m-%d') == target_date RETURN 1) LET daily_sessions = COUNT(FOR s IN agent_sessions FILTER DATE_FORMAT(s.start_time, '%Y-%m-%d') == target_date RETURN 1) RETURN { date: target_date, error_per_session: daily_errors / (daily_sessions > 0 ? daily_sessions : 1) }",
      "description": "Calculate the daily errors-per-session rate for the last 7 days.",
      "english_variations": {
        "layperson": "Are we getting more errors per work session recently?",
        "mba": "Track the daily errors-per-session KPI to measure overall system reliability trends.",
        "developer": "For the last 7 days, calculate the ratio of daily errors to daily sessions.",
        "dba": "Complex daily aggregation of two collections to calculate a ratio."
      },
      "expected_result_type": "aggregated",
      "visualization": "line_chart"
    },
    {
      "id": 335,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR agent_name IN (FOR s IN agent_sessions RETURN DISTINCT s.agent_name) LET tools_used = UNIQUE(FOR t IN tool_executions JOIN s IN agent_sessions ON t.session_id == s.session_id WHERE s.agent_name == agent_name RETURN t.tool_name) RETURN { agent: agent_name, unique_tools_used: tools_used, tool_count: LENGTH(tools_used) }",
      "description": "For each agent, list all the unique tools they have ever used.",
      "english_variations": {
        "layperson": "What are all the different tools each agent knows how to use?",
        "mba": "Analyze the tool proficiency and diversity for each agent.",
        "developer": "For each agent, get the unique set of tools they've used across all sessions.",
        "dba": "Join sessions and tools, then group by agent to get the unique list of tools."
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 336,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR e in errors_and_failures LET session_tools = (FOR t in tool_executions FILTER t.session_id == e.session_id RETURN t.tool_name) FILTER 'linter' IN session_tools AND 'compiler' IN session_tools RETURN e",
      "description": "Find errors that occurred in sessions where both a linter and a compiler were used.",
      "english_variations": {
        "layperson": "Which errors happened during a lint-and-compile workflow?",
        "mba": "Isolate errors occurring in sessions that involve both static analysis and compilation steps.",
        "developer": "Find errors from sessions where both 'linter' and 'compiler' tools were used.",
        "dba": "Find errors whose session_id is associated with executions of both 'linter' and 'compiler'."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 337,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR s in solution_outcomes COLLECT cat = s.category INTO g RETURN { category: cat, score_variance: VARIANCE(g[*].s.success_score) }",
      "description": "Calculate the variance of success scores within each solution category.",
      "english_variations": {
        "layperson": "How consistent are the results for each type of solution?",
        "mba": "Analyze the variance in success scores to understand the consistency of outcomes for each solution category.",
        "developer": "Calculate the variance of success_score, grouped by category.",
        "dba": "SELECT category, VARIANCE(success_score) FROM solution_outcomes GROUP BY category"
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 338,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "LET high_confidence_lessons = (FOR l IN lessons_learned FILTER l.confidence > 0.9 RETURN l.lesson) FOR s IN solution_outcomes FILTER s.key_reason IN high_confidence_lessons RETURN s",
      "description": "Find solutions that were based on high-confidence lessons.",
      "english_variations": {
        "layperson": "Which solutions were based on things we are very sure about?",
        "mba": "Identify solutions derived from high-confidence best practices in the knowledge base.",
        "developer": "Find solutions where the key_reason is one of the high-confidence lessons.",
        "dba": "Find solutions whose key_reason is in the set of high-confidence lessons."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 339,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR t IN tool_executions LET session_agent = DOCUMENT(CONCAT('agent_sessions/', t.session_id)).agent_name COLLECT agent = session_agent, tool = t.tool_name WITH COUNT INTO usage_count RETURN {agent, tool, usage_count}",
      "description": "Create a matrix of which agents use which tools and how often.",
      "english_variations": {
        "layperson": "Show me a breakdown of which agent uses which tool.",
        "mba": "Generate a usage matrix of agents and tools for capability analysis.",
        "developer": "Count tool usage, grouped by agent and tool name.",
        "dba": "Join tools to sessions, then group by agent and tool to get counts."
      },
      "expected_result_type": "aggregated",
      "visualization": "heatmap"
    },
    {
      "id": 340,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR a IN code_artifacts FILTER a.operation == 'modify' LET error_count = COUNT(FOR e IN errors_and_failures FILTER e.session_id == a.session_id) FILTER error_count > 0 RETURN { file_path: a.file_path, errors_in_session: error_count }",
      "description": "For modified files, show how many errors occurred in the session they were modified in.",
      "english_variations": {
        "layperson": "When files were changed, how many errors happened at the same time?",
        "mba": "Correlate code modifications with error counts in the same session to assess change risk.",
        "developer": "For modified artifacts, count the errors in their parent session.",
        "dba": "Join modified artifacts with a count of errors from the same session."
      },
      "expected_result_type": "aggregated",
      "visualization": "table"
    },
    {
      "id": 341,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR s IN agent_sessions FILTER s.status == 'timeout' LET last_tool = (FOR t in tool_executions FILTER t.session_id == s.session_id SORT t.start_time DESC LIMIT 1 RETURN t.tool_name)[0] RETURN { session_id: s.session_id, last_tool_before_timeout: last_tool }",
      "description": "For sessions that timed out, what was the last tool they were trying to use?",
      "english_variations": {
        "layperson": "When a session timed out, what was it doing?",
        "mba": "Identify the last tool used in timed-out sessions to investigate causes of session hangs.",
        "developer": "For timed-out sessions, find the last tool executed.",
        "dba": "Join timed-out sessions with the last tool from their execution history."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 342,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR e1 IN errors_and_failures FOR e2 IN errors_and_failures FILTER e1.session_id == e2.session_id AND e1.error_type == 'TimeoutError' AND e2.error_type == 'DatabaseConnectionError' RETURN { session_id: e1.session_id }",
      "description": "Find sessions that experienced both a TimeoutError and a DatabaseConnectionError.",
      "english_variations": {
        "layperson": "Which sessions had both timeout and database connection problems?",
        "mba": "Identify sessions affected by a combination of timeout and database connectivity issues.",
        "developer": "Find sessions that contain both a TimeoutError and a DatabaseConnectionError.",
        "dba": "Self-join errors on session_id to find sessions with a specific combination of error types."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 343,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "LET python_errors = (FOR e IN errors_and_failures LET artifact_lang = (FOR a IN code_artifacts FILTER a.session_id == e.session_id RETURN a.language)[0] FILTER artifact_lang == 'Python' RETURN e) RETURN COUNT(python_errors)",
      "description": "Count the number of errors that occurred in sessions that worked on Python code.",
      "english_variations": {
        "layperson": "How many errors happened during Python work?",
        "mba": "Quantify the number of errors associated with Python development sessions.",
        "developer": "Count errors from sessions that touched Python files.",
        "dba": "Count errors where the session_id is associated with a Python code artifact."
      },
      "expected_result_type": "single_value",
      "visualization": "text"
    },
    {
      "id": 344,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR g IN glossary_terms LET usage_in_errors = COUNT(FOR e IN errors_and_failures FILTER CONTAINS(e.message, g.term) RETURN 1) LET usage_in_lessons = COUNT(FOR l IN lessons_learned FILTER CONTAINS(l.lesson, g.term) RETURN 1) RETURN {term: g.term, error_mentions: usage_in_errors, lesson_mentions: usage_in_lessons}",
      "description": "For each glossary term, count its mentions in error messages vs. in lessons learned.",
      "english_variations": {
        "layperson": "Are terms mentioned more in problems or in solutions?",
        "mba": "Compare the usage of terminology in problem descriptions versus in the knowledge base.",
        "developer": "For each term, count its occurrences in error messages and lesson texts.",
        "dba": "Perform multiple subqueries to count term mentions across different collections."
      },
      "expected_result_type": "aggregated",
      "visualization": "scatter_plot"
    },
    {
      "id": 345,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR s IN agent_sessions LET session_log_levels = UNIQUE(FOR log IN log_events FILTER log.session_id == s.session_id RETURN log.level) FILTER 'CRITICAL' IN session_log_levels AND 'DEBUG' NOT IN session_log_levels RETURN s",
      "description": "Find sessions that have critical logs but are missing any debug logs, which might indicate a logging failure.",
      "english_variations": {
        "layperson": "Which critical problems have no debug info?",
        "mba": "Identify critical incidents with insufficient diagnostic logging.",
        "developer": "Find sessions with CRITICAL logs but no DEBUG logs.",
        "dba": "Find sessions containing a 'CRITICAL' log level but not a 'DEBUG' log level."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 346,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR u IN (FOR t IN tool_executions RETURN DISTINCT t.tool_name) LET last_used = MAX(FOR t IN tool_executions FILTER t.tool_name == u RETURN t.start_time) FILTER last_used < DATE_SUBTRACT(DATE_NOW(), 90, 'day') RETURN { tool: u, last_used: last_used }",
      "description": "Find tools that have not been used in the last 90 days.",
      "english_variations": {
        "layperson": "Which tools haven't we used in a while?",
        "mba": "Identify unused tools in the toolchain for potential deprecation.",
        "developer": "Find tools whose last execution was more than 90 days ago.",
        "dba": "For each tool, find its max start_time and filter those older than 90 days."
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 347,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "LET total_size_by_lang = (FOR a in code_artifacts COLLECT lang = a.language INTO g RETURN { language: lang, total_size: SUM(g[*].a.size) }) FOR item in total_size_by_lang SORT item.total_size DESC LIMIT 1 RETURN item",
      "description": "Find the language that takes up the most space in the codebase.",
      "english_variations": {
        "layperson": "Which programming language do we have the most code in?",
        "mba": "Identify the language with the largest footprint in the codebase for resource allocation.",
        "developer": "Find the language with the maximum total artifact size.",
        "dba": "SELECT language, SUM(size) as s FROM code_artifacts GROUP BY language ORDER BY s DESC LIMIT 1"
      },
      "expected_result_type": "aggregated",
      "visualization": "text"
    },
    {
      "id": 348,
      "category": "complex_join",
      "difficulty": "expert",
      "aql": "FOR e IN errors_and_failures LET next_error_time = MIN(FOR e2 IN errors_and_failures FILTER e2.timestamp > e.timestamp RETURN e2.timestamp) FILTER next_error_time != null RETURN { current_error_time: e.timestamp, time_until_next_error_seconds: DATE_DIFF(next_error_time, e.timestamp, 's') }",
      "description": "Calculate the time between each consecutive error.",
      "english_variations": {
        "layperson": "How long do we usually go between errors?",
        "mba": "Analyze the Mean Time Between Failures (MTBF) by calculating the delta between consecutive errors.",
        "developer": "For each error, find the next one and calculate the time difference.",
        "dba": "Use a correlated subquery with a LEAD window function concept to find time between errors."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "line_chart"
    },
    {
      "id": 349,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR s IN agent_sessions LET error_count = COUNT(FOR e IN errors_and_failures FILTER e.session_id == s.session_id RETURN 1) SORT error_count DESC LIMIT 1 RETURN DOCUMENT(s._id)",
      "description": "Return the full session document for the session with the most errors.",
      "english_variations": {
        "layperson": "Show me all the details for the most problematic session.",
        "mba": "Retrieve the complete record for the session with the highest incident count.",
        "developer": "Get the session document that has the highest number of associated errors.",
        "dba": "Find the session_id with the most errors, then select that full document."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 350,
      "category": "complex_join",
      "difficulty": "advanced",
      "aql": "FOR l IN lessons_learned LET implementation_count = COUNT(FOR s IN solution_outcomes FILTER CONTAINS(s.key_reason, l.lesson) RETURN 1) RETURN { lesson: l.lesson, implementation_count }",
      "description": "For each lesson, count how many solutions have implemented it.",
      "english_variations": {
        "layperson": "How many times has each lesson been used to fix something?",
        "mba": "Measure the adoption rate of learned lessons in solution implementations.",
        "developer": "For each lesson, count how many solutions mention it in their reason.",
        "dba": "For each lesson, count its mentions in the solution_outcomes collection."
      },
      "expected_result_type": "aggregated",
      "visualization": "bar_chart"
    },
    {
      "id": 351,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR session IN agent_sessions LET tools = (FOR t IN tool_executions FILTER t.session_id == session.session_id SORT t.start_time RETURN t.tool_name) FILTER tools[0] == 'git' AND tools[-1] == 'pytest' AND session.status == 'completed' RETURN session.session_id",
      "description": "Find successful sessions that followed a 'git -> ... -> pytest' tool usage pattern.",
      "english_variations": {
        "layperson": "Which work sessions successfully tested code they just pulled?",
        "mba": "Identify successful 'fetch-then-test' workflow patterns for process optimization.",
        "developer": "Mine for sessions that start with 'git', end with 'pytest', and succeed.",
        "dba": "Pattern query to find sessions matching a specific sequence of tool executions."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 352,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR e1 IN errors_and_failures FOR e2 IN errors_and_failures FILTER e1.session_id == e2.session_id AND e1.error_type == e2.error_type AND e1._key < e2._key RETURN { session_id: e1.session_id, repeated_error: e1.error_type }",
      "description": "Find sessions where the same error type occurred more than once.",
      "english_variations": {
        "layperson": "Which sessions had the same error happen over and over?",
        "mba": "Identify recurring error patterns within a single session.",
        "developer": "Find sessions containing duplicate error types.",
        "dba": "Self-join errors on session_id and error_type to find repetitions."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 353,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR t IN tool_executions FILTER t.status == 'failed' LET preceding_tool = (FOR t2 IN tool_executions FILTER t2.session_id == t.session_id AND t2.start_time < t.start_time SORT t2.start_time DESC LIMIT 1 RETURN t2.tool_name)[0] FILTER preceding_tool != null COLLECT failing_tool = t.tool_name, prior_tool = preceding_tool WITH COUNT INTO count RETURN { prior_tool, failing_tool, count }",
      "description": "Find which tools most frequently precede a failure of another tool.",
      "english_variations": {
        "layperson": "What tool is usually run right before another tool fails?",
        "mba": "Analyze tool-pair failure correlation to identify problematic workflows.",
        "developer": "Find common tool sequences that end in failure.",
        "dba": "Mine for sequential patterns of (tool_A -> tool_B_fails)."
      },
      "expected_result_type": "aggregated",
      "visualization": "heatmap"
    },
    {
      "id": 354,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR s IN agent_sessions LET tool_count = COUNT(FOR t IN tool_executions FILTER t.session_id == s.session_id RETURN 1) LET error_count = COUNT(FOR e IN errors_and_failures FILTER e.session_id == s.session_id RETURN 1) FILTER tool_count > 10 AND error_count == 0 RETURN s",
      "description": "Identify 'golden path' sessions: those with many tool executions and zero errors.",
      "english_variations": {
        "layperson": "Show me long, complex sessions that went perfectly.",
        "mba": "Identify highly successful, complex sessions as examples of ideal workflows.",
        "developer": "Find sessions with > 10 tools and 0 errors.",
        "dba": "Pattern query to find sessions with high tool count and zero errors."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 355,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR e IN errors_and_failures FILTER e.resolved == false LET similar_resolved = (FOR e2 IN errors_and_failures FILTER e2.resolved == true AND e2.error_type == e.error_type RETURN e2.resolution) FILTER LENGTH(similar_resolved) > 0 RETURN { unresolved_error: e.message, suggested_resolution: similar_resolved[0] }",
      "description": "For unresolved errors, find a suggested resolution from a previously resolved error of the same type.",
      "english_variations": {
        "layperson": "For this open problem, how did we fix a similar one before?",
        "mba": "Leverage historical resolution data to suggest fixes for open incidents.",
        "developer": "Find a resolution for an open error by matching with a past resolved error of the same type.",
        "dba": "Pattern query to find resolutions for open errors based on historical data."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 356,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR s IN agent_sessions LET has_large_artifact = LENGTH(FOR a IN code_artifacts FILTER a.session_id == s.session_id AND a.size > 100000 RETURN 1) > 0 LET has_timeout_error = LENGTH(FOR e IN errors_and_failures FILTER e.session_id == s.session_id AND e.error_type == 'TimeoutError' RETURN 1) > 0 FILTER has_large_artifact AND has_timeout_error RETURN s",
      "description": "Find a pattern of sessions that produce a large artifact and also have a timeout error.",
      "english_variations": {
        "layperson": "Do large files cause timeouts?",
        "mba": "Correlate the generation of large artifacts with the occurrence of timeout errors.",
        "developer": "Find sessions that both created a file > 100KB and had a TimeoutError.",
        "dba": "Pattern query for sessions matching two distinct criteria in linked collections."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 357,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR l in lessons_learned FILTER l.confidence < 0.6 LET conflicting_lesson = (FOR l2 in lessons_learned FILTER l2.category == l.category AND l2.confidence > 0.9 RETURN l2.lesson) FILTER LENGTH(conflicting_lesson) > 0 RETURN { low_confidence_lesson: l.lesson, conflicting_high_confidence_lesson: conflicting_lesson[0] }",
      "description": "Find low-confidence lessons that may conflict with a high-confidence lesson in the same category.",
      "english_variations": {
        "layperson": "Are there any lessons that contradict each other?",
        "mba": "Identify potential conflicts in the knowledge base by comparing low- and high-confidence lessons.",
        "developer": "Find low-confidence lessons that have a high-confidence counterpart in the same category.",
        "dba": "Self-join lessons to find potential contradictions based on confidence scores."
      },
      "expected_result_type": "empty",
      "visualization": "none"
    },
    {
      "id": 358,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR tool in tool_executions FILTER tool.exit_code != 0 LET preceding_commands = (FOR t2 IN tool_executions FILTER t2.session_id == tool.session_id AND t2.start_time < tool.start_time SORT t2.start_time RETURN {cmd: t2.command, status: t2.status}) RETURN { failing_command: tool.command, history: preceding_commands }",
      "description": "For each failing command, show the history of commands that came before it in the same session.",
      "english_variations": {
        "layperson": "When a command failed, what was done just before it?",
        "mba": "Analyze the command history preceding tool failures to understand the context of the failure.",
        "developer": "For each failed tool, get the sequence of preceding commands in that session.",
        "dba": "For each failed tool, query the history of commands within its session."
      },
      "expected_result_type": "multiple_rows",
      "visualization": "table"
    },
    {
      "id": 359,
      "category": "pattern_mining",
      "difficulty": "expert",
      "aql": "FOR a1 IN code_artifacts FOR a2 IN code_artifacts FILTER a1.session_id == a2.session_id AND a1.file_path == a2.file_path AND a1.operation == 'create' AND a2.operation