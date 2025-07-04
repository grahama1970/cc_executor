from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

# In-memory storage
todos = []
next_id = 1

# Pydantic models
class TodoCreate(BaseModel):
    title: str
    completed: bool = False

class TodoUpdate(BaseModel):
    title: str
    completed: bool

class Todo(BaseModel):
    id: int
    title: str
    completed: bool

@app.get("/todos", response_model=List[Todo])
async def get_todos():
    return todos

@app.post("/todos", response_model=Todo)
async def create_todo(todo: TodoCreate):
    global next_id
    new_todo = Todo(id=next_id, title=todo.title, completed=todo.completed)
    todos.append(new_todo.dict())
    next_id += 1
    return new_todo

@app.put("/todos/{todo_id}", response_model=Todo)
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    global todos
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            todos[i]["title"] = todo_update.title
            todos[i]["completed"] = todo_update.completed
            return Todo(**todos[i])
    raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    global todos
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            del todos[i]
            return {"message": f"Todo {todo_id} deleted"}
    raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)