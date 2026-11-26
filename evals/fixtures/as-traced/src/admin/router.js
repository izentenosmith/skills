const express = require('express');
const db = require('../db');
const { requireRole } = require('../middleware/requireRole');

const router = express.Router();

// Support staff use the tenant directory too, so these read-only views sit above the admin-only guard.
router.get('/tenants', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, name, plan, seats, billing_email, created_at FROM tenants ORDER BY name',
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

router.get('/tenants/:tenantId/users', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, email, display_name, role, disabled, last_login_at FROM users WHERE tenant_id = $1 ORDER BY email',
      [req.params.tenantId],
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

// Everything below is admin-only.
router.use(requireRole('admin'));

router.post('/users/:userId/disable', async (req, res, next) => {
  try {
    const { rowCount } = await db.query('UPDATE users SET disabled = true WHERE id = $1', [req.params.userId]);
    if (!rowCount) return res.status(404).json({ error: 'not found' });
    console.info('admin disabled user', { by: req.session.user.id, userId: req.params.userId });
    res.sendStatus(204);
  } catch (err) {
    next(err);
  }
});

router.patch('/tenants/:tenantId/plan', async (req, res, next) => {
  try {
    const { plan, seats } = req.body;
    if (!['free', 'team', 'business'].includes(plan) || !Number.isInteger(seats) || seats < 1) {
      return res.status(400).json({ error: 'plan and seats required' });
    }
    await db.query('UPDATE tenants SET plan = $1, seats = $2 WHERE id = $3', [plan, seats, req.params.tenantId]);
    console.info('admin changed plan', { by: req.session.user.id, tenantId: req.params.tenantId, plan, seats });
    res.sendStatus(204);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
