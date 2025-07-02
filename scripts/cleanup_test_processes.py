#!/usr/bin/env python3
"""Clean up any lingering test processes from stress tests."""

import subprocess
import psutil
import signal
import os
import time

def cleanup_test_processes():
    """Find and terminate test-related processes."""
    
    print("🧹 Cleaning up test processes...")
    
    patterns = [
        "websocket_handler.py",
        "stress_test",
        "claude -p",
        "python.*preflight",
        "python.*cc_executor"
    ]
    
    terminated = []
    
    # Find processes matching patterns
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            
            for pattern in patterns:
                if pattern in cmdline and proc.pid != os.getpid():
                    print(f"  Found: PID {proc.pid} - {cmdline[:80]}")
                    
                    # Try graceful termination first
                    try:
                        proc.terminate()
                        terminated.append((proc.pid, cmdline[:80]))
                    except psutil.NoSuchProcess:
                        pass
                    break
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Wait for graceful termination
    if terminated:
        print(f"\n  Waiting 5s for {len(terminated)} processes to terminate...")
        time.sleep(5)
        
        # Force kill any remaining
        for pid, cmd in terminated:
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    print(f"  Force killing PID {pid}")
                    proc.kill()
            except psutil.NoSuchProcess:
                pass
    
    # Check ports
    print("\n📡 Checking ports...")
    ports_to_check = [8002, 8004]
    
    for port in ports_to_check:
        try:
            result = subprocess.run(
                ['lsof', f'-ti:{port}'], 
                capture_output=True, 
                text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                print(f"  Port {port} in use by PIDs: {', '.join(pids)}")
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                        print(f"    Killed PID {pid}")
                    except:
                        pass
            else:
                print(f"  Port {port}: Free ✓")
        except:
            print(f"  Port {port}: Unable to check")
    
    print("\n✅ Cleanup complete!")
    
    # Show remaining Claude processes
    print("\n📋 Remaining Claude processes:")
    result = subprocess.run(
        ['ps', 'aux'], 
        capture_output=True, 
        text=True
    )
    
    claude_count = 0
    for line in result.stdout.split('\n'):
        if 'claude' in line and 'grep' not in line:
            claude_count += 1
            parts = line.split(None, 10)
            if len(parts) > 10:
                print(f"  PID {parts[1]}: {parts[10][:80]}")
    
    if claude_count == 0:
        print("  None found ✓")
    else:
        print(f"\n  ⚠️  {claude_count} Claude processes still running")
        print("  These appear to be interactive Claude sessions, not test processes")

if __name__ == "__main__":
    cleanup_test_processes()