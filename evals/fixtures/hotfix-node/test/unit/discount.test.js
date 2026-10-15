const test = require("node:test");
const assert = require("node:assert");
const { applyDiscount } = require("../../src/pricing/discount");

test("no discount leaves the amount unchanged", () => {
  assert.strictEqual(applyDiscount(1990, 0), 1990);
});

test("10% off a round amount", () => {
  assert.strictEqual(applyDiscount(1000, 10), 900);
});
