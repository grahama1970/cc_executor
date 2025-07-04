from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# In-memory storage
todos: List[dict] = []
todo_counter = 0


class TodoCreate(BaseModel):
    title: str
    completed: bool = False


class Todo(BaseModel):
    id: int
    title: str
    completed: bool


@app.get("/todos", response_model=List[Todo])
async def get_todos():
    return todos


@app.post("/todos", response_model=Todo)
async def create_todo(todo: TodoCreate):
    global todo_counter
    todo_counter += 1
    new_todo = {
        "id": todo_counter,
        "title": todo.title,
        "completed": todo.completed
    }
    todos.append(new_todo)
    return new_todo


@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            todos.pop(i)
            return {"message": "Todo deleted successfully"}
    raise HTTPException(status_code=404, detail="Todo not found")