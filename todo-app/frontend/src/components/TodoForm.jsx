import React, { useState } from 'react'

function TodoForm({ onSubmit }) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    due_date: ''
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (\!formData.title.trim()) return
    
    const todoData = {
      ...formData,
      due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null
    }
    
    onSubmit(todoData)
    setFormData({
      title: '',
      description: '',
      priority: 'medium',
      due_date: ''
    })
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  return (
    <form className="todo-form" onSubmit={handleSubmit}>
      <input
        type="text"
        name="title"
        placeholder="What needs to be done?"
        value={formData.title}
        onChange={handleChange}
        className="todo-input"
        required
      />
      
      <textarea
        name="description"
        placeholder="Add description (optional)"
        value={formData.description}
        onChange={handleChange}
        className="todo-textarea"
        rows="2"
      />
      
      <div className="form-row">
        <select
          name="priority"
          value={formData.priority}
          onChange={handleChange}
          className="priority-select"
        >
          <option value="low">Low Priority</option>
          <option value="medium">Medium Priority</option>
          <option value="high">High Priority</option>
        </select>
        
        <input
          type="datetime-local"
          name="due_date"
          value={formData.due_date}
          onChange={handleChange}
          className="due-date-input"
        />
        
        <button type="submit" className="add-button">
          Add Todo
        </button>
      </div>
    </form>
  )
}

export default TodoForm
EOF < /dev/null