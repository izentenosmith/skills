const express = require('express');
const db = require('../db');

const router = express.Router();

// GET /api/v2/orders
router.get('/', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, status, total_cents, created_at FROM orders WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 100',
      [req.session.user.tenantId]
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

// GET /api/v2/orders/:id
router.get('/:id', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, status, total_cents, created_at FROM orders WHERE id = $1 AND tenant_id = $2',
      [req.params.id, req.session.user.tenantId]
    );
    if (!rows[0]) return res.status(404).json({ error: 'not found' });
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
