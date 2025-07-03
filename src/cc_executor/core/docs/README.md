# Core Module Documentation

## Overview
This directory contains comprehensive documentation for the CC Executor core module.

## Structure

### `/architecture/`
- System design documents
- Component interaction diagrams
- Data flow documentation

### `/assessment/`
- [README.md](assessment/README.md) - Self-assessment system documentation
- How the core module tests itself
- Behavioral testing methodology

### `/guides/`
- [USAGE_RESPONSE_SAVING_GUIDE.md](guides/USAGE_RESPONSE_SAVING_GUIDE.md) - Pattern for response saving
- Development guidelines
- Testing procedures

### `/api/`
- WebSocket protocol specification
- JSON-RPC message formats
- Integration examples

### Root Documents
- [ASSESSMENT_SUMMARY_REPORT.md](ASSESSMENT_SUMMARY_REPORT.md) - Current implementation status
- This README.md - Documentation overview

## Key Concepts

### 1. Response Saving Pattern
Every Python module must save its execution output as JSON to enable verification by self-improving prompts. See the [guide](guides/USAGE_RESPONSE_SAVING_GUIDE.md) for details.

### 2. WebSocket MCP Protocol
The service implements Model Context Protocol over WebSocket using JSON-RPC 2.0.

### 3. Process Management
Commands execute in isolated process groups with full signal control (SIGSTOP/SIGCONT/SIGTERM).

## Quick Links
- [Main README](../README.md) - Core module overview
- [Self-Improving Prompt](../prompts/ASSESS_ALL_CORE_USAGE.md) - Automated testing system
- [API Reference](api/) - Protocol documentation