import { describe, it, expect } from "vitest";
import { renderInvoice } from "../src/render";

describe("renderInvoice", () => {
  it("totals the lines", () => {
    const html = renderInvoice({
      id: "INV-1", customer: "Acme",
      lines_json: JSON.stringify([{ label: "a", cents: 1050 }, { label: "b", cents: 250 }]),
    });
    expect(html).toContain("Total 13.00");
  });
});
