import express from "express";
import { openDb } from "./db";
import { renderInvoice } from "./render";
import { renderPdf } from "./pdf";

const app = express();
app.use(express.json());
const db = openDb();

// Readiness: migrations have run and the database answers. The k8s probes hit this.
app.get("/healthz", (_req, res) => {
  db.prepare("SELECT 1").get();
  res.json({ ok: true });
});

app.post("/invoices", (req, res) => {
  const { id, customer, lines } = req.body;
  db.prepare("INSERT INTO invoices (id, customer, lines_json) VALUES (?, ?, ?)")
    .run(id, customer, JSON.stringify(lines));
  res.status(201).json({ id });
});

app.get("/invoices/:id", (req, res) => {
  const row = db.prepare("SELECT * FROM invoices WHERE id = ?").get(req.params.id);
  if (!row) return res.sendStatus(404);
  res.type("html").send(renderInvoice(row as any));
});

app.get("/invoices/:id/pdf", async (req, res) => {
  const row = db.prepare("SELECT * FROM invoices WHERE id = ?").get(req.params.id);
  if (!row) return res.sendStatus(404);
  res.type("application/pdf").send(await renderPdf(renderInvoice(row as any)));
});

const port = Number(process.env.PORT ?? 8080);
app.listen(port, () => console.log(`invoicer listening on :${port}`));
