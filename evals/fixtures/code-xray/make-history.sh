#!/usr/bin/env bash
# Build the code-xray fixture's git repository: Shopwell, a stdlib-Python shop
# backend (orders, subscriptions, billing, a web front end, an API layer and a
# legacy reporting module), with twelve months of history (2025-11-03 .. 2026-10-27),
# five fixed authors and about 300 commits. The plants are described in README.md
# (kept out of the run) and in ../code-xray.answers.md.
# Idempotent and deterministic: removes and rebuilds repo/ each time, from a fixed seed.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf repo && mkdir repo && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false
git config tag.gpgsign false

python3 -I - <<'PY'
import datetime
import os
import pathlib
import random
import subprocess

R = random.Random(51)
ROOT = pathlib.Path.cwd()
AUTHORS = {"ana": "Ana Rivera", "ben": "Ben Okafor", "chen": "Chen Wei", "dana": "Dana Kowalski",
           "elif": "Elif Demir"}
DANA_LAST = datetime.datetime(2026, 3, 18, 16, 40)
LICENSE_PY = "# Copyright 2026 Shopwell Ltd. Licensed under the Apache License, Version 2.0.\n"
LICENSE_JS = "// Copyright 2026 Shopwell Ltd. Licensed under the Apache License, Version 2.0.\n"
LICENSE_CSS = "/* Copyright 2026 Shopwell Ltd. Licensed under the Apache License, Version 2.0. */\n"
LICENSE_HTML = "<!-- Copyright 2026 Shopwell Ltd. Licensed under the Apache License, Version 2.0. -->\n"
state = {"licensed": False}


def header(path):
    if not state["licensed"]:
        return ""
    if path.endswith("_pb2.py"):
        return ""
    return {".py": LICENSE_PY, ".js": LICENSE_JS, ".proto": LICENSE_JS, ".css": LICENSE_CSS,
            ".html": LICENSE_HTML}.get(
        pathlib.PurePosixPath(path).suffix, "")


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def commit(when, who, msg):
    name = AUTHORS[who]
    email = name.lower().replace(" ", ".") + "@example.invalid"
    iso = when.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    env = dict(os.environ, GIT_AUTHOR_DATE=iso, GIT_COMMITTER_DATE=iso, GIT_AUTHOR_NAME=name,
               GIT_COMMITTER_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_EMAIL=email)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-q", "--no-verify", "-m", msg], env=env, check=True)


def day(s, hour=None):
    d = datetime.datetime.strptime(s, "%Y-%m-%d")
    return d.replace(hour=hour if hour is not None else R.randint(9, 17), minute=R.randint(0, 59))


def spread(start, end, n, power=1.0):
    """n datetimes between two dates; power > 1 packs them toward the end."""
    a, b = day(start, 9), day(end, 9)
    span = (b - a).total_seconds()
    out = []
    for i in range(n):
        f = ((i + 0.5) / n) ** (1 / power)
        t = a + datetime.timedelta(seconds=span * f)
        out.append(t.replace(hour=R.randint(9, 17), minute=R.randint(0, 59)))
    return out


# ------------------------------------------------------------------ orders/pricing.py (the real hotspot)

class Pricing:
    CATS = ["shoes", "outerwear", "bags", "kids", "home", "beauty", "sport", "gifts"]

    def __init__(self):
        self.rules = []          # each: dict(code, th, depth, cat, pct)
        self.shipping = ['    if region == "EU":', '        cost += Decimal("4.90")']
        self.tier = ['    if tier == "gold":', '        rate = Decimal("0.05")']
        self.quote_extra = []
        self.subtotal_extra = []
        self.n = 0
        for _ in range(3):
            self.add_rule(depth=2)

    def add_rule(self, depth):
        self.n += 1
        self.rules.append({"code": f"PROMO{self.n:03d}", "th": R.choice([25, 40, 50, 75, 100, 120]),
                           "depth": depth, "cat": R.choice(self.CATS), "pct": R.choice([5, 10, 15, 20, 25])})

    def tweak_rule(self):
        r = R.choice(self.rules)
        r["th"] += R.choice([5, 10, 15])

    def rule_lines(self, r):
        ind = lambda k: "    " * k
        out = [f'{ind(2)}if promo.code == "{r["code"]}":',
               f'{ind(3)}if subtotal >= Decimal("{r["th"]}"):',
               f"{ind(4)}applied.append(promo.code)"]
        k = 4
        if r["depth"] >= 3:
            out.append(f"{ind(k)}for line in lines:")
            k += 1
        if r["depth"] >= 4:
            out.append(f'{ind(k)}if line.category == "{r["cat"]}":')
            k += 1
        if r["depth"] >= 5:
            out.append(f'{ind(k)}if customer.tier in ("gold", "staff"):')
            k += 1
        if r["depth"] >= 6:
            out.append(f"{ind(k)}if not line.on_sale and line.qty >= 2:")
            k += 1
        target = "line.total" if r["depth"] >= 3 else "subtotal"
        out.append(f'{ind(k)}discount += {target} * Decimal("0.{r["pct"]:02d}")')
        return out

    def render(self):
        rules = [ln for r in self.rules for ln in self.rule_lines(r)]
        return header("x.py") + "\n".join([
            '"""Order pricing: line totals, promotions, shipping and the final quote."""',
            "from decimal import Decimal, ROUND_HALF_UP",
            "",
            "TWO_PLACES = Decimal(\"0.01\")",
            "",
            "",
            "def round_money(amount):",
            "    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)",
            "",
            "",
            "def compute_line_total(line):",
            "    total = Decimal(line.unit_price) * line.qty",
            "    if line.on_sale:",
            "        total = total * Decimal(\"0.90\")",
            "    return round_money(total)",
            "",
            "",
            "def compute_subtotal(lines):",
            "    subtotal = Decimal(\"0\")",
            "    for line in lines:",
            "        subtotal += compute_line_total(line)",
            *self.subtotal_extra,
            "    return round_money(subtotal)",
            "",
            "",
            "def apply_promotions(lines, promos, customer, subtotal):",
            "    \"\"\"Return (discount, applied codes) for the active promotions.\"\"\"",
            "    discount = Decimal(\"0\")",
            "    applied = []",
            "    for promo in promos:",
            "        if not promo.active:",
            "            continue",
            *rules,
            "    if discount > subtotal:",
            "        discount = subtotal",
            "    return round_money(discount), applied",
            "",
            "",
            "def price_for_tier(tier, subtotal):",
            "    rate = Decimal(\"0\")",
            *self.tier,
            "    return round_money(subtotal * rate)",
            "",
            "",
            "def apply_shipping(region, subtotal):",
            "    cost = Decimal(\"0\")",
            *self.shipping,
            "    if subtotal >= Decimal(\"80\"):",
            "        cost = Decimal(\"0\")",
            "    return round_money(cost)",
            "",
            "",
            "def quote(lines, promos, customer, region):",
            "    subtotal = compute_subtotal(lines)",
            "    discount, applied = apply_promotions(lines, promos, customer, subtotal)",
            "    tier = price_for_tier(customer.tier, subtotal - discount)",
            "    shipping = apply_shipping(region, subtotal - discount)",
            *self.quote_extra,
            "    total = subtotal - discount - tier + shipping",
            "    return {\"subtotal\": subtotal, \"discount\": discount, \"tier\": tier,",
            "            \"shipping\": shipping, \"total\": round_money(total), \"applied\": applied}",
            "",
        ])

    def other_change(self, k):
        regions = ["UK", "CH", "NO", "US", "CA", "AU", "JP", "IS", "TR", "MX", "BR", "ZA", "NZ", "SG"]
        if k % 4 == 0:
            reg = regions[k % len(regions)]
            self.shipping += [f'    if region == "{reg}":', f'        cost += Decimal("{R.randint(5, 19)}.{R.choice(["00", "50", "90"])}")']
            return "apply_shipping"
        if k % 4 == 1:
            tier = ["silver", "staff", "partner", "student", "vip"][k % 5]
            self.tier += [f'    if tier == "{tier}":', f'        rate = Decimal("0.{R.randint(1, 9):02d}")']
            return "price_for_tier"
        if k % 4 == 2:
            self.quote_extra += [f'    if region == "{["IS", "NO", "CH"][k % 3]}" and customer.tier == "staff":',
                                 '        shipping = Decimal("0")']
            return "quote"
        extra = ["gift_wrap", "deposit", "bottle_return", "voucher_fee", "insurance"][k % 5]
        self.subtotal_extra += [f'        if getattr(line, "{extra}", None):',
                                f"            subtotal -= Decimal(line.{extra})"]
        return "compute_subtotal"


class CheckoutJs:
    def __init__(self):
        self.preview = []
        self.summary = ["  rows.push(['Subtotal', formatMoney(q.subtotal)]);"]
        self.misc = ["  button.classList.add('is-busy');"]

    def mirror(self, pricing):
        self.preview = []
        for r in pricing.rules:
            cond = f"q.subtotal >= {r['th']}"
            if r["depth"] >= 4:
                cond += f" && cart.lines.some(l => l.category === '{r['cat']}')"
            if r["depth"] >= 5:
                cond += " && ['gold', 'staff'].includes(cart.customer.tier)"
            self.preview += [f"    if (promo.code === '{r['code']}') {{",
                             f"      if ({cond}) {{",
                             f"        discount += q.subtotal * 0.{r['pct']:02d};",
                             "        applied.push(promo.code);",
                             "      }",
                             "    }"]

    def render(self):
        return header("x.js") + "\n".join([
            "// Checkout page: live price preview and submit.",
            "'use strict';",
            "",
            "function formatMoney(n) {",
            "  return (Math.round(n * 100) / 100).toFixed(2);",
            "}",
            "",
            "function applyPromotionsPreview(cart, promos, q) {",
            "  // Mirrors orders/pricing.py apply_promotions so the page can show the discount before submit.",
            "  let discount = 0;",
            "  const applied = [];",
            "  for (const promo of promos) {",
            "    if (!promo.active) continue;",
            *self.preview,
            "  }",
            "  return { discount: Math.min(discount, q.subtotal), applied };",
            "}",
            "",
            "function renderSummary(q) {",
            "  const rows = [];",
            *self.summary,
            "  rows.push(['Total', formatMoney(q.total)]);",
            "  return rows;",
            "}",
            "",
            "function onSubmit(event) {",
            "  const button = event.target.querySelector('button[type=submit]');",
            *self.misc,
            "  return true;",
            "}",
            "",
            "module.exports = { formatMoney, applyPromotionsPreview, renderSummary, onSubmit };",
            "",
        ])


# ------------------------------------------------------------------ the discount clone twins

class Discounts:
    def __init__(self):
        self.rules = [("WELCOME10", "percent", 10), ("SPRING5", "fixed", 5), ("FRIEND15", "percent", 15)]
        self.clamp = {"orders": False, "subscriptions": False}
        self.notes = {"orders": [], "subscriptions": []}
        self.n = 0

    def add_rule(self):
        self.n += 1
        kind = R.choice(["percent", "fixed"])
        self.rules.append((f"CODE{self.n:02d}", kind, R.choice([5, 10, 12, 15, 20, 25])))

    def tweak(self):
        i = R.randrange(len(self.rules))
        code, kind, v = self.rules[i]
        self.rules[i] = (code, kind, v + R.choice([1, 2, 5]))

    def render(self, pkg):
        what = "one-off orders" if pkg == "orders" else "subscription renewals"
        body = []
        for code, kind, v in self.rules:
            body.append(f'    if code == "{code}":')
            if kind == "percent":
                body.append(f'        amount = subtotal * Decimal("{v}") / 100')
            else:
                body.append(f'        amount = Decimal("{v}")')
        return header("x.py") + "\n".join([
            f'"""Discount codes for {what}."""',
            "from decimal import Decimal",
            "",
            "STACKABLE = {\"WELCOME10\", \"FRIEND15\"}",
            "",
            "",
            "def normalise(code):",
            "    return (code or \"\").strip().upper()",
            "",
            "",
            "def is_stackable(code):",
            "    return normalise(code) in STACKABLE",
            "",
            "",
            "def discount_for(code, subtotal, customer=None):",
            "    \"\"\"The discount a code gives on this subtotal, as a Decimal.\"\"\"",
            "    code = normalise(code)",
            "    amount = Decimal(\"0\")",
            "    if customer is not None and getattr(customer, \"blocked\", False):",
            "        return amount",
            *body,
            *self.notes[pkg],
            *(["    amount = min(amount, subtotal)"] if self.clamp[pkg] else []),
            "    return amount.quantize(Decimal(\"0.01\"))",
            "",
            "",
            "def describe(code):",
            "    code = normalise(code)",
            "    for known in (" + ", ".join(f'"{c}"' for c, _, _ in self.rules) + "):",
            "        if known == code:",
            "            return f\"Code {code}\"",
            "    return \"Unknown code\"",
            "",
        ])


# ------------------------------------------------------------------ billing/tax.py (knowledge loss)

class Tax:
    def __init__(self):
        self.regions = []
        self.tail = []
        for reg in ["DE", "FR", "NL", "ES", "IT"]:
            self.add(reg)

    def add(self, reg):
        rate = R.choice([19, 20, 21, 22, 23, 25])
        reduced = R.choice([5, 7, 9, 10])
        self.regions.append((reg, rate, reduced))

    def render(self):
        out = [header("x.py") + '"""VAT and sales tax by region. Rates are percentages."""',
               "from decimal import Decimal, ROUND_HALF_UP", "", ""]
        for reg, rate, reduced in self.regions:
            out += [f"def _rate_{reg.lower()}(category, b2b=False):",
                    "    if b2b:",
                    "        return Decimal(\"0\")",
                    "    if category in (\"food\", \"books\", \"kids\"):",
                    f"        return Decimal(\"{reduced}\")",
                    "    if category == \"digital\":",
                    "        if b2b:",
                    "            return Decimal(\"0\")",
                    f"        return Decimal(\"{rate}\")",
                    f"    return Decimal(\"{rate}\")",
                    "", ""]
        out += ["RATES = {"]
        out += [f'    "{reg}": _rate_{reg.lower()},' for reg, _, _ in self.regions]
        out += ["}", "", "",
                "def tax_for(region, category, amount, b2b=False):",
                "    fn = RATES.get(region)",
                "    if fn is None:",
                "        raise KeyError(f\"no tax rules for {region}\")",
                "    rate = fn(category, b2b)",
                "    return (Decimal(amount) * rate / 100).quantize(Decimal(\"0.01\"), rounding=ROUND_HALF_UP)",
                *self.tail, ""]
        return "\n".join(out)


# ------------------------------------------------------------------ api/schema_pb2.py (generated churn)

class Proto:
    def __init__(self):
        self.messages = ["Order", "OrderLine", "Quote", "Customer", "Address", "Promotion"]
        self.version = 0

    def proto(self):
        out = [header("x.proto") + 'syntax = "proto3";', "", "package shopwell.api;", ""]
        for i, m in enumerate(self.messages):
            out += [f"message {m} {{", "  string id = 1;", f"  int64 updated_at = {2 + i % 3};", "}", ""]
        return "\n".join(out)

    def pb2(self):
        self.version += 1
        rr = random.Random(self.version * 7919)
        blob = "".join(rr.choice("0123456789abcdef") for _ in range(96))
        out = ["# -*- coding: utf-8 -*-",
               "# Generated by the protocol buffer compiler.  DO NOT EDIT!",
               "# source: api/schema.proto",
               '"""Generated protocol buffer code."""',
               "from google.protobuf import descriptor as _descriptor",
               "from google.protobuf import descriptor_pool as _descriptor_pool",
               "from google.protobuf import symbol_database as _symbol_database",
               "from google.protobuf.internal import builder as _builder",
               "",
               "_sym_db = _symbol_database.Default()",
               "",
               f"DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\\n\\x10{blob}')",
               "",
               "_globals = globals()",
               "_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)",
               "_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'api.schema_pb2', _globals)",
               "if _descriptor._USE_C_DESCRIPTORS == False:",
               "  DESCRIPTOR._options = None"]
        off = 40 + rr.randint(0, 30)
        for i in range(260 + 3 * len(self.messages)):
            m = self.messages[i % len(self.messages)].upper()
            out.append(f"  _globals['_{m}_F{i:03d}']._serialized_start={off}")
            off += rr.randint(20, 90)
            out.append(f"  _globals['_{m}_F{i:03d}']._serialized_end={off}")
        out.append("# @@protoc_insertion_point(module_scope)")
        return "\n".join(out) + "\n"


# ------------------------------------------------------------------ legacy/report_builder.py (the cold giant)

def report_builder():
    rr = random.Random(1999)
    sections = ["sales", "returns", "inventory", "margins", "suppliers", "regions", "channels", "staff_hours",
                "promotions", "shipping", "refunds", "loyalty", "gift_cards", "tax", "payouts", "chargebacks",
                "warehouses", "forecast", "seasonality", "cohorts", "vendors", "audit"]
    out = ['"""Monthly and quarterly management reports (ported from the 2019 PHP back office)."""',
           "import csv", "import io", "", "",
           "def _fmt(value, kind):",
           "    if kind == \"money\":",
           "        return f\"{value:,.2f}\"",
           "    if kind == \"pct\":",
           "        return f\"{value:.1f}%\"",
           "    return str(value)", "", ""]
    for s in sections:
        cols = rr.sample(["region", "channel", "category", "store", "month", "week", "sku", "vendor"], 3)
        out += [f"def build_{s}_section(rows, opts):",
                f"    \"\"\"The {s.replace('_', ' ')} section.\"\"\"",
                "    out = []",
                "    totals = {}",
                "    for row in rows:",
                f"        if row.get(\"section\") == \"{s}\":",
                f"            if opts.get(\"by_{cols[0]}\"):",
                f"                key = row.get(\"{cols[0]}\")",
                "                if key is not None:",
                "                    if key not in totals:",
                "                        totals[key] = 0",
                "                    if row.get(\"amount\"):",
                "                        if opts.get(\"exclude_returns\") and row.get(\"is_return\"):",
                "                            if opts.get(\"strict\"):",
                "                                continue",
                "                            else:",
                "                                totals[key] -= row[\"amount\"]",
                "                        else:",
                "                            totals[key] += row[\"amount\"]",
                "                else:",
                "                    if opts.get(\"include_unknown\"):",
                "                        totals.setdefault(\"unknown\", 0)",
                "                        totals[\"unknown\"] += row.get(\"amount\", 0)",
                f"            elif opts.get(\"by_{cols[1]}\"):",
                f"                key = (row.get(\"{cols[1]}\"), row.get(\"{cols[2]}\"))",
                "                if all(k is not None for k in key):",
                "                    for part in key:",
                "                        if part not in totals:",
                "                            totals[part] = 0",
                "                        if row.get(\"amount\"):",
                "                            if row.get(\"currency\", \"EUR\") != \"EUR\":",
                "                                if opts.get(\"fx\"):",
                "                                    rate = opts[\"fx\"].get(row[\"currency\"], 1)",
                "                                    totals[part] += row[\"amount\"] * rate",
                "                                else:",
                "                                    totals[part] += row[\"amount\"]",
                "                            else:",
                "                                totals[part] += row[\"amount\"]",
                "            else:",
                "                totals.setdefault(\"all\", 0)",
                "                totals[\"all\"] += row.get(\"amount\", 0)",
                "    for key in sorted(totals, key=str):",
                "        value = totals[key]",
                "        if opts.get(\"hide_zero\") and not value:",
                "            continue",
                "        out.append((key, _fmt(value, opts.get(\"kind\", \"money\"))))",
                "    return out", "", ""]
    out += ["def build_report(rows, opts):",
            "    report = []"]
    for s in sections:
        out += [f"    if opts.get(\"{s}\", True):",
                f"        report.append((\"{s}\", build_{s}_section(rows, opts)))"]
    out += ["    return report", "", "",
            "def to_csv(report):",
            "    buf = io.StringIO()",
            "    w = csv.writer(buf)",
            "    for name, lines in report:",
            "        for key, value in lines:",
            "            w.writerow([name, key, value])",
            "    return buf.getvalue()", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ the filler modules

FILLER_PKGS = {
    "orders": ["cart", "checkout", "models", "validation", "events", "fulfilment"],
    "subscriptions": ["plans", "renewals", "models", "proration"],
    "billing": ["invoices", "payments", "refunds", "currency"],
    "web": ["views", "routes", "forms"],
    "api": ["handlers", "serializers", "auth"],
    "inventory": ["stock", "warehouses", "reservations", "suppliers"],
    "shipping": ["rates", "carriers", "labels", "tracking"],
    "customers": ["accounts", "addresses", "loyalty", "preferences"],
    "notifications": ["email", "sms", "templates", "queue"],
    "catalog": ["products", "categories", "search", "images"],
    "reports": ["daily", "finance", "exports"],
    "utils": ["money", "dates", "ids", "logging_setup", "retry"],
    "config": ["settings", "defaults"],
    "legacy": ["csv_export"],
}
TESTS = ["cart", "checkout", "invoices", "refunds", "renewals", "stock", "reservations", "shipping_rates",
         "carriers", "accounts", "loyalty", "email", "search", "products", "money", "dates", "ids", "retry",
         "daily_report", "handlers", "serializers", "plans", "proration", "payments", "currency"]
filler = {}     # path -> text


def filler_module(pkg, mod):
    return (f'"""{pkg}.{mod}: {mod.replace("_", " ")} for the {pkg} package."""\n\n\n'
            f"def describe():\n    return \"{pkg}.{mod}\"\n")


def filler_test(name):
    return ("import unittest\n\n\n"
            f"class Test{name.title().replace('_', '')}(unittest.TestCase):\n"
            "    def test_placeholder(self):\n"
            "        self.assertTrue(True)\n")


fn_counter = [0]


def filler_edit(path):
    fn_counter[0] += 1
    k = fn_counter[0]
    text = filler[path]
    if path.startswith("tests/"):
        text += (f"\n    def test_case_{k}(self):\n"
                 f"        self.assertEqual({k} % 7, {k % 7})\n")
    elif path.endswith(".js"):
        text += f"\nfunction helper{k}(x) {{\n  return x + {k % 9};\n}}\n"
    elif path.endswith(".html"):
        text = text.replace("</main>", f"  <p class=\"note-{k}\"></p>\n</main>")
    elif path.endswith(".css"):
        text += f"\n.note-{k} {{ margin: {k % 5}px; }}\n"
    elif path.endswith(".md"):
        text += f"\n- Note {k}: see the runbook.\n"
    else:
        arg = R.choice(["value", "items", "order", "record", "payload"])
        text += (f"\n\ndef helper_{k}({arg}):\n"
                 f"    if not {arg}:\n"
                 f"        return None\n"
                 f"    return {arg}\n")
    filler[path] = text


def put_filler(path, text):
    filler[path] = text
    write(path, text)


def flush(paths):
    for p in paths:
        write(p, filler[p])


# ------------------------------------------------------------------ build

pricing, checkout, disc, tax, proto = Pricing(), CheckoutJs(), Discounts(), Tax(), Proto()
checkout.mirror(pricing)


def w_pricing():
    write("orders/pricing.py", pricing.render())


def w_checkout():
    write("web/static/checkout.js", checkout.render())


def w_disc(pkg):
    write(f"{pkg}/discounts.py", disc.render(pkg))


def w_tax():
    write("billing/tax.py", tax.render())


def w_pb2():
    write("api/schema_pb2.py", proto.pb2())


def w_proto():
    write("api/schema.proto", proto.proto())


def imports(pkg_list, tests=()):
    paths = []
    for pkg in pkg_list:
        put_filler(f"{pkg}/__init__.py", "")
        paths.append(f"{pkg}/__init__.py")
        for mod in FILLER_PKGS.get(pkg, []):
            put_filler(f"{pkg}/{mod}.py", filler_module(pkg, mod))
            paths.append(f"{pkg}/{mod}.py")
    for t in tests:
        put_filler(f"tests/test_{t}.py", filler_test(t))
        paths.append(f"tests/test_{t}.py")
    return paths


# -- the imports, one package or two per commit (none is a mass commit)
put_filler("README.md", "# Shopwell\n\nThe Shopwell shop backend: orders, subscriptions, billing, the web front end and the API.\n\n"
           "    python3 -m unittest discover -s tests\n")
put_filler("docs/architecture.md", "# Architecture\n\nOne Python process; `web/` renders pages, `api/` serves the app.\n")
put_filler("docs/runbook.md", "# Runbook\n\n- Deploys go out on Tuesdays.\n")
put_filler("pyproject.toml", "[project]\nname = \"shopwell\"\nversion = \"0.1.0\"\nrequires-python = \">=3.10\"\n")
put_filler("Makefile", "test:\n\tpython3 -m unittest discover -s tests\n")
put_filler("scripts/gen_proto.sh", "#!/bin/sh\n# Regenerates api/schema_pb2.py from api/schema.proto.\nprotoc --python_out=. api/schema.proto\n")
imports(["utils", "config"], ["money", "dates", "ids", "retry"])
put_filler("tests/__init__.py", "")
commit(day("2025-11-03", 10), "ana", "Initial import: project skeleton, utils and config")

imports(["orders"], ["cart", "checkout"])
w_pricing()
w_disc("orders")
write("tests/test_pricing.py", "import unittest\n\nfrom orders.pricing import round_money\n\n\n"
      "class TestPricing(unittest.TestCase):\n    def test_round_half_up(self):\n"
      "        self.assertEqual(str(round_money('2.345')), '2.35')\n")
write("tests/test_discounts.py", "import unittest\nfrom decimal import Decimal\n\nfrom orders.discounts import discount_for\n\n\n"
      "class TestDiscounts(unittest.TestCase):\n    def test_welcome(self):\n"
      "        self.assertEqual(discount_for('welcome10', Decimal('50')), Decimal('5.00'))\n")
commit(day("2025-11-03", 15), "ana", "Import the orders package")

imports(["billing"], ["invoices", "refunds", "payments", "currency"])
w_tax()
write("tests/test_tax.py", "import unittest\nfrom decimal import Decimal\n\nfrom billing.tax import tax_for\n\n\n"
      "class TestTax(unittest.TestCase):\n    def test_de_standard(self):\n"
      "        self.assertGreater(tax_for('DE', 'shoes', Decimal('100')), 0)\n")
commit(day("2025-11-04", 11), "dana", "Import the billing package")

imports(["web"])
w_checkout()
for js in ["cart", "account"]:
    put_filler(f"web/static/{js}.js", f"// {js} page.\n'use strict';\n\nfunction init() {{\n  return true;\n}}\n")
put_filler("web/static/styles.css", "body { font-family: system-ui, sans-serif; }\n")
for page in ["base", "checkout", "cart", "account"]:
    put_filler(f"web/templates/{page}.html", f"<!doctype html>\n<title>{page}</title>\n<main>\n</main>\n")
commit(day("2025-11-04", 16), "chen", "Import the web front end")

put_filler("legacy/__init__.py", "")
put_filler("legacy/csv_export.py", filler_module("legacy", "csv_export"))
write("legacy/report_builder.py", report_builder())
commit(day("2025-11-05", 10), "ben", "Import legacy reporting from the old back office")

imports(["subscriptions"], ["renewals", "plans", "proration"])
w_disc("subscriptions")
write("tests/test_subscriptions_discounts.py",
      "import unittest\nfrom decimal import Decimal\n\nfrom subscriptions.discounts import discount_for\n\n\n"
      "class TestSubscriptionDiscounts(unittest.TestCase):\n    def test_welcome(self):\n"
      "        self.assertEqual(discount_for('WELCOME10', Decimal('20')), Decimal('2.00'))\n")
commit(day("2025-11-05", 15), "chen", "Import subscriptions")

imports(["api"], ["handlers", "serializers"])
w_proto()
w_pb2()
commit(day("2025-11-06", 11), "ben", "Import the API layer and its generated protos")

imports(["inventory", "shipping"], ["stock", "reservations", "shipping_rates", "carriers"])
commit(day("2025-11-06", 16), "elif", "Import inventory and shipping")

imports(["customers", "notifications", "catalog", "reports"],
        ["accounts", "loyalty", "email", "search", "products", "daily_report"])
commit(day("2025-11-07", 12), "chen", "Import customers, notifications, catalog and reports")

PLANTED = {"orders/pricing.py", "orders/discounts.py", "subscriptions/discounts.py", "billing/tax.py",
           "web/static/checkout.js", "api/schema_pb2.py", "api/schema.proto", "legacy/report_builder.py",
           "tests/test_pricing.py", "legacy/csv_export.py", "legacy/__init__.py"}
FILLERS = sorted(p for p in filler if p not in PLANTED and not p.endswith("__init__.py")
                 and pathlib.PurePosixPath(p).suffix in (".py", ".js", ".css", ".html", ".md"))
BILLING = [p for p in FILLERS if p.startswith("billing/")]

# -- the events after the imports, executed in date order
events = []   # (when, seq, fn)
seq = [0]


def ev(when, fn):
    seq[0] += 1
    events.append((when, seq[0], fn))


ACTIVE = ["ana", "ben", "chen", "elif"]

# pricing.py: 45 commits, packed toward the end of the year; 32 change apply_promotions,
# 34 also change web/static/checkout.js (the client-side copy of the promotion rules)
P_DATES = spread("2025-11-12", "2026-10-27", 45, power=1.6)
P_DATES[-1] = day("2026-10-27", 17)
promo_idx = set(R.sample(range(45), 32))
promo_idx.add(44)
promo_idx = set(sorted(promo_idx)[-32:]) if len(promo_idx) > 32 else promo_idx
others = [i for i in range(45) if i not in promo_idx]
co_js = set(sorted(promo_idx)[1:]) | set(others[:34 - (len(promo_idx) - 1)])
test_idx = set(R.sample(range(45), 14))
PROMO_SUBJECTS = ["pricing: add {c} promotion", "pricing: {c} applies only above threshold",
                  "pricing: {c} for gold and staff customers", "fix: {c} double-applied on multi-line carts",
                  "pricing: {c} excludes sale items", "pricing: category-specific {c}"]


def pricing_event(i):
    def run():
        who = R.choice(ACTIVE)
        if i in promo_idx:
            if R.random() < 0.7 or len(pricing.rules) < 6:
                depth = 2 + min(4, (len(pricing.rules) + R.randint(0, 4)) // 5)
                pricing.add_rule(depth)
                code = pricing.rules[-1]["code"]
            else:
                pricing.tweak_rule()
                code = R.choice(pricing.rules)["code"]
            msg = R.choice(PROMO_SUBJECTS).format(c=code)
        else:
            fn = pricing.other_change(i)
            msg = {"apply_shipping": "pricing: shipping surcharge for another region",
                   "price_for_tier": "pricing: new customer tier rate",
                   "quote": "pricing: document rounding in quote",
                   "compute_subtotal": "pricing: clarify what the subtotal covers"}[fn]
        w_pricing()
        if i in co_js:
            if i in promo_idx:
                checkout.mirror(pricing)
            else:
                checkout.summary.append(f"  rows.push(['Note {i}', '']);")
            w_checkout()
        if i in test_idx:
            with open(ROOT / "tests/test_pricing.py", "a") as fh:
                fh.write(f"\n    def test_case_{i}(self):\n        self.assertEqual(str(round_money('{i}.005')), '{i}.01')\n")
        commit(P_DATES[i], who, msg)
    return run


for i in range(45):
    ev(P_DATES[i], pricing_event(i))

# checkout.js alone, once
ev(day("2026-02-02"), lambda: (checkout.misc.append("  button.setAttribute('aria-busy', 'true');"), w_checkout(),
                               commit(day("2026-02-02", 11), "chen", "checkout: mark the pay button busy while submitting")))

# the discount twins: 22 commits change both the same way, 2 change each alone
T_DATES = spread("2025-11-17", "2026-10-20", 22)


def twins_event(i):
    def run():
        if i % 3 == 2:
            disc.tweak()
            msg = "discounts: adjust code values in orders and subscriptions"
        else:
            disc.add_rule()
            msg = f"discounts: add {disc.rules[-1][0]} (orders and subscriptions)"
        w_disc("orders")
        w_disc("subscriptions")
        commit(T_DATES[i], R.choice(["ana", "chen", "elif"]), msg)
    return run


for i in range(22):
    ev(T_DATES[i], twins_event(i))


def twin_solo(when, pkg, who, msg, clamp=False, note=None):
    def run():
        if clamp:
            disc.clamp[pkg] = True
        if note:
            disc.notes[pkg].append(note)
        w_disc(pkg)
        commit(when, who, msg)
    ev(when, run)


twin_solo(day("2026-01-21", 14), "orders", "ana", "discounts: comment the blocked-customer rule",
          note="    # blocked customers never get a discount (checked above)")
twin_solo(day("2026-05-12", 10), "orders", "ana", "fix: a fixed-amount code could make an order total negative",
          clamp=True)
twin_solo(day("2026-02-17", 15), "subscriptions", "chen", "subscriptions: note renewal codes apply per period",
          note="    # renewal codes apply to each billing period")
twin_solo(day("2026-08-04", 11), "subscriptions", "elif", "subscriptions: keep discount notes together",
          note="    # see billing/proration.py for mid-period changes")

# billing/tax.py: Dana's file; she leaves in March. Three small touches by others afterwards.
TAX_REGIONS = ["PL", "SE", "DK", "FI", "AT", "BE", "PT", "IE", "CZ", "HU", "RO", "GR"]
TAX_DATES = spread("2025-11-11", "2026-03-16", 12)


def tax_event(i):
    def run():
        tax.add(TAX_REGIONS[i])
        w_tax()
        commit(TAX_DATES[i], "dana", f"tax: add {TAX_REGIONS[i]} rates")
    return run


for i in range(12):
    ev(TAX_DATES[i], tax_event(i))


def tax_touch(when, who, msg, lines):
    def run():
        tax.tail.extend(lines)
        w_tax()
        commit(when, who, msg)
    ev(when, run)


tax_touch(day("2026-04-14", 10), "ben", "tax: typo in error message", ["", "", "# rates reviewed 2026-04"])
tax_touch(day("2026-05-20", 15), "elif", "tax: expose the region list", ["", "", "def regions():", "    return sorted(RATES)"])
tax_touch(day("2026-07-21", 11), "elif", "tax: guard against an empty region", ["", "", "def known(region):",
                                                                                   "    return bool(region) and region in RATES"])

# api/schema_pb2.py: regenerated 55 times; the .proto itself changes in 10 of them
G_DATES = spread("2025-11-10", "2026-10-24", 55)
proto_idx = set(R.sample(range(55), 10))


def pb2_event(i):
    def run():
        paths = []
        if i in proto_idx:
            proto.messages.append(f"Msg{i}")
            w_proto()
            filler_edit("api/handlers.py")
            paths.append("api/handlers.py")
            msg = f"api: add {proto.messages[-1]} message and regenerate"
        else:
            msg = "api: regenerate protos"
        w_pb2()
        flush(paths)
        commit(G_DATES[i], R.choice(["ben", "chen"]), msg)
    return run


for i in range(55):
    ev(G_DATES[i], pb2_event(i))

# everyday work on the rest of the code base
F_DATES = spread("2025-11-10", "2026-10-26", 150)
FILLER_SUBJECTS = ["{m}: small fix", "{m}: tidy up", "{m}: handle empty input", "{m}: add helper",
                   "{m}: cover an edge case", "{m}: rename for clarity", "{m}: follow-up from review"]


def filler_event(i):
    def run():
        who_pool = ACTIVE + (["dana", "dana"] if F_DATES[i] < DANA_LAST else [])
        who = R.choice(who_pool)
        pool = BILLING if who == "dana" and R.random() < 0.7 else FILLERS
        paths = R.sample(pool, min(len(pool), R.choice([1, 1, 2, 2, 3])))
        for p in paths:
            filler_edit(p)
        flush(paths)
        mod = pathlib.PurePosixPath(paths[0]).stem
        commit(F_DATES[i], who, R.choice(FILLER_SUBJECTS).format(m=mod))
    return run


for i in range(150):
    ev(F_DATES[i], filler_event(i))
ev(DANA_LAST, lambda: (filler_edit("billing/refunds.py"), flush(["billing/refunds.py"]),
                       commit(DANA_LAST, "dana", "refunds: last handover notes before I leave")))


# the licence-header sweep: one commit touching every source file (a mass commit)
def sweep():
    state["licensed"] = True
    n = 0
    for p in sorted(filler):
        h = header(p)
        if h and not filler[p].startswith(h):
            filler[p] = h + filler[p]
            write(p, filler[p])
            n += 1
    for p in ["tests/test_pricing.py", "tests/test_discounts.py", "tests/test_tax.py",
              "tests/test_subscriptions_discounts.py"]:
        text = (ROOT / p).read_text()
        write(p, LICENSE_PY + text)
    write("legacy/report_builder.py", LICENSE_PY + report_builder())
    w_pricing(); w_checkout(); w_disc("orders"); w_disc("subscriptions"); w_tax()
    w_proto()
    commit(day("2026-06-09", 9), "elif", "chore: add Apache-2.0 licence headers to every source file")


ev(day("2026-06-09", 9), sweep)


events.sort(key=lambda e: (e[0], e[1]))
for when, _, fn in events:
    fn()
PY
