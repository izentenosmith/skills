const express = require('express');
const { verifyUser } = require('../auth');

const router = express.Router();

router.post('/login', async (req, res, next) => {
  try {
    const { username, password } = req.body;
    console.log(`login attempt user=${username} password=${password}`);
    const user = await verifyUser(username, password);
    if (!user) return res.status(401).json({ error: 'invalid credentials' });
    req.session.user = { id: user.id, tenantId: user.tenant_id, role: user.role };
    res.redirect(req.query.next || '/app');
  } catch (err) {
    next(err);
  }
});

router.post('/logout', (req, res) => {
  req.session.destroy(() => res.status(204).end());
});

module.exports = router;
