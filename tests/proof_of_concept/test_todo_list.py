"""
Unit tests for the full-featured TodoList class.

Tests the TodoList class with persistent storage, priorities, and completion tracking.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path

from todo_list import TodoList


class TestTodoList:
    """Test cases for the TodoList class."""

    @pytest.fixture
    def temp_storage_path(self):
        """Create a temporary file for todo storage."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def todo_list(self, temp_storage_path):
        """Create a TodoList instance with temporary storage."""
        return TodoList(storage_path=temp_storage_path)

    def test_initialization(self, todo_list):
        """Test TodoList initialization."""
        assert todo_list.todos == []
        assert todo_list._next_id == 1
        assert isinstance(todo_list.storage_path, Path)

    def test_add_todo(self, todo_list):
        """Test adding a new todo item."""
        todo_id = todo_list.add("Test task", "high")
        assert todo_id == 1
        assert len(todo_list.todos) == 1
        
        todo = todo_list.todos[0]
        assert todo["id"] == 1
        assert todo["task"] == "Test task"
        assert todo["priority"] == "high"
        assert todo["completed"] is False
        assert isinstance(todo["created_at"], datetime)

    def test_add_multiple_todos(self, todo_list):
        """Test adding multiple todo items."""
        id1 = todo_list.add("First task")
        id2 = todo_list.add("Second task", "low")
        id3 = todo_list.add("Third task", "high")
        
        assert id1 == 1
        assert id2 == 2
        assert id3 == 3
        assert len(todo_list.todos) == 3

    def test_remove_todo(self, todo_list):
        """Test removing a todo item."""
        id1 = todo_list.add("Task to remove")
        id2 = todo_list.add("Task to keep")
        
        assert todo_list.remove(id1) is True
        assert len(todo_list.todos) == 1
        assert todo_list.todos[0]["id"] == id2

    def test_remove_nonexistent_todo(self, todo_list):
        """Test removing a todo that doesn't exist."""
        todo_list.add("Some task")
        assert todo_list.remove(999) is False
        assert len(todo_list.todos) == 1

    def test_list_all_todos(self, todo_list):
        """Test listing all todos."""
        todo_list.add("Task 1")
        todo_list.add("Task 2")
        todo_list.add("Task 3")
        
        todos = todo_list.list()
        assert len(todos) == 3
        assert todos[0]["task"] == "Task 1"
        assert todos[1]["task"] == "Task 2"
        assert todos[2]["task"] == "Task 3"

    def test_list_filtered_todos(self, todo_list):
        """Test listing todos with completion filter."""
        id1 = todo_list.add("Completed task")
        id2 = todo_list.add("Pending task 1")
        id3 = todo_list.add("Pending task 2")
        
        todo_list.complete(id1)
        
        # Filter completed
        completed = todo_list.list(filter_completed=True)
        assert len(completed) == 1
        assert completed[0]["id"] == id1
        
        # Filter pending
        pending = todo_list.list(filter_completed=False)
        assert len(pending) == 2
        assert pending[0]["id"] == id2
        assert pending[1]["id"] == id3

    def test_complete_todo(self, todo_list):
        """Test marking a todo as completed."""
        todo_id = todo_list.add("Task to complete")
        
        assert todo_list.todos[0]["completed"] is False
        assert todo_list.complete(todo_id) is True
        assert todo_list.todos[0]["completed"] is True

    def test_complete_nonexistent_todo(self, todo_list):
        """Test completing a todo that doesn't exist."""
        todo_list.add("Some task")
        assert todo_list.complete(999) is False

    def test_save_and_load(self, temp_storage_path):
        """Test saving and loading todos from storage."""
        # Create and populate first todo list
        todo_list1 = TodoList(storage_path=temp_storage_path)
        id1 = todo_list1.add("Task 1", "high")
        id2 = todo_list1.add("Task 2", "low")
        todo_list1.complete(id1)
        
        # Create second todo list from same storage
        todo_list2 = TodoList(storage_path=temp_storage_path)
        
        # Verify data was loaded correctly
        assert len(todo_list2.todos) == 2
        assert todo_list2.todos[0]["task"] == "Task 1"
        assert todo_list2.todos[0]["completed"] is True
        assert todo_list2.todos[1]["task"] == "Task 2"
        assert todo_list2.todos[1]["completed"] is False
        assert todo_list2._next_id == 3

    def test_load_from_corrupted_file(self, temp_storage_path):
        """Test loading from a corrupted JSON file."""
        # Write invalid JSON
        with open(temp_storage_path, 'w') as f:
            f.write("{ invalid json }")
        
        # Should handle gracefully
        todo_list = TodoList(storage_path=temp_storage_path)
        assert todo_list.todos == []
        assert todo_list._next_id == 1

    def test_load_from_nonexistent_file(self):
        """Test loading when storage file doesn't exist."""
        todo_list = TodoList(storage_path="nonexistent_file.json")
        assert todo_list.todos == []
        assert todo_list._next_id == 1

    def test_str_representation(self, todo_list):
        """Test string representation of todo list."""
        # Empty list
        assert str(todo_list) == "Todo list is empty"
        
        # With items
        id1 = todo_list.add("Task 1", "high")
        id2 = todo_list.add("Task 2", "medium")
        todo_list.complete(id1)
        
        output = str(todo_list)
        assert "Todo List:" in output
        assert "✓ [1] Task 1 (high)" in output
        assert "○ [2] Task 2 (medium)" in output

    def test_priority_values(self, todo_list):
        """Test different priority values."""
        id1 = todo_list.add("Low priority", "low")
        id2 = todo_list.add("Medium priority", "medium")
        id3 = todo_list.add("High priority", "high")
        id4 = todo_list.add("Default priority")  # Should default to medium
        
        assert todo_list.todos[0]["priority"] == "low"
        assert todo_list.todos[1]["priority"] == "medium"
        assert todo_list.todos[2]["priority"] == "high"
        assert todo_list.todos[3]["priority"] == "medium"

    def test_auto_save_on_operations(self, temp_storage_path):
        """Test that operations automatically save to storage."""
        todo_list = TodoList(storage_path=temp_storage_path)
        
        # Add triggers save
        todo_list.add("Task 1")
        assert os.path.exists(temp_storage_path)
        with open(temp_storage_path, 'r') as f:
            data = json.load(f)
            assert len(data["todos"]) == 1
        
        # Complete triggers save
        todo_list.complete(1)
        with open(temp_storage_path, 'r') as f:
            data = json.load(f)
            assert data["todos"][0]["completed"] is True
        
        # Remove triggers save
        todo_list.remove(1)
        with open(temp_storage_path, 'r') as f:
            data = json.load(f)
            assert len(data["todos"]) == 0

    def test_datetime_serialization(self, temp_storage_path):
        """Test that datetime objects are properly serialized/deserialized."""
        todo_list1 = TodoList(storage_path=temp_storage_path)
        todo_list1.add("Test task")
        
        # Check the saved file contains ISO format datetime
        with open(temp_storage_path, 'r') as f:
            data = json.load(f)
            assert isinstance(data["todos"][0]["created_at"], str)
            # Should be in ISO format
            datetime.fromisoformat(data["todos"][0]["created_at"])
        
        # Load in new instance
        todo_list2 = TodoList(storage_path=temp_storage_path)
        assert isinstance(todo_list2.todos[0]["created_at"], datetime)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])