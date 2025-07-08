"""
Simple Todo List Manager

A basic Python class for managing todo items with add, remove, and list functionality.
"""

class TodoList:
    """A simple todo list manager with add, remove, and list methods."""
    
    def __init__(self):
        """Initialize an empty todo list."""
        self.todos = []
    
    def add(self, item: str) -> None:
        """
        Add a new item to the todo list.
        
        Args:
            item: The todo item to add
        """
        if not item or not item.strip():
            raise ValueError("Todo item cannot be empty")
        self.todos.append(item.strip())
    
    def remove(self, index: int) -> str:
        """
        Remove an item from the todo list by index.
        
        Args:
            index: The index of the item to remove (0-based)
            
        Returns:
            The removed item
            
        Raises:
            IndexError: If index is out of range
        """
        if not 0 <= index < len(self.todos):
            raise IndexError(f"Index {index} out of range. List has {len(self.todos)} items.")
        return self.todos.pop(index)
    
    def list(self) -> list[str]:
        """
        Get all todo items.
        
        Returns:
            A list of all todo items
        """
        return self.todos.copy()
    
    def __len__(self) -> int:
        """Return the number of todo items."""
        return len(self.todos)
    
    def __str__(self) -> str:
        """Return a string representation of the todo list."""
        if not self.todos:
            return "Todo list is empty"
        
        lines = ["Todo List:"]
        for i, item in enumerate(self.todos):
            lines.append(f"  {i}. {item}")
        return "\n".join(lines)


if __name__ == "__main__":
    # Usage demonstration
    todo = TodoList()
    
    # Add items
    todo.add("Buy groceries")
    todo.add("Write report")
    todo.add("Call dentist")
    
    # List items
    print(todo)
    print(f"\nTotal items: {len(todo)}")
    
    # Remove an item
    removed = todo.remove(1)
    print(f"\nRemoved: '{removed}'")
    
    # List again
    print(f"\n{todo}")
    
    # Get list as array
    items = todo.list()
    print(f"\nItems as list: {items}")