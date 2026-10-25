// The PDF render service is external; its key comes from the environment at run time.
export async function renderPdf(html: string): Promise<Buffer> {
  const r = await fetch(process.env.PDF_RENDER_URL ?? "https://pdf.internal.example.com/render", {
    method: "POST",
    headers: {
      authorization: `Bearer ${process.env.PDF_RENDER_API_KEY}`,
      "content-type": "text/html",
    },
    body: html,
  });
  if (!r.ok) throw new Error(`pdf render failed: ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}
