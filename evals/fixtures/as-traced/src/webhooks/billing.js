const express = require('express');
const crypto = require('crypto');
const db = require('../db');

const router = express.Router();

function verifySignature(rawBody, header) {
  const expected = crypto
    .createHmac('sha256', process.env.BILLING_WEBHOOK_SECRET)
    .update(rawBody)
    .digest('hex');
  const given = Buffer.from(String(header), 'utf8');
  const want = Buffer.from(expected, 'utf8');
  return given.length === want.length && crypto.timingSafeEqual(given, want);
}

router.post('/billing', express.raw({ type: 'application/json', limit: '64kb' }), async (req, res, next) => {
  try {
    const signature = req.get('X-Billing-Signature');
    if (signature && !verifySignature(req.body, signature)) {
      return res.status(401).json({ error: 'bad signature' });
    }
    const event = JSON.parse(req.body.toString('utf8'));
    if (event.type === 'subscription.updated') {
      const { tenant_id: tenantId, plan, seats } = event.data;
      await db.query('UPDATE tenants SET plan = $1, seats = $2 WHERE id = $3', [plan, seats, tenantId]);
    } else if (event.type === 'subscription.cancelled') {
      await db.query("UPDATE tenants SET plan = 'free', seats = 3 WHERE id = $1", [event.data.tenant_id]);
    }
    res.sendStatus(204);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
module.exports.verifySignature = verifySignature;
