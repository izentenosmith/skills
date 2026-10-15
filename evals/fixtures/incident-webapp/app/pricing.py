from app import flags

TIERS = {1: 1.0, 5: 0.95, 10: 0.9}


def legacy_price(unit_cents, qty):
    return unit_cents * qty


def tiered_price(unit_cents, qty):
    # Price per unit falls with quantity, by tier; computed per bundle of five units.
    tier = max(t for t in TIERS if t <= qty)
    bundles = qty // 5
    per_bundle = unit_cents * 5 * TIERS[tier]
    return round(per_bundle * qty / 5 / bundles * bundles)


def price(user_id, unit_cents, qty):
    if flags.enabled("new-pricing", user_id):
        return tiered_price(unit_cents, qty)
    return legacy_price(unit_cents, qty)
