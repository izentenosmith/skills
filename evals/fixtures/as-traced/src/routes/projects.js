const express = require('express');
const db = require('../db');
const { loadProject } = require('../middleware/loadProject');

const router = express.Router();

// Sort keys the list accepts, mapped to columns. Anything else falls back to newest first.
const SORTABLE = new Map([
  ['name', 'p.name'],
  ['created', 'p.created_at'],
  ['updated', 'p.updated_at'],
]);

router.get('/projects', async (req, res, next) => {
  try {
    const order = SORTABLE.get(req.query.sort) || 'p.created_at';
    const dir = req.query.dir === 'asc' ? 'ASC' : 'DESC';
    const { rows } = await db.query(
      `SELECT p.id, p.name, p.created_at, p.updated_at FROM projects p
       WHERE p.tenant_id = $1 ORDER BY ${order} ${dir} LIMIT 200`,
      [req.session.user.tenantId],
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

router.post('/projects', async (req, res, next) => {
  try {
    const name = String(req.body.name || '').trim();
    if (!name || name.length > 200) return res.status(400).json({ error: 'name is required (max 200)' });
    const { rows } = await db.query(
      'INSERT INTO projects (tenant_id, name) VALUES ($1, $2) RETURNING id, name, created_at',
      [req.session.user.tenantId, name],
    );
    res.status(201).json(rows[0]);
  } catch (err) {
    next(err);
  }
});

router.get('/projects/:projectId', loadProject, (req, res) => {
  res.json(req.project);
});

router.delete('/projects/:projectId', loadProject, async (req, res, next) => {
  try {
    if (req.session.user.role !== 'owner') return res.status(403).json({ error: 'owners only' });
    await db.query('DELETE FROM projects WHERE id = $1 AND tenant_id = $2', [req.project.id, req.session.user.tenantId]);
    res.sendStatus(204);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
