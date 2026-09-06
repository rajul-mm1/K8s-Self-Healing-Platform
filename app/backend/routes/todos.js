const express = require('express');
const Todo = require('../models/Todo');

const router = express.Router();

router.get('/', async (req, res) => {
  const todos = await Todo.find().sort({ createdAt: -1 });
  res.json(todos);
});

router.post('/', async (req, res) => {
  const { title } = req.body;
  if (!title || !title.trim()) {
    return res.status(400).json({ error: 'title is required' });
  }
  const todo = await Todo.create({ title: title.trim() });
  res.status(201).json(todo);
});

router.patch('/:id', async (req, res) => {
  const { completed, title } = req.body;
  const update = {};
  if (completed !== undefined) update.completed = completed;
  if (title !== undefined) update.title = title;

  const todo = await Todo.findByIdAndUpdate(req.params.id, update, { new: true });
  if (!todo) return res.status(404).json({ error: 'not found' });
  res.json(todo);
});

router.delete('/:id', async (req, res) => {
  const todo = await Todo.findByIdAndDelete(req.params.id);
  if (!todo) return res.status(404).json({ error: 'not found' });
  res.status(204).send();
});

module.exports = router;
