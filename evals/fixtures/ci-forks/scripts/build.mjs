// Render docs/**/*.md to dist/**/*.html.
import { readdir, readFile, mkdir, writeFile } from "node:fs/promises";
import { join, relative, dirname } from "node:path";
import { marked } from "marked";

const SRC = "docs";
const OUT = "dist";

async function* walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (entry.name.endsWith(".md")) yield path;
  }
}

export async function build() {
  const pages = [];
  for await (const file of walk(SRC)) {
    const html = marked.parse(await readFile(file, "utf8"));
    const target = join(OUT, relative(SRC, file)).replace(/\.md$/, ".html");
    await mkdir(dirname(target), { recursive: true });
    await writeFile(target, `<!doctype html><meta charset="utf-8"><main>${html}</main>\n`);
    pages.push(target);
  }
  return pages;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const pages = await build();
  console.log(`built ${pages.length} pages into ${OUT}/`);
}
