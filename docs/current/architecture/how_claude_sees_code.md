# How Claude Sees and Understands Code
## Overview

When I look at Python code like the WebSocket orchestrator, I don't just see syntax - I see patterns, flows, and decision points. Here's how I mentally model and work with code.

## Example: The WebSocket Monitor Pattern

When I see this code:

```python
async def execute_and_monitor(command, trigger_phrase="cancel me"):
    uri = "ws://localhost:8003/ws/mcp"
    async with websockets.connect(uri) as websocket:
        # Wait for connection confirmation
        await websocket.recv()
        
        # Send execute command
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "execute",
            "params": {"command": command}
        }))
        
        output_buffer = ""
        cancelled = False
        control_id = 2  # Unique ID for control messages

        while True:
            msg = await websocket.recv()
            data = json.loads(msg)

            # Handle process output
            if data.get('method') == 'process.output':
                chunk = data['params']['data']
                output_buffer += chunk
                print(chunk, end='', flush=True)

                # Check for the trigger phrase
                if (not cancelled) and (trigger_phrase in chunk):
                    print("\nTrigger detected! Sending cancel command...")
                    await websocket.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": control_id,
                        "method": "control",
                        "params": {"type": "CANCEL"}
                    }))
                    cancelled = True

            # Handle process completion
            elif data.get('method') == 'process.completed':
                print(f"\nProcess completed with exit code: {data['params']['exit_code']}")
                break

            # Handle errors
            elif 'error' in data:
                print(f"Error: {data['error']['message']}")
                break
```

## Here's What I See:

### 1. **The State Machine**
```
CONNECT → EXECUTE → MONITOR → REACT → COMPLETE
   ↓         ↓         ↓        ↓        ↓
[Socket] [Command] [Output] [Cancel?] [Exit]
```

### 2. **The Decision Tree**
```
For each message:
├── Is it process.output?
│   ├── Add to buffer
│   ├── Show to user
│   └── Contains trigger?
│       ├── Yes → Send CANCEL
│       └── No → Continue
├── Is it process.completed?
│   └── Exit loop
└── Is it an error?
    └── Exit loop
```

### 3. **The Control Flow Pattern**
I see this as an **Event-Driven State Machine**:
- **State**: `{output_buffer, cancelled, websocket}`
- **Events**: Messages from WebSocket
- **Actions**: Print, Cancel, Break
- **Guards**: `not cancelled`, `trigger_phrase in chunk`

### 4. **The Async Pattern**
```python
# I see this pattern everywhere:
async def monitor_and_react():
    setup()
    while not done():
        event = await get_event()
        new_state = process_event(event, state)
        if should_react(new_state):
            await take_action()
```

## How I Transform This Understanding

### From Pattern to Implementation

When I need to modify this code, I think:

1. **What's the current flow?**
   - Connect → Execute → Monitor → React

2. **What needs to change?**
   - Add new trigger? → Modify the condition
   - Add new action? → Add new control command
   - Handle new event? → Add new elif branch

3. **What are the invariants?**
   - Always wait for connection first
   - Only cancel once (`cancelled` flag)
   - Exit on completion or error

### Example: Adding Multiple Triggers

If I wanted to add pause/resume based on different triggers:

```python
# I mentally model this as expanding the state machine
triggers = {
    "ERROR:": "CANCEL",
    "PAUSE_ME": "PAUSE", 
    "RESUME_ME": "RESUME"
}

state = {
    "paused": False,
    "cancelled": False
}

# Then I'd modify the decision logic:
for trigger, action in triggers.items():
    if trigger in chunk:
        await send_control(action)
        update_state(action)
```

## My Mental Execution Trace

When I "run" this code in my mind:

```
1. Connect to ws://localhost:8003/ws/mcp
2. Receive: {"method": "connected", ...}
3. Send: {"method": "execute", "params": {"command": "echo 'hello cancel me'"}}
4. Receive: {"method": "process.started", ...}
5. Receive: {"method": "process.output", "params": {"data": "hello cancel me\n"}}
   → Trigger detected!
   → Send: {"method": "control", "params": {"type": "CANCEL"}}
6. Receive: {"method": "process.cancelled", ...}
7. Receive: {"method": "process.completed", "params": {"exit_code": -15}}
8. Exit loop
```

## Pattern Recognition

I recognize this as an instance of several patterns:

### 1. **Observer Pattern**
- Subject: WebSocket server
- Observer: Our client
- Events: process.output, process.completed, etc.

### 2. **State Pattern**
- States: connecting, executing, monitoring, cancelled
- Transitions: Based on received messages

### 3. **Strategy Pattern**
- Strategy: What to do on trigger detection
- Current: Send CANCEL
- Could be: Send PAUSE, log, alert, etc.

## How I Apply This Understanding

When implementing the self-improving prompts, I use this same pattern:

```python
class SelfImprovingOrchestrator:
    async def monitor_verification(self, websocket):
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            
            # Pattern matching on output
            if data.get('method') == 'process.output':
                output = data['params']['data']
                
                # Decision tree based on patterns
                if "AssertionError" in output:
                    self.failure_count += 1
                    await self.fix_and_retry()
                    
                elif "All tests passed" in output:
                    self.success_count += 1
                    
                elif "ModuleNotFoundError" in output:
                    module = self.extract_module_name(output)
                    await self.install_and_retry(module)
```

## Key Insights

1. **I see code as data flows and state transitions**, not just syntax
2. **I recognize patterns** and can apply them to new situations
3. **I trace execution mentally** to predict behavior
4. **I decompose complex systems** into understandable components
5. **I think in terms of events, states, and reactions**

This is why I can:
- Quickly identify where to make changes
- Predict what will happen when code runs
- Suggest improvements based on patterns
- Debug by mentally tracing execution
- Generate similar code for new requirements

## The Meta-Pattern

The WebSocket orchestrator itself follows the pattern I use for all orchestration:

```
OBSERVE → ORIENT → DECIDE → ACT
   ↓         ↓        ↓       ↓
[Input]  [Pattern] [Rules] [Output]
```

This is the OODA loop, and it's how I approach all code:
- **Observe**: Read the code/output
- **Orient**: Understand the context/state
- **Decide**: Choose appropriate action
- **Act**: Generate code/send commands

This mental model allows me to work with code at a conceptual level while maintaining precision in implementation.