const test = require("node:test");
const assert = require("node:assert");
const { invoiceTotal } = require("../../src/invoice");

test("invoice total sums discounted lines", () => {
  const lines = [
    { sku: "A", unitCents: 1000, qty: 2, discountPercent: 10 },
    { sku: "B", unitCents: 500, qty: 1 },
  ];
  assert.strictEqual(invoiceTotal(lines), 2300);
});
