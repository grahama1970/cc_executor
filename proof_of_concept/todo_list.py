"""
Todo List Manager

A simple todo list class with add, remove, and list functionality.
"""

from typing import List, Optional
from datetime import datetime
import json
import os
from pathlib import Path


class TodoList:
    """Manages a simple todo list with add, remove, and list operations."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize a todo list.
        
        Args:
            storage_path: Path to JSON file for persistence. If None, uses 'todos.json'
        """
        self.storage_path = Path(storage_path) if storage_path else Path("todos.json")
        self.todos: List[dict] = []
        self._next_id = 1
        self.load()
    
    def add(self, task: str, priority: str = "medium") -> int:
        """
        Add a new todo item.
        
        Args:
            task: Description of the task
            priority: Priority level (low, medium, high)
            
        Returns:
            ID of the created todo
        """
        todo = {
            "id": self._next_id,
            "task": task,
            "priority": priority,
            "created_at": datetime.now(),
            "completed": False
        }
        self.todos.append(todo)
        self._next_id += 1
        self.save()  # Auto-save after adding
        return todo["id"]
    
    def remove(self, todo_id: int) -> bool:
        """
        Remove a todo by ID.
        
        Args:
            todo_id: ID of the todo to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, todo in enumerate(self.todos):
            if todo["id"] == todo_id:
                self.todos.pop(i)
                self.save()  # Auto-save after removing
                return True
        return False
    
    def list(self, filter_completed: Optional[bool] = None) -> List[dict]:
        """
        List all todos or filter by completion status.
        
        Args:
            filter_completed: If True, show only completed. If False, show only pending.
                            If None, show all.
            
        Returns:
            List of todo items
        """
        if filter_completed is None:
            return self.todos.copy()
        
        return [todo for todo in self.todos if todo["completed"] == filter_completed]
    
    def complete(self, todo_id: int) -> bool:
        """
        Mark a todo as completed.
        
        Args:
            todo_id: ID of the todo to complete
            
        Returns:
            True if marked complete, False if not found
        """
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["completed"] = True
                self.save()  # Auto-save after completing
                return True
        return False
    
    def save(self) -> None:
        """Save the todo list to JSON file."""
        # Convert datetime objects to ISO format for JSON serialization
        serializable_todos = []
        for todo in self.todos:
            todo_copy = todo.copy()
            todo_copy["created_at"] = todo_copy["created_at"].isoformat()
            serializable_todos.append(todo_copy)
        
        data = {
            "todos": serializable_todos,
            "next_id": self._next_id
        }
        
        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to JSON file
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self) -> None:
        """Load the todo list from JSON file."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Convert ISO format strings back to datetime objects
            self.todos = []
            for todo_data in data.get("todos", []):
                todo = todo_data.copy()
                todo["created_at"] = datetime.fromisoformat(todo["created_at"])
                self.todos.append(todo)
            
            self._next_id = data.get("next_id", 1)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Could not load todos from {self.storage_path}: {e}")
            self.todos = []
            self._next_id = 1
    
    def __str__(self) -> str:
        """String representation of the todo list."""
        if not self.todos:
            return "Todo list is empty"
        
        lines = ["Todo List:"]
        for todo in self.todos:
            status = "✓" if todo["completed"] else "○"
            lines.append(f"  {status} [{todo['id']}] {todo['task']} ({todo['priority']})")
        return "\n".join(lines)


if __name__ == "__main__":
    # Usage demonstration
    todo_list = TodoList()
    
    # Add some todos
    id1 = todo_list.add("Write documentation", "high")
    id2 = todo_list.add("Review pull requests", "medium")
    id3 = todo_list.add("Update dependencies", "low")
    
    print("Initial todo list:")
    print(todo_list)
    print()
    
    # Complete a task
    todo_list.complete(id2)
    print("After completing task 2:")
    print(todo_list)
    print()
    
    # List only pending tasks
    pending = todo_list.list(filter_completed=False)
    print(f"Pending tasks: {len(pending)}")
    for todo in pending:
        print(f"  - {todo['task']}")
    print()
    
    # Remove a task
    removed = todo_list.remove(id3)
    print(f"Task {id3} removed: {removed}")
    print("Final todo list:")
    print(todo_list)