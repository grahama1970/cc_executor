"""
Comprehensive pytest tests for the TODO API.
Tests all endpoints (GET, POST, DELETE) including edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from todo_api.main import app, todos, next_id


@pytest.fixture(autouse=True)
def reset_state():
    """Reset the global state before each test."""
    global todos, next_id
    todos.clear()
    # Reset next_id through the module
    import todo_api.main
    todo_api.main.next_id = 1
    yield
    # Cleanup after test
    todos.clear()
    todo_api.main.next_id = 1


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestGetTodos:
    """Tests for GET /todos endpoint."""
    
    def test_get_empty_todos(self, client):
        """Test getting todos when list is empty."""
        response = client.get("/todos")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_todos_with_items(self, client):
        """Test getting todos when list has items."""
        # Add some todos first
        client.post("/todos", json={"title": "Test 1", "completed": False})
        client.post("/todos", json={"title": "Test 2", "completed": True})
        
        response = client.get("/todos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["title"] == "Test 1"
        assert data[0]["completed"] is False
        assert data[1]["id"] == 2
        assert data[1]["title"] == "Test 2"
        assert data[1]["completed"] is True


class TestCreateTodo:
    """Tests for POST /todos endpoint."""
    
    def test_create_todo_minimal(self, client):
        """Test creating a todo with only required fields."""
        response = client.post("/todos", json={"title": "New Todo"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "New Todo"
        assert data["completed"] is False  # Default value
    
    def test_create_todo_complete(self, client):
        """Test creating a todo with all fields."""
        response = client.post("/todos", json={
            "title": "Complete Todo",
            "completed": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Complete Todo"
        assert data["completed"] is True
    
    def test_create_multiple_todos(self, client):
        """Test creating multiple todos with incrementing IDs."""
        for i in range(3):
            response = client.post("/todos", json={"title": f"Todo {i+1}"})
            assert response.status_code == 200
            assert response.json()["id"] == i + 1
    
    def test_create_todo_missing_title(self, client):
        """Test creating a todo without required title field."""
        response = client.post("/todos", json={"completed": True})
        assert response.status_code == 422  # Validation error
    
    def test_create_todo_empty_title(self, client):
        """Test creating a todo with empty title."""
        response = client.post("/todos", json={"title": ""})
        assert response.status_code == 200  # Empty string is valid
        assert response.json()["title"] == ""
    
    def test_create_todo_invalid_json(self, client):
        """Test creating a todo with invalid JSON."""
        response = client.post("/todos", data="not json")
        assert response.status_code == 422
    
    def test_create_todo_persistence(self, client):
        """Test that created todos persist in the list."""
        client.post("/todos", json={"title": "Persistent Todo"})
        
        response = client.get("/todos")
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Persistent Todo"


class TestUpdateTodo:
    """Tests for PUT /todos/{todo_id} endpoint."""
    
    def test_update_existing_todo(self, client):
        """Test updating an existing todo."""
        # Create a todo first
        create_response = client.post("/todos", json={"title": "Original", "completed": False})
        todo_id = create_response.json()["id"]
        
        # Update it
        response = client.put(f"/todos/{todo_id}", json={
            "title": "Updated",
            "completed": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == todo_id
        assert data["title"] == "Updated"
        assert data["completed"] is True
        
        # Verify the update persisted
        get_response = client.get("/todos")
        todos = get_response.json()
        assert len(todos) == 1
        assert todos[0]["title"] == "Updated"
        assert todos[0]["completed"] is True
    
    def test_update_non_existent_todo(self, client):
        """Test updating a todo that doesn't exist."""
        response = client.put("/todos/999", json={
            "title": "Won't work",
            "completed": False
        })
        assert response.status_code == 404
        assert response.json()["detail"] == "Todo 999 not found"
    
    def test_update_title_only(self, client):
        """Test updating only the title of a todo."""
        # Create a todo
        create_response = client.post("/todos", json={"title": "Original", "completed": True})
        todo_id = create_response.json()["id"]
        
        # Update only title
        response = client.put(f"/todos/{todo_id}", json={
            "title": "New Title",
            "completed": True  # Keep the same completed status
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["completed"] is True
    
    def test_update_completed_only(self, client):
        """Test updating only the completed status of a todo."""
        # Create a todo
        create_response = client.post("/todos", json={"title": "Keep Title", "completed": False})
        todo_id = create_response.json()["id"]
        
        # Update only completed status
        response = client.put(f"/todos/{todo_id}", json={
            "title": "Keep Title",  # Keep the same title
            "completed": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Keep Title"
        assert data["completed"] is True
    
    def test_update_missing_fields(self, client):
        """Test updating with missing required fields."""
        # Create a todo
        create_response = client.post("/todos", json={"title": "Test"})
        todo_id = create_response.json()["id"]
        
        # Try to update without title
        response = client.put(f"/todos/{todo_id}", json={"completed": True})
        assert response.status_code == 422
        
        # Try to update without completed
        response = client.put(f"/todos/{todo_id}", json={"title": "New Title"})
        assert response.status_code == 422
    
    def test_update_invalid_id_type(self, client):
        """Test updating with invalid ID type."""
        response = client.put("/todos/abc", json={
            "title": "Won't work",
            "completed": False
        })
        assert response.status_code == 422
    
    def test_update_empty_title(self, client):
        """Test updating with empty title."""
        # Create a todo
        create_response = client.post("/todos", json={"title": "Original"})
        todo_id = create_response.json()["id"]
        
        # Update with empty title
        response = client.put(f"/todos/{todo_id}", json={
            "title": "",
            "completed": True
        })
        assert response.status_code == 200
        assert response.json()["title"] == ""
    
    def test_update_multiple_todos(self, client):
        """Test updating multiple todos."""
        # Create three todos
        ids = []
        for i in range(3):
            response = client.post("/todos", json={"title": f"Todo {i+1}", "completed": False})
            ids.append(response.json()["id"])
        
        # Update each one differently
        client.put(f"/todos/{ids[0]}", json={"title": "First Updated", "completed": True})
        client.put(f"/todos/{ids[1]}", json={"title": "Second Updated", "completed": False})
        client.put(f"/todos/{ids[2]}", json={"title": "Third Updated", "completed": True})
        
        # Verify all updates
        response = client.get("/todos")
        todos = response.json()
        assert len(todos) == 3
        
        todo_dict = {todo["id"]: todo for todo in todos}
        assert todo_dict[ids[0]]["title"] == "First Updated"
        assert todo_dict[ids[0]]["completed"] is True
        assert todo_dict[ids[1]]["title"] == "Second Updated"
        assert todo_dict[ids[1]]["completed"] is False
        assert todo_dict[ids[2]]["title"] == "Third Updated"
        assert todo_dict[ids[2]]["completed"] is True
    
    def test_update_special_characters(self, client):
        """Test updating with special characters in title."""
        # Create a todo
        create_response = client.post("/todos", json={"title": "Original"})
        todo_id = create_response.json()["id"]
        
        # Update with special characters
        special_title = "Updated with émojis 🎉🚀 and \"quotes\""
        response = client.put(f"/todos/{todo_id}", json={
            "title": special_title,
            "completed": True
        })
        assert response.status_code == 200
        assert response.json()["title"] == special_title
    
    def test_update_idempotency(self, client):
        """Test that updating with same values is idempotent."""
        # Create a todo
        create_response = client.post("/todos", json={"title": "Test", "completed": False})
        todo_id = create_response.json()["id"]
        
        # Update twice with same values
        update_data = {"title": "Updated", "completed": True}
        response1 = client.put(f"/todos/{todo_id}", json=update_data)
        response2 = client.put(f"/todos/{todo_id}", json=update_data)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


class TestDeleteTodo:
    """Tests for DELETE /todos/{todo_id} endpoint."""
    
    def test_delete_existing_todo(self, client):
        """Test deleting an existing todo."""
        # Create a todo first
        create_response = client.post("/todos", json={"title": "To Delete"})
        todo_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/todos/{todo_id}")
        assert response.status_code == 200
        assert response.json() == {"message": f"Todo {todo_id} deleted"}
        
        # Verify it's gone
        get_response = client.get("/todos")
        assert get_response.json() == []
    
    def test_delete_non_existent_todo(self, client):
        """Test deleting a todo that doesn't exist."""
        response = client.delete("/todos/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Todo 999 not found"
    
    def test_delete_invalid_id_type(self, client):
        """Test deleting with invalid ID type."""
        response = client.delete("/todos/abc")
        assert response.status_code == 422  # Validation error
    
    def test_delete_from_multiple_todos(self, client):
        """Test deleting one todo from multiple."""
        # Create three todos
        ids = []
        for i in range(3):
            response = client.post("/todos", json={"title": f"Todo {i+1}"})
            ids.append(response.json()["id"])
        
        # Delete the middle one
        client.delete(f"/todos/{ids[1]}")
        
        # Verify only two remain
        response = client.get("/todos")
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == ids[0]
        assert data[1]["id"] == ids[2]
    
    def test_delete_already_deleted_todo(self, client):
        """Test deleting a todo that was already deleted."""
        # Create and delete a todo
        create_response = client.post("/todos", json={"title": "To Delete"})
        todo_id = create_response.json()["id"]
        client.delete(f"/todos/{todo_id}")
        
        # Try to delete again
        response = client.delete(f"/todos/{todo_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == f"Todo {todo_id} not found"


class TestEdgeCases:
    """Tests for edge cases and unusual scenarios."""
    
    def test_concurrent_operations(self, client):
        """Test behavior with rapid concurrent-like operations."""
        # Create multiple todos rapidly
        for i in range(10):
            client.post("/todos", json={"title": f"Rapid {i}"})
        
        # Delete every other one
        for i in range(1, 11, 2):
            client.delete(f"/todos/{i}")
        
        # Verify correct state
        response = client.get("/todos")
        data = response.json()
        assert len(data) == 5
        assert all(todo["id"] % 2 == 0 for todo in data)
    
    def test_large_todo_title(self, client):
        """Test creating a todo with a very long title."""
        long_title = "A" * 1000
        response = client.post("/todos", json={"title": long_title})
        assert response.status_code == 200
        assert response.json()["title"] == long_title
    
    def test_special_characters_in_title(self, client):
        """Test creating todos with special characters."""
        special_titles = [
            "Todo with émojis 🎉🚀",
            "Todo with \n newlines",
            "Todo with \"quotes\"",
            "Todo with \\backslashes\\",
            "Todo with unicode: 你好世界"
        ]
        
        for title in special_titles:
            response = client.post("/todos", json={"title": title})
            assert response.status_code == 200
            assert response.json()["title"] == title


if __name__ == "__main__":
    # Run specific test if executed directly
    import sys
    if len(sys.argv) > 1:
        pytest.main([__file__, "-v", "-k", sys.argv[1]])
    else:
        pytest.main([__file__, "-v"])