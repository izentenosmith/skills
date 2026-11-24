import { test } from "node:test";
import assert from "node:assert";
import { readFile } from "node:fs/promises";
import { build } from "../scripts/build.mjs";

test("every page builds and every internal link resolves", async () => {
  const pages = await build();
  assert.ok(pages.length > 0);
  for (const page of pages) {
    const html = await readFile(page, "utf8");
    for (const [, href] of html.matchAll(/href="(\.{0,2}\/?[^"#:]+\.html)"/g)) {
      const target = new URL(href, `file://${process.cwd()}/${page}`).pathname;
      await assert.doesNotReject(readFile(target), `${page} links to missing ${href}`);
    }
  }
});
