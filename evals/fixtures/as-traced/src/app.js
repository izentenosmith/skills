const express = require('express');
const session = require('express-session');
const PgStore = require('connect-pg-simple')(session);
const helmet = require('helmet');

const db = require('./db');
const { requireAuth } = require('./middleware/requireAuth');
const authRoutes = require('./routes/auth');
const apiRoutes = require('./routes');
const billingHooks = require('./webhooks/billing');

const app = express();
app.set('trust proxy', 1);
app.use(helmet());

// Webhooks need the raw body for signature checks, so they mount before the JSON parser.
app.use('/hooks', billingHooks);

app.use(express.json({ limit: '100kb' }));
app.use(session({
  store: new PgStore({ pool: db.pool }),
  name: 'tl.sid',
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: { secure: true, httpOnly: true, sameSite: 'lax', maxAge: 8 * 60 * 60 * 1000 },
}));

app.use('/auth', authRoutes);
app.use('/api', requireAuth, apiRoutes);

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'internal error' });
});

module.exports = app;
