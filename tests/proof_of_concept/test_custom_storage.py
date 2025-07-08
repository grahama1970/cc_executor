#!/usr/bin/env python3
"""
Test custom storage paths for TodoList.

Demonstrates using TodoList with different storage locations.
"""

from todo_list import TodoList
import os
from pathlib import Path

def test_custom_storage():
    """Test using custom storage paths for different todo lists."""
    
    print("=== Testing Custom Storage Paths ===\n")
    
    # Create a data directory for our todo lists
    data_dir = Path("data/todos")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create personal todo list
    print("Creating personal todo list...")
    personal_todos = TodoList(storage_path="data/todos/personal.json")
    personal_todos.add("Buy groceries", "medium")
    personal_todos.add("Call mom", "high")
    personal_todos.add("Schedule dentist appointment", "low")
    
    print("Personal todos:")
    print(personal_todos)
    
    # Create work todo list
    print("\nCreating work todo list...")
    work_todos = TodoList(storage_path="data/todos/work.json")
    work_todos.add("Finish quarterly report", "high")
    work_todos.add("Review team PRs", "high")
    work_todos.add("Update project roadmap", "medium")
    
    print("\nWork todos:")
    print(work_todos)
    
    # Verify files were created
    print("\n--- Verifying storage files ---")
    for filename in ["personal.json", "work.json"]:
        filepath = data_dir / filename
        if filepath.exists():
            print(f"✓ {filepath} exists ({filepath.stat().st_size} bytes)")
        else:
            print(f"✗ {filepath} missing!")
    
    # Load them again to verify persistence
    print("\n--- Loading from storage ---")
    personal_todos2 = TodoList(storage_path="data/todos/personal.json")
    work_todos2 = TodoList(storage_path="data/todos/work.json")
    
    print(f"\nPersonal todos loaded: {len(personal_todos2.list())} items")
    print(f"Work todos loaded: {len(work_todos2.list())} items")
    
    # Clean up
    import shutil
    if data_dir.exists():
        shutil.rmtree(data_dir.parent)
        print("\n✓ Cleaned up test data directory")


if __name__ == "__main__":
    test_custom_storage()