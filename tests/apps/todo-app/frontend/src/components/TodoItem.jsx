import React, { useState } from 'react'
import { format } from 'date-fns'

function TodoItem({ todo, onToggle, onUpdate, onDelete }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState({
    title: todo.title,
    description: todo.description || '',
    priority: todo.priority,
    due_date: todo.due_date ? new Date(todo.due_date).toISOString().slice(0, 16) : ''
  })

  const handleSave = () => {
    const updates = {
      ...editData,
      due_date: editData.due_date ? new Date(editData.due_date).toISOString() : null
    }
    onUpdate(todo.id, updates)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditData({
      title: todo.title,
      description: todo.description || '',
      priority: todo.priority,
      due_date: todo.due_date ? new Date(todo.due_date).toISOString().slice(0, 16) : ''
    })
    setIsEditing(false)
  }

  const priorityClass = `priority-${todo.priority}`
  const completedClass = todo.completed ? 'completed' : ''

  if (isEditing) {
    return (
      <div className={`todo-item editing ${priorityClass}`}>
        <input
          type="text"
          value={editData.title}
          onChange={(e) => setEditData({...editData, title: e.target.value})}
          className="edit-input"
        />
        <textarea
          value={editData.description}
          onChange={(e) => setEditData({...editData, description: e.target.value})}
          className="edit-textarea"
          rows="2"
        />
        <div className="edit-row">
          <select
            value={editData.priority}
            onChange={(e) => setEditData({...editData, priority: e.target.value})}
            className="priority-select"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
          <input
            type="datetime-local"
            value={editData.due_date}
            onChange={(e) => setEditData({...editData, due_date: e.target.value})}
            className="due-date-input"
          />
          <button onClick={handleSave} className="save-btn">Save</button>
          <button onClick={handleCancel} className="cancel-btn">Cancel</button>
        </div>
      </div>
    )
  }

  return (
    <div className={`todo-item ${priorityClass} ${completedClass}`}>
      <div className="todo-header">
        <input
          type="checkbox"
          checked={todo.completed}
          onChange={() => onToggle(todo.id)}
          className="todo-checkbox"
        />
        <h3 className="todo-title">{todo.title}</h3>
        <div className="todo-actions">
          <button onClick={() => setIsEditing(true)} className="edit-btn">
            Edit
          </button>
          <button onClick={() => onDelete(todo.id)} className="delete-btn">
            Delete
          </button>
        </div>
      </div>
      
      {todo.description && (
        <p className="todo-description">{todo.description}</p>
      )}
      
      <div className="todo-meta">
        <span className={`priority-badge ${priorityClass}`}>
          {todo.priority}
        </span>
        {todo.due_date && (
          <span className="due-date">
            Due: {format(new Date(todo.due_date), 'MMM d, yyyy h:mm a')}
          </span>
        )}
        <span className="created-date">
          Created: {format(new Date(todo.created_at), 'MMM d, yyyy')}
        </span>
      </div>
    </div>
  )
}

export default TodoItem
EOF < /dev/null