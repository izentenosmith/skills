const test = require('node:test');
const assert = require('node:assert');
const crypto = require('crypto');

process.env.BILLING_WEBHOOK_SECRET = 'test-secret';
const { verifySignature } = require('../src/webhooks/billing');

const body = Buffer.from(JSON.stringify({ type: 'subscription.updated', data: { tenant_id: 1, plan: 'team', seats: 5 } }));
const sign = (b) => crypto.createHmac('sha256', 'test-secret').update(b).digest('hex');

test('accepts a correctly signed body', () => {
  assert.strictEqual(verifySignature(body, sign(body)), true);
});

test('rejects a tampered body', () => {
  const tampered = Buffer.from(body.toString().replace('"seats":5', '"seats":500'));
  assert.strictEqual(verifySignature(tampered, sign(body)), false);
});

test('rejects a signature of the wrong length', () => {
  assert.strictEqual(verifySignature(body, 'abc'), false);
});
