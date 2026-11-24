// Post (or update) the preview link on the pull request.
// Env: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER.
const { GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER } = process.env;
const api = `https://api.github.com/repos/${GITHUB_REPOSITORY}/issues/${PR_NUMBER}/comments`;
const headers = {
  authorization: `Bearer ${GITHUB_TOKEN}`,
  accept: "application/vnd.github+json",
};
const marker = "<!-- tidepool-preview -->";
const url = `https://pr-${PR_NUMBER}.tidepool-docs.pages.dev`;
const body = `${marker}\nPreview: ${url}`;

const existing = (await (await fetch(api, { headers })).json()).find((c) => c.body?.startsWith(marker));
const res = existing
  ? await fetch(`https://api.github.com/repos/${GITHUB_REPOSITORY}/issues/comments/${existing.id}`,
      { method: "PATCH", headers, body: JSON.stringify({ body }) })
  : await fetch(api, { method: "POST", headers, body: JSON.stringify({ body }) });
if (!res.ok) throw new Error(`comment failed: ${res.status}`);
console.log(`commented ${url}`);
