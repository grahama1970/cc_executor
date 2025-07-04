from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
import uuid

app = FastAPI()

# In-memory storage
todos: Dict[str, dict] = {}

class TodoCreate(BaseModel):
    title: str
    description: str = ""

class TodoResponse(BaseModel):
    id: str
    title: str
    description: str
    created_at: datetime

class TodoUpdate(BaseModel):
    title: str = None
    description: str = None

@app.get("/todos", response_model=List[TodoResponse])
def get_todos():
    return list(todos.values())

@app.post("/todos", response_model=TodoResponse)
def create_todo(todo: TodoCreate):
    todo_id = str(uuid.uuid4())
    new_todo = {
        "id": todo_id,
        "title": todo.title,
        "description": todo.description,
        "created_at": datetime.now()
    }
    todos[todo_id] = new_todo
    return new_todo

@app.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: str, todo_update: TodoUpdate):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    todo = todos[todo_id]
    update_data = todo_update.dict(exclude_unset=True)
    
    if update_data:
        for field, value in update_data.items():
            todo[field] = value
    
    return todo

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: str):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    del todos[todo_id]
    return {"message": "Todo deleted successfully"}