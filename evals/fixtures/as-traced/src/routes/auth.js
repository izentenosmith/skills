const express = require('express');
const rateLimit = require('express-rate-limit');
const db = require('../db');
const { verifyPassword } = require('../auth/password');

const router = express.Router();
const loginLimiter = rateLimit({ windowMs: 15 * 60 * 1000, limit: 10 });

router.post('/login', loginLimiter, async (req, res, next) => {
  try {
    const { email, password } = req.body || {};
    const { rows } = await db.query(
      'SELECT id, tenant_id, email, role, password_hash FROM users WHERE email = $1 AND disabled = false',
      [String(email || '').toLowerCase()],
    );
    const user = rows[0];
    if (!user || !(await verifyPassword(String(password || ''), user.password_hash))) {
      console.warn('login failed', { email });
      return res.status(401).json({ error: 'invalid credentials' });
    }
    req.session.regenerate((err) => {
      if (err) return next(err);
      req.session.user = { id: user.id, tenantId: user.tenant_id, email: user.email, role: user.role };
      res.json({ id: user.id, email: user.email, role: user.role });
    });
  } catch (err) {
    next(err);
  }
});

router.post('/logout', (req, res) => {
  req.session.destroy(() => res.sendStatus(204));
});

module.exports = router;
