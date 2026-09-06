import React, { useEffect, useState } from 'react';

const API_BASE = (window.__ENV__ && window.__ENV__.API_BASE_URL) || '/api';

export default function App() {
  const [todos, setTodos] = useState([]);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTodos = async () => {
    try {
      setError(null);
      const res = await fetch(`${API_BASE}/todos`);
      if (!res.ok) throw new Error('Failed to load todos');
      setTodos(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTodos(); }, []);

  const addTodo = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    const res = await fetch(`${API_BASE}/todos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (res.ok) {
      setTitle('');
      fetchTodos();
    }
  };

  const toggleTodo = async (todo) => {
    await fetch(`${API_BASE}/todos/${todo._id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ completed: !todo.completed }),
    });
    fetchTodos();
  };

  const deleteTodo = async (id) => {
    await fetch(`${API_BASE}/todos/${id}`, { method: 'DELETE' });
    fetchTodos();
  };

  return (
    <div className="container">
      <h1>Self-Healing Todo</h1>
      <form onSubmit={addTodo} className="add-form">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What needs doing?"
        />
        <button type="submit">Add</button>
      </form>

      {loading && <p>Loading...</p>}
      {error && <p className="error">Backend unreachable: {error}</p>}

      <ul className="todo-list">
        {todos.map((todo) => (
          <li key={todo._id} className={todo.completed ? 'completed' : ''}>
            <span onClick={() => toggleTodo(todo)}>{todo.title}</span>
            <button className="delete" onClick={() => deleteTodo(todo._id)}>✕</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
