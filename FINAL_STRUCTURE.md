# CC Executor Final Structure

## Directory Organization

```
src/cc_executor/
├── core/                      # Essential WebSocket service only
│   ├── __init__.py
│   ├── main.py               # FastAPI entry
│   ├── config.py             # Configuration
│   ├── models.py             # Data models
│   ├── session_manager.py    # Session management
│   ├── process_manager.py    # Process control
│   ├── stream_handler.py     # Stream handling
│   ├── websocket_handler.py  # WebSocket protocol
│   ├── resource_monitor.py   # Resource monitoring
│   └── prompts/              # Assessment prompts
│       ├── ASSESS_ALL_CORE_USAGE.md
│       ├── scripts/          # Python scripts for prompts
│       │   └── assess_all_core_usage.py
│       ├── reports/          # Generated reports
│       └── tmp/              # Temporary files
│
├── hooks/                     # All hook-related code
│   ├── [hook files...]
│   ├── hook_enforcement.py   # From core/
│   ├── hook_integration.py   # From core/
│   └── prompts/              # Assessment prompts
│       ├── ASSESS_ALL_HOOKS_USAGE.md
│       ├── scripts/
│       ├── reports/
│       └── tmp/
│
├── cli/                       # CLI interface
│   ├── __init__.py
│   ├── main.py
│   └── prompts/              # Assessment prompts
│       ├── ASSESS_ALL_CLI_USAGE.md
│       ├── scripts/
│       ├── reports/
│       └── tmp/
│
├── utils/                     # Helper utilities
│   ├── timeout_recovery_manager.py
│   ├── enhanced_timeout_calculator.py
│   ├── smart_timeout_defaults.py
│   ├── enhanced_prompt_classifier.py
│   ├── redis_similarity_search.py
│   ├── concurrent_executor.py
│   ├── reflection_parser.py
│   └── usage_helper.py
│
├── client/                    # WebSocket client
│   └── client.py
│
├── examples/                  # Example usage
│   ├── factorial.py
│   └── simple_example.py
│
└── prompts/                   # Other prompts
    └── cc_execute.py
```

## Key Benefits

1. **Clean Separation**: Each directory has a single, clear purpose
2. **Self-Contained Testing**: Each major component has its own `prompts/` subdirectory
3. **No Code Extraction Issues**: Python scripts are separate from markdown prompts
4. **Organized Reports**: Reports saved in `prompts/reports/` not cluttering main directories
5. **Temporary Files**: Each component has its own `prompts/tmp/` for testing artifacts

## Assessment Structure

For each component (core, cli, hooks):
- `prompts/ASSESS_ALL_*_USAGE.md` - Self-improving prompt documentation
- `prompts/scripts/assess_all_*_usage.py` - Actual Python code to run
- `prompts/reports/` - Generated assessment reports
- `prompts/tmp/` - Temporary files during testing

This structure avoids the common issue where agents struggle to extract Python code from markdown files.