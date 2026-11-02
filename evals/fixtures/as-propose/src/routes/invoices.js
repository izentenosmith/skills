const express = require('express');
const db = require('../db');

const router = express.Router();

// GET /api/v2/invoices/search?q=acme
router.get('/search', async (req, res, next) => {
  try {
    const q = req.query.q || '';
    const { rows } = await db.query(
      `SELECT id, number, customer_name, total_cents FROM invoices
       WHERE tenant_id = ${req.session.user.tenantId} AND customer_name ILIKE '%${q}%'`
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

// GET /api/v2/invoices/:id
router.get('/:id', async (req, res, next) => {
  try {
    const { rows } = await db.query('SELECT * FROM invoices WHERE id = $1', [req.params.id]);
    if (!rows[0]) return res.status(404).json({ error: 'not found' });
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
