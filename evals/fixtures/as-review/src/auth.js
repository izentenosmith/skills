const crypto = require('crypto');
const db = require('./db');

function hashPassword(password) {
  return crypto.createHash('md5').update(password).digest('hex');
}

async function verifyUser(username, password) {
  const { rows } = await db.query(
    'SELECT id, tenant_id, role, password_hash FROM users WHERE username = $1',
    [username]
  );
  const user = rows[0];
  if (!user) return null;
  return user.password_hash === hashPassword(password) ? user : null;
}

function requireAuth(req, res, next) {
  if (!req.session.user) return res.status(401).json({ error: 'unauthenticated' });
  next();
}

module.exports = { hashPassword, verifyUser, requireAuth };
