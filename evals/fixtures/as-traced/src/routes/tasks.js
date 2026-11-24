const express = require('express');
const db = require('../db');
const { loadProject } = require('../middleware/loadProject');

const router = express.Router();
const STATUSES = new Set(['todo', 'doing', 'done']);

router.get('/projects/:projectId/tasks', loadProject, async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, title, status, due_date, assignee_email FROM tasks WHERE project_id = $1 AND tenant_id = $2 ORDER BY id',
      [req.project.id, req.session.user.tenantId],
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

router.post('/projects/:projectId/tasks', loadProject, async (req, res, next) => {
  try {
    const title = String(req.body.title || '').trim();
    if (!title || title.length > 300) return res.status(400).json({ error: 'title is required (max 300)' });
    const { rows } = await db.query(
      `INSERT INTO tasks (tenant_id, project_id, title, status, due_date)
       VALUES ($1, $2, $3, 'todo', $4) RETURNING id, title, status, due_date`,
      [req.session.user.tenantId, req.project.id, title, req.body.dueDate || null],
    );
    res.status(201).json(rows[0]);
  } catch (err) {
    next(err);
  }
});

router.patch('/projects/:projectId/tasks/:taskId', loadProject, async (req, res, next) => {
  try {
    const status = req.body.status;
    if (!STATUSES.has(status)) return res.status(400).json({ error: 'status must be todo, doing or done' });
    const { rowCount } = await db.query(
      'UPDATE tasks SET status = $1 WHERE id = $2 AND project_id = $3 AND tenant_id = $4',
      [status, req.params.taskId, req.project.id, req.session.user.tenantId],
    );
    if (!rowCount) return res.status(404).json({ error: 'not found' });
    res.sendStatus(204);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
