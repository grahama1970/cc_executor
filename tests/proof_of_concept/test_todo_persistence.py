#!/usr/bin/env python3
"""
Test script to verify JSON persistence of TodoList.

This script demonstrates that todos are persisted between sessions.
"""

from todo_list import TodoList
import os

def test_persistence():
    """Test that todos persist between TodoList instances."""
    
    print("=== Testing Todo List JSON Persistence ===\n")
    
    # Clean up any existing todos.json for a fresh test
    if os.path.exists("todos.json"):
        os.remove("todos.json")
        print("Removed existing todos.json for fresh test\n")
    
    # Session 1: Create a TodoList and add some items
    print("Session 1: Creating new TodoList and adding items...")
    todo1 = TodoList()
    id1 = todo1.add("Complete project documentation", "high")
    id2 = todo1.add("Fix bug in authentication", "high")
    id3 = todo1.add("Update README", "low")
    
    print(f"Added 3 todos with IDs: {id1}, {id2}, {id3}")
    print(todo1)
    
    # Complete one task
    todo1.complete(id2)
    print(f"\nCompleted task {id2}")
    
    # The todos should now be saved to todos.json
    del todo1  # Delete the instance to simulate closing the program
    
    print("\n--- Simulating program restart ---\n")
    
    # Session 2: Create a new TodoList instance
    print("Session 2: Creating new TodoList instance...")
    todo2 = TodoList()
    
    print("Loaded todos from JSON file:")
    print(todo2)
    
    # Verify the data was persisted correctly
    todos = todo2.list()
    assert len(todos) == 3, f"Expected 3 todos, got {len(todos)}"
    
    # Check that task 2 is still marked as completed
    task2 = next((t for t in todos if t['id'] == id2), None)
    assert task2 is not None, "Task 2 not found"
    assert task2['completed'] == True, "Task 2 should be completed"
    
    print("\n✓ Persistence test passed! Todos were successfully saved and loaded.")
    
    # Add a new task in session 2
    id4 = todo2.add("Implement new feature", "medium")
    print(f"\nAdded new task with ID {id4} in session 2")
    print(todo2)
    
    # Clean up
    os.remove("todos.json")
    print("\n✓ Test complete. Cleaned up todos.json")


if __name__ == "__main__":
    test_persistence()