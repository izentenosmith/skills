// API v1 — kept for the old mobile app.
const express = require('express');
const db = require('../db');

const router = express.Router();

// GET /api/v1/invoices?tenant=42
router.get('/invoices', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, number, customer_name, total_cents FROM invoices WHERE tenant_id = $1',
      [req.query.tenant]
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

// GET /api/v1/invoices/:id
router.get('/invoices/:id', async (req, res, next) => {
  try {
    const { rows } = await db.query('SELECT * FROM invoices WHERE id = $1', [req.params.id]);
    res.json(rows[0] || {});
  } catch (err) {
    next(err);
  }
});

module.exports = router;
