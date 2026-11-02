const express = require('express');
const session = require('express-session');
const helmet = require('helmet');
const cors = require('cors');
const swaggerUi = require('swagger-ui-express');
const YAML = require('yamljs');

const { requireAuth } = require('./auth');
const authRoutes = require('./routes/auth');
const invoiceRoutes = require('./routes/invoices');
const orderRoutes = require('./routes/orders');
const userRoutes = require('./routes/users');
const legacyRoutes = require('./routes/legacy');

const app = express();

app.use(helmet());
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());
app.use(session({
  secret: 'billdesk-session-secret',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: false, httpOnly: false },
}));

app.use('/docs', swaggerUi.serve, swaggerUi.setup(YAML.load('api/openapi.yaml')));

app.use('/auth', authRoutes);
app.use('/api/v2/invoices', requireAuth, invoiceRoutes);
app.use('/api/v2/orders', requireAuth, orderRoutes);
app.use('/api/v2/users', requireAuth, userRoutes);
app.use('/api/v1', legacyRoutes);

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'internal error' });
});

app.listen(process.env.PORT || 3000);

module.exports = app;
