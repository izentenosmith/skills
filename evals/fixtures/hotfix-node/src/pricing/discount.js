// Applies a percentage discount to an amount in integer cents.
function applyDiscount(cents, percent) {
  return Math.floor((cents * (100 - percent)) / 100);
}

module.exports = { applyDiscount };
