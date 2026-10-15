const { applyDiscount } = require("./pricing/discount");

function cartPreview(items) {
  return items.map((i) => ({
    sku: i.sku,
    unitCents: applyDiscount(i.unitCents, i.discountPercent || 0),
    qty: i.qty,
  }));
}

module.exports = { cartPreview };
