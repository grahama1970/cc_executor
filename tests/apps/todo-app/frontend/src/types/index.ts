export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
}

export interface TodoList {
  id: number;
  user_id: number;
  title: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface TodoItem {
  id: number;
  list_id: number;
  title: string;
  description?: string;
  is_completed: boolean;
  priority: 'low' | 'medium' | 'high';
  due_date?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  tags: Tag[];
}

export interface TodoListWithItems extends TodoList {
  todo_items: TodoItem[];
}

export interface CreateTodoList {
  title: string;
  description?: string;
}

export interface CreateTodoItem {
  list_id: number;
  title: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high';
  due_date?: string;
  tag_ids?: number[];
}

export interface UpdateTodoItem {
  title?: string;
  description?: string;
  is_completed?: boolean;
  priority?: 'low' | 'medium' | 'high';
  due_date?: string;
  tag_ids?: number[];
}