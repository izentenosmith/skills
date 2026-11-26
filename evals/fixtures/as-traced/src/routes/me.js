const express = require('express');
const db = require('../db');

const router = express.Router();

// Preference keys the web app may set. Values are short strings.
const PREFERENCE_KEYS = ['theme', 'locale', 'reportSort'];

router.get('/me', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, email, display_name, role, preferences FROM users WHERE id = $1',
      [req.session.user.id],
    );
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

router.put('/me/preferences', async (req, res, next) => {
  try {
    const prefs = {};
    for (const key of PREFERENCE_KEYS) {
      const value = req.body[key];
      if (typeof value === 'string' && value.length <= 120) prefs[key] = value;
    }
    await db.query(
      'UPDATE users SET preferences = preferences || $1::jsonb WHERE id = $2',
      [JSON.stringify(prefs), req.session.user.id],
    );
    res.json(prefs);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
