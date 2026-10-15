const { applyDiscount } = require("./pricing/discount");

// lines: [{ sku, unitCents, qty, discountPercent }]
function invoiceTotal(lines) {
  return lines.reduce((sum, l) => sum + applyDiscount(l.unitCents, l.discountPercent || 0) * l.qty, 0);
}

module.exports = { invoiceTotal };
