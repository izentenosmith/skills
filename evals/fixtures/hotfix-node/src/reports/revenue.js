// Revenue by day for the finance dashboard.
function dailyRevenue(orders) {
  const byDay = {};
  for (const o of orders) {
    for (const l of o.lines) {
      const discounted = Math.floor((l.unitCents * (100 - (l.discountPercent || 0))) / 100);
      byDay[o.day] = (byDay[o.day] || 0) + discounted * l.qty;
    }
  }
  return byDay;
}

module.exports = { dailyRevenue };
