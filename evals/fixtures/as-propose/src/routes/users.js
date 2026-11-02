const express = require('express');
const _ = require('lodash');
const db = require('../db');

const router = express.Router();

// GET /api/v2/users/me
router.get('/me', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, username, email, role, tenant_id FROM users WHERE id = $1',
      [req.session.user.id]
    );
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

// PATCH /api/v2/users/me
router.patch('/me', async (req, res, next) => {
  try {
    const { rows } = await db.query('SELECT * FROM users WHERE id = $1', [req.session.user.id]);
    const user = Object.assign(rows[0], req.body);
    await db.query(
      'UPDATE users SET email = $1, display_name = $2, role = $3 WHERE id = $4',
      [user.email, user.display_name, user.role, user.id]
    );
    res.json(_.omit(user, ['password_hash']));
  } catch (err) {
    next(err);
  }
});

module.exports = router;
