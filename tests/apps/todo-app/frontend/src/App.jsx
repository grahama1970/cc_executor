import React, { useState, useEffect } from 'react'
import axios from 'axios'
import TodoList from './components/TodoList'
import TodoForm from './components/TodoForm'
import './App.css'

const API_URL = '/api/todos'

function App() {
  const [todos, setTodos] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetchTodos()
  }, [])

  const fetchTodos = async () => {
    try {
      const response = await axios.get(API_URL)
      setTodos(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching todos:', error)
      setLoading(false)
    }
  }

  const addTodo = async (todoData) => {
    try {
      const response = await axios.post(API_URL, todoData)
      setTodos([...todos, response.data])
    } catch (error) {
      console.error('Error adding todo:', error)
    }
  }

  const updateTodo = async (id, updates) => {
    try {
      const response = await axios.put(`${API_URL}/${id}`, updates)
      setTodos(todos.map(todo => todo.id === id ? response.data : todo))
    } catch (error) {
      console.error('Error updating todo:', error)
    }
  }

  const toggleTodo = async (id) => {
    try {
      const response = await axios.patch(`${API_URL}/${id}/toggle`)
      setTodos(todos.map(todo => todo.id === id ? response.data : todo))
    } catch (error) {
      console.error('Error toggling todo:', error)
    }
  }

  const deleteTodo = async (id) => {
    try {
      await axios.delete(`${API_URL}/${id}`)
      setTodos(todos.filter(todo => todo.id \!== id))
    } catch (error) {
      console.error('Error deleting todo:', error)
    }
  }

  const filteredTodos = todos.filter(todo => {
    if (filter === 'active') return \!todo.completed
    if (filter === 'completed') return todo.completed
    return true
  })

  return (
    <div className="app">
      <header className="app-header">
        <h1>Todo App</h1>
      </header>
      
      <main className="app-main">
        <TodoForm onSubmit={addTodo} />
        
        <div className="filter-buttons">
          <button 
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All ({todos.length})
          </button>
          <button 
            className={filter === 'active' ? 'active' : ''}
            onClick={() => setFilter('active')}
          >
            Active ({todos.filter(t => \!t.completed).length})
          </button>
          <button 
            className={filter === 'completed' ? 'active' : ''}
            onClick={() => setFilter('completed')}
          >
            Completed ({todos.filter(t => t.completed).length})
          </button>
        </div>

        {loading ? (
          <div className="loading">Loading...</div>
        ) : (
          <TodoList 
            todos={filteredTodos}
            onToggle={toggleTodo}
            onUpdate={updateTodo}
            onDelete={deleteTodo}
          />
        )}
      </main>
    </div>
  )
}

export default App
EOF < /dev/null