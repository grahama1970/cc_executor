import pytest
from fastapi.testclient import TestClient
from main import app, todos
from datetime import datetime


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_todos():
    """Clear todos before each test."""
    todos.clear()
    yield
    todos.clear()


def test_get_todos_empty(client):
    """Test getting todos when list is empty."""
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []


def test_create_todo_minimal(client):
    """Test creating todo with just title."""
    todo_data = {"title": "Test Todo"}
    response = client.post("/todos", json=todo_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == ""
    assert "id" in data
    assert "created_at" in data
    assert len(todos) == 1


def test_create_todo_with_description(client):
    """Test creating todo with title and description."""
    todo_data = {"title": "Test Todo", "description": "Test Description"}
    response = client.post("/todos", json=todo_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == "Test Description"
    assert "id" in data
    assert "created_at" in data


def test_get_todos_multiple(client):
    """Test getting multiple todos."""
    # Create multiple todos
    client.post("/todos", json={"title": "Todo 1"})
    client.post("/todos", json={"title": "Todo 2", "description": "Desc 2"})
    client.post("/todos", json={"title": "Todo 3"})
    
    response = client.get("/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    titles = [todo["title"] for todo in data]
    assert "Todo 1" in titles
    assert "Todo 2" in titles
    assert "Todo 3" in titles


def test_delete_todo_success(client):
    """Test deleting an existing todo."""
    # Create a todo
    create_response = client.post("/todos", json={"title": "To Delete"})
    todo_id = create_response.json()["id"]
    
    # Delete it
    delete_response = client.delete(f"/todos/{todo_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Todo deleted successfully"}
    
    # Verify it's gone
    assert todo_id not in todos
    get_response = client.get("/todos")
    assert len(get_response.json()) == 0


def test_delete_todo_not_found(client):
    """Test deleting non-existent todo."""
    fake_id = "non-existent-id"
    response = client.delete(f"/todos/{fake_id}")
    
    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}


def test_create_todo_validation_error(client):
    """Test creating todo with invalid data."""
    # Missing required field
    response = client.post("/todos", json={})
    assert response.status_code == 422
    
    # Empty title
    response = client.post("/todos", json={"title": ""})
    assert response.status_code == 422


def test_todo_persistence_across_requests(client):
    """Test that todos persist across multiple requests."""
    # Create todo
    create_response = client.post("/todos", json={"title": "Persistent Todo"})
    todo_id = create_response.json()["id"]
    
    # Get todos multiple times
    for _ in range(3):
        response = client.get("/todos")
        todos_list = response.json()
        assert len(todos_list) == 1
        assert todos_list[0]["id"] == todo_id
        assert todos_list[0]["title"] == "Persistent Todo"


def test_created_at_timestamp(client):
    """Test that created_at is properly set."""
    before = datetime.now()
    response = client.post("/todos", json={"title": "Time Test"})
    after = datetime.now()
    
    created_at_str = response.json()["created_at"]
    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
    
    # Allow for some time difference due to processing
    assert before <= created_at <= after


def test_unique_ids(client):
    """Test that each todo gets a unique ID."""
    ids = set()
    for i in range(10):
        response = client.post("/todos", json={"title": f"Todo {i}"})
        todo_id = response.json()["id"]
        assert todo_id not in ids
        ids.add(todo_id)
    
    assert len(ids) == 10


def test_update_todo_title(client):
    """Test updating a todo's title."""
    # Create a todo
    create_response = client.post("/todos", json={"title": "Original Title", "description": "Original Desc"})
    todo_id = create_response.json()["id"]
    original_created_at = create_response.json()["created_at"]
    
    # Update title only
    update_response = client.put(f"/todos/{todo_id}", json={"title": "Updated Title"})
    assert update_response.status_code == 200
    
    updated = update_response.json()
    assert updated["id"] == todo_id
    assert updated["title"] == "Updated Title"
    assert updated["description"] == "Original Desc"  # Should remain unchanged
    assert updated["created_at"] == original_created_at  # Should remain unchanged


def test_update_todo_description(client):
    """Test updating a todo's description."""
    # Create a todo
    create_response = client.post("/todos", json={"title": "Test Todo", "description": "Original Desc"})
    todo_id = create_response.json()["id"]
    
    # Update description only
    update_response = client.put(f"/todos/{todo_id}", json={"description": "Updated Description"})
    assert update_response.status_code == 200
    
    updated = update_response.json()
    assert updated["id"] == todo_id
    assert updated["title"] == "Test Todo"  # Should remain unchanged
    assert updated["description"] == "Updated Description"


def test_update_todo_both_fields(client):
    """Test updating both title and description."""
    # Create a todo
    create_response = client.post("/todos", json={"title": "Original", "description": "Original"})
    todo_id = create_response.json()["id"]
    
    # Update both fields
    update_response = client.put(f"/todos/{todo_id}", json={
        "title": "Updated Title",
        "description": "Updated Description"
    })
    assert update_response.status_code == 200
    
    updated = update_response.json()
    assert updated["title"] == "Updated Title"
    assert updated["description"] == "Updated Description"


def test_update_todo_not_found(client):
    """Test updating a non-existent todo."""
    fake_id = "non-existent-id"
    response = client.put(f"/todos/{fake_id}", json={"title": "New Title"})
    
    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}


def test_update_todo_empty_request(client):
    """Test updating with empty request body."""
    # Create a todo
    create_response = client.post("/todos", json={"title": "Test", "description": "Test"})
    todo_id = create_response.json()["id"]
    
    # Update with empty body - should succeed but not change anything
    update_response = client.put(f"/todos/{todo_id}", json={})
    assert update_response.status_code == 200
    
    updated = update_response.json()
    assert updated["title"] == "Test"
    assert updated["description"] == "Test"


def test_update_todo_persistence(client):
    """Test that updates persist across requests."""
    # Create a todo
    create_response = client.post("/todos", json={"title": "Original", "description": "Original"})
    todo_id = create_response.json()["id"]
    
    # Update it
    client.put(f"/todos/{todo_id}", json={"title": "Updated"})
    
    # Get all todos and verify update persisted
    get_response = client.get("/todos")
    todos_list = get_response.json()
    assert len(todos_list) == 1
    assert todos_list[0]["title"] == "Updated"
    assert todos_list[0]["description"] == "Original"