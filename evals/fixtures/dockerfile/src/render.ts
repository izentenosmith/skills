import fs from "node:fs";
import path from "node:path";
import { createHmac } from "node:crypto";
import Handlebars from "handlebars";

const TEMPLATES = path.join(__dirname, "..", "templates");
const invoice = Handlebars.compile(fs.readFileSync(path.join(TEMPLATES, "invoice.hbs"), "utf8"));

type Row = { id: string; customer: string; lines_json: string; due_date?: string };

export function renderInvoice(row: Row): string {
  const lines = JSON.parse(row.lines_json) as { label: string; cents: number }[];
  const total = lines.reduce((s, l) => s + l.cents, 0);
  const sig = createHmac("sha256", process.env.INVOICE_SIGNING_SECRET ?? "")
    .update(row.id).digest("hex").slice(0, 16);
  return invoice({ ...row, lines, total: (total / 100).toFixed(2), sig });
}
