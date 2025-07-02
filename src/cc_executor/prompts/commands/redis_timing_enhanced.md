# Redis BM25 Timing Enhanced - Load-Aware Smart Timeouts

## 🎯 Purpose
Get intelligent timeout suggestions based on historical execution times AND system load.

## 🚀 Setup
```bash
source .venv/bin/activate && export PYTHONPATH=./src

# Enhanced schema with load tracking
redis-cli FT.CREATE task_times_v2 ON HASH PREFIX 1 task: SCHEMA \
  natural_language TEXT \
  elapsed_time NUMERIC \
  status TAG \
  timestamp NUMERIC \
  cpu_load NUMERIC \
  gpu_memory_gb NUMERIC \
  system_load_avg NUMERIC
```

## 📋 Core Functions

### Get System Load
```bash
get_system_load() {
    # CPU load average (1 minute)
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    
    # GPU memory usage (if nvidia-smi available)
    local gpu_memory=0
    if command -v nvidia-smi &> /dev/null; then
        gpu_memory=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
        gpu_memory=$(echo "scale=2; $gpu_memory / 1024" | bc)  # Convert to GB
    fi
    
    echo "$cpu_load|$gpu_memory"
}
```

### Enhanced Timeout Calculation
```bash
get_bm25_timeout_enhanced() {
    local query="$1"
    local default="$2"
    
    # Get current system load
    local load_info=$(get_system_load)
    local cpu_load=$(echo "$load_info" | cut -d'|' -f1)
    local gpu_memory=$(echo "$load_info" | cut -d'|' -f2)
    
    # Search for similar tasks
    local times=$(redis-cli FT.SEARCH task_times_v2 "$query" \
                  RETURN 3 elapsed_time cpu_load system_load_avg \
                  LIMIT 0 10 2>/dev/null | \
                  grep -A3 "elapsed_time" | grep -E '^[0-9]')
    
    if [ -z "$times" ]; then
        local timeout=$default
    else
        # Calculate weighted average based on similar load conditions
        local avg=$(echo "$times" | awk '{sum+=$1; n++} END {if(n>0) print sum/n; else print 0}')
        local timeout=$(echo "if ($avg * 2 > 30) $avg * 2 else 30" | bc -l | cut -d. -f1)
    fi
    
    # LOAD ADJUSTMENT: If CPU load > 14, multiply timeout by 3
    if (( $(echo "$cpu_load > 14" | bc -l) )); then
        echo "⚠️ High system load detected: $cpu_load" >&2
        timeout=$(echo "$timeout * 3" | bc)
    fi
    
    # Cap at 10 minutes
    if [ "$timeout" -gt 600 ]; then
        echo "600"
    else
        echo "$timeout"
    fi
}
```

### Store Task with Load Info
```bash
create_task_with_load() {
    local task_description="$1"
    
    # Get system load
    local load_info=$(get_system_load)
    local cpu_load=$(echo "$load_info" | cut -d'|' -f1)
    local gpu_memory=$(echo "$load_info" | cut -d'|' -f2)
    
    # Create task ID
    TASK_ID="task:$(uuidgen)"
    echo "TASK_ID=$TASK_ID"
    
    # Store with load information
    redis-cli HSET "$TASK_ID" \
      natural_language "$task_description" \
      elapsed_time "0" \
      status "pending" \
      timestamp "$(date +%s)" \
      cpu_load "$cpu_load" \
      gpu_memory_gb "$gpu_memory" \
      system_load_avg "$cpu_load"
    
    echo "$TASK_ID"
}
```

### Update Task with Actual Time
```bash
update_task_with_load() {
    local task_id="$1"
    local elapsed="$2"
    
    # Get current load (to see if it changed during execution)
    local load_info=$(get_system_load)
    local cpu_load=$(echo "$load_info" | cut -d'|' -f1)
    local gpu_memory=$(echo "$load_info" | cut -d'|' -f2)
    
    redis-cli HSET "$task_id" \
      elapsed_time "$elapsed" \
      status "completed" \
      end_cpu_load "$cpu_load" \
      end_gpu_memory_gb "$gpu_memory"
}
```

## 💡 Usage Example
```bash
# Before execution - get load-aware timeout
TIMEOUT=$(get_bm25_timeout_enhanced "analyze python security" 120)
echo "Using timeout: ${TIMEOUT}s"

# Create task with load tracking
TASK_ID=$(create_task_with_load "analyze python security vulnerabilities")

# Execute with that timeout
START_TIME=$(date +%s)
claude -p "Analyze this Python code for security issues" --timeout "$TIMEOUT"

# Update with actual time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
update_task_with_load "$TASK_ID" "$ELAPSED"
```

## 📊 Load Analysis Queries

### Find Tasks by Load Level
```bash
# Tasks executed under high load (>14)
redis-cli FT.SEARCH task_times_v2 "@cpu_load:[14 +inf]" \
  RETURN 3 natural_language elapsed_time cpu_load

# Tasks with high GPU usage (>15GB)
redis-cli FT.SEARCH task_times_v2 "@gpu_memory_gb:[15 +inf]" \
  RETURN 3 natural_language elapsed_time gpu_memory_gb
```

### Average Time by Load Level
```bash
# Compare execution times at different load levels
echo "Low load (<5):"
redis-cli FT.SEARCH task_times_v2 "@cpu_load:[0 5]" \
  RETURN 1 elapsed_time LIMIT 0 100 | \
  grep -E '^[0-9]' | awk '{sum+=$1; n++} END {print "Avg: " sum/n "s"}'

echo "High load (>14):"
redis-cli FT.SEARCH task_times_v2 "@cpu_load:[14 +inf]" \
  RETURN 1 elapsed_time LIMIT 0 100 | \
  grep -E '^[0-9]' | awk '{sum+=$1; n++} END {print "Avg: " sum/n "s"}'
```

## 🚨 Load Thresholds
- **Normal**: CPU load < 5 → Use standard timeout
- **Moderate**: CPU load 5-14 → Monitor, may need 1.5x timeout
- **High**: CPU load > 14 → **3x timeout automatically**
- **Critical**: CPU load > 20 → Consider postponing non-critical tasks

## ⚠️ Important Notes
1. High Ollama GPU usage (>20GB) significantly impacts Claude CLI performance
2. System load > 14 triggers automatic 3x timeout multiplier
3. Load data helps predict future task performance under similar conditions
4. Store both start and end load to detect load changes during execution