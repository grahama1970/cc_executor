# Core Directory Analysis and Restructuring Plan

## Current State Analysis

### Core Directory Structure Issues

1. **Mixed Concerns**: The core directory contains:
   - Essential WebSocket service files (9 files)
   - Hook-related files that belong in hooks/ (2 files)
   - Helper utilities with unclear placement (9 files)
   - Test/example/documentation files (8 files)

2. **Assessment Prompt vs Reality**:
   - The ASSESS_ALL_CORE_USAGE.md tests 14 components
   - But the actual core has 21+ Python files
   - Some tested components don't exist (e.g., factorial.py is tested but shouldn't be core)

### File Categorization

#### ESSENTIAL Core Files (Keep in core/)
1. **main.py** - FastAPI WebSocket service entry point
2. **config.py** - Configuration and environment variables
3. **models.py** - Pydantic models for JSON-RPC
4. **session_manager.py** - WebSocket session lifecycle
5. **process_manager.py** - Process execution/control
6. **stream_handler.py** - Output streaming with back-pressure
7. **websocket_handler.py** - WebSocket protocol/routing
8. **resource_monitor.py** - System resource monitoring
9. **__init__.py** - Package initialization

#### MOVE to hooks/
1. **hook_enforcement.py** - Hook workaround implementation
2. **hook_integration.py** - Hook system configuration

#### QUESTIONABLE Placement (Need decision)
1. **client.py** - WebSocket client (maybe client/ directory?)
2. **timeout_recovery_manager.py** - Timeout strategies
3. **enhanced_timeout_calculator.py** - Dynamic timeouts
4. **smart_timeout_defaults.py** - Intelligent defaults
5. **enhanced_prompt_classifier.py** - Prompt classification
6. **redis_similarity_search.py** - Redis similarity
7. **concurrent_executor.py** - Parallel execution
8. **reflection_parser.py** - Parse reflection blocks
9. **usage_helper.py** - Usage capture utility

#### REMOVE from core/
1. **factorial.py** - Example file
2. **simple_example.py** - Example usage
3. **run_with_hooks.py** - Duplicate of hook_integration
4. **assess_all_core_usage.py** - Assessment script
5. **ASSESS_ALL_CORE_USAGE.md** - Self-improving prompt
6. **CORE_COMPONENTS_TEST_SUMMARY.md** - Documentation
7. **README.md** - Documentation
8. **reports/** - Test reports directory

## Recommended Structure

### Option 1: Minimal Core (Recommended)
```
src/cc_executor/
├── core/                      # Only WebSocket service essentials
│   ├── __init__.py
│   ├── main.py               # FastAPI entry
│   ├── config.py             # Configuration
│   ├── models.py             # Data models
│   ├── session_manager.py    # Session management
│   ├── process_manager.py    # Process control
│   ├── stream_handler.py     # Stream handling
│   ├── websocket_handler.py  # WebSocket protocol
│   ├── resource_monitor.py   # Resource monitoring
│   └── ASSESS_ALL_CORE_USAGE.md  # Self-improving prompt
│
├── hooks/                     # All hook-related code
│   ├── hook_enforcement.py   # From core/
│   ├── hook_integration.py   # From core/
│   └── [existing hooks]
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
├── client/                    # Client code
│   └── client.py
│
└── examples/                  # Examples
    ├── factorial.py
    └── simple_example.py
```

### Option 2: Keep Utilities in Core
```
src/cc_executor/
├── core/                      # WebSocket service + related utilities
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── session_manager.py
│   ├── process_manager.py
│   ├── stream_handler.py
│   ├── websocket_handler.py
│   ├── resource_monitor.py
│   ├── timeout_recovery_manager.py    # Keep timeout utilities
│   ├── enhanced_timeout_calculator.py
│   ├── smart_timeout_defaults.py
│   ├── client.py                      # Keep client here
│   └── ASSESS_ALL_CORE_USAGE.md
│
├── hooks/                     # Move hook-related
│   ├── hook_enforcement.py
│   ├── hook_integration.py
│   └── [existing hooks]
│
└── utils/                     # Only truly generic utilities
    ├── enhanced_prompt_classifier.py
    ├── redis_similarity_search.py
    ├── concurrent_executor.py
    ├── reflection_parser.py
    └── usage_helper.py
```

## Self-Improving Prompt Updates Needed

The ASSESS_ALL_CORE_USAGE.md needs to be updated to:
1. Only test files that actually belong in core/
2. Remove tests for factorial.py and other non-core files
3. Add proper categorization of what constitutes "core" functionality
4. Update the component expectations to match the new structure

## Benefits of Restructuring

1. **Clarity**: Clear separation of concerns
2. **Testability**: Each directory has focused functionality
3. **Maintainability**: Easy to find and update related code
4. **Self-Containment**: Each directory is self-sufficient for its purpose

## Next Steps

1. Choose Option 1 or Option 2
2. Move files to their new locations
3. Update all import statements
4. Update self-improving prompts to match new structure
5. Clean up reports/ and tmp/ directories
6. Apply same pattern to cli/ and hooks/ directories