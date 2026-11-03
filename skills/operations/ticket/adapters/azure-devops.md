# Adapter — Azure DevOps (Boards)

**Prefer `az boards`** (the `azure-devops` extension of the Azure CLI): it keeps the personal access token out of every file and carries organization and project defaults. Use `az rest` for the few operations the CLI can't do, and raw REST with a token from an environment variable only when `az` isn't available.

Placeholders below: `<org>`, `<project>`, `<team>`, `<id>`. Set defaults once with `az devops configure --defaults organization=https://dev.azure.com/<org> project=<project>`.

## Canonical → Azure DevOps

| Canonical | Azure DevOps |
|---|---|
| kind | Work item type — depends on the process: Agile (User Story, Bug, Task, Feature, Epic, Issue), Scrum (Product Backlog Item, Bug, Task, Impediment), Basic (Issue, Task, Epic), or a custom inherited process with its own types |
| state category | Each type's states belong to categories: Proposed, In Progress, Resolved, Completed, Removed |
| container | `System.IterationPath` |
| area | `System.AreaPath` |
| label | `System.Tags` (semicolon-separated) |
| description format | HTML in `System.Description`; bugs in some processes use `Microsoft.VSTS.TCM.ReproSteps` instead |
| hours | Agile/CMMI: `Microsoft.VSTS.Scheduling.CompletedWork` / `RemainingWork` / `OriginalEstimate` on tasks; Scrum: `Effort`; custom processes often add their own decimal field |
| comment | `--discussion` on update (`System.History`) |

## Preflight

```bash
az boards query --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project" -o tsv | head -3
```

`Access Denied: The Personal Access Token used has expired` → stop; the user runs `az devops login --organization https://dev.azure.com/<org>` themselves, with a token scoped to **Work Items: Read, write & manage**.

## Discovering the schema

```bash
# Types, then the states and fields (with allowed values and required flags) of one type
az rest --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --url "https://dev.azure.com/<org>/<project>/_apis/wit/workitemtypes?api-version=7.1" --query "value[].name"
az rest --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --url "https://dev.azure.com/<org>/<project>/_apis/wit/workitemtypes/<Type>/states?api-version=7.1"
az rest --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --url "https://dev.azure.com/<org>/<project>/_apis/wit/workitemtypes/<Type>/fields?\$expand=allowedValues&api-version=7.1" \
  --query "value[].{field:referenceName, required:alwaysRequired, values:allowedValues}"
```

`az rest` needs an Azure AD session (`az login`); the PAT from `az devops login` does **not** work for it. The `--resource` GUID is the fixed application id of Azure DevOps.

Required fields can also come from **process rules** that the field metadata doesn't show. A create that fails with `TF401320: Rule Error for field <X>` names a field the profile must add.

**The current sprint:**

```bash
az boards iteration team list --team "<team>" --timeframe current --query "[].path" -o tsv
```

**All sprints**, when the user names one:

```bash
az boards iteration project list --depth 4 -o json
```

Two traps in that output:

- Iterations are nested under `children`; a JMESPath filter at the root returns nothing, without an error.
- A node's `path` includes an `\Iteration\` segment (`\<project>\Iteration\Sprint 22`) that `System.IterationPath` rejects. The value to write is `<project>\Sprint 22` — derive it from the node's `name` and its parents, not from `path`.

Naming conventions drift over a project's life (`Sprint - 15` then `Sprint 16`). Never interpolate a sprint name from a pattern; look it up.

## Searching (reconcile)

WIQL selects custom fields directly — far faster than one `work-item show` per id:

```bash
az boards query --wiql "SELECT [System.Id],[System.WorkItemType],[System.Title],[System.State],[System.Tags] \
FROM WorkItems WHERE [System.TeamProject] = @project \
AND [System.IterationPath] = '<project>\Sprint 22' \
AND [System.AssignedTo] = '<assignee>'" -o json
```

- `[System.Tags]` and other long-text fields accept only `CONTAINS` (and `NOT CONTAINS`), never `=` or `<>` — `The specified operator cannot be used with long-text fields`.
- `[System.Title] CONTAINS 'word'` for keyword search; `[System.ChangedDate] < @today - 30` for stale items.
- The assignee is the identity's sign-in name, which isn't always the email domain the user writes with. Take it from the user's own recent items.

## Create

```bash
az boards work-item create --type "<Type>" --title "<title>" \
  --description "<p><strong>Context:</strong> …</p>" \
  --assigned-to "<assignee>" --area "<area path>" --iteration "<iteration path>" \
  --fields "System.State=<initial state>" "<Custom.RequiredField>=<value>" \
  -o json
```

The create accepts only the type's initial state (or a few early ones). To document finished work, create in the initial state and then update to the done state.

## Update, transition, close

```bash
az boards work-item update --id <id> --state "<done state>" \
  --discussion "Implemented in <shas>; verified in <environment>." \
  --fields "<hours field>=<n>" -o json
```

For batches, loop these from a script and report OK/FAIL per item without aborting.

## Tags — they append

`--fields "System.Tags=<tag>"` **adds** to the existing set; it doesn't replace it. Several at once: `"System.Tags=prod-incident; caused-by-2210"`. Writing an empty value is ignored — it removes nothing.

So a misspelled tag can't be fixed by writing the field again. **To remove a tag**, replace the whole set with a JSON Patch — the only operation that can shrink it:

```bash
printf '[{"op":"replace","path":"/fields/System.Tags","value":"prod-incident"}]' > "$TMPDIR/tags.json"
az rest --method PATCH --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --url "https://dev.azure.com/<org>/<project>/_apis/wit/workitems/<id>?api-version=7.1" \
  --headers "Content-Type=application/json-patch+json" --body @"$TMPDIR/tags.json" -o none
```

An empty `value` removes every tag.

## Linking commits

**The mention convention:** `AB#<id>` in a commit message or PR description, with the Boards ↔ GitHub connection active, links the item on push. For Azure Repos, the work item is linked from the PR or with `#<id>` in the commit message.

**Through the API**, for commits already pushed — an `ArtifactLink` in the item's *Development* section (not *Deployment*, which only pipelines populate):

| Code host | Link URL |
|---|---|
| GitHub | `vstfs:///GitHub/Commit/<repo-guid>%2F<sha>` — **two** segments; the repo GUID is Azure's internal id for the connected repository |
| Azure Repos | `vstfs:///Git/Commit/<project-id>%2F<repo-id>%2F<sha>` |

The GitHub repo GUID is **not** the Boards connection id and **not** the pipelines service-endpoint id; using either gives "GitHub Commit link could not be read". It isn't returned by the connections API either: add the first link by hand in the item's UI and copy the GUID from the item's `relations`. Record it in the profile.

```bash
cat > "$TMPDIR/link.json" <<'JSON'
[{"op":"add","path":"/relations/-","value":{
  "rel":"ArtifactLink",
  "url":"vstfs:///GitHub/Commit/<repo-guid>%2F<sha>",
  "attributes":{"name":"GitHub Commit"}}}]
JSON
az rest --method PATCH --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --url "https://dev.azure.com/<org>/<project>/_apis/wit/workitems/<id>?api-version=7.1" \
  --headers "Content-Type=application/json-patch+json" --body @"$TMPDIR/link.json" -o none
```

To remove a malformed link, read `az boards work-item show --id <id> --expand relations`, find its index, and patch `{"op":"remove","path":"/relations/<index>"}`. `az boards work-item relation remove` only handles links between work items.

Tools that **don't** work for artifact links: `az boards work-item relation add --relation-type ArtifactLink` (it can't set `attributes.name`) and `az devops invoke --in-file` with a JSON Patch body (fails on some CLI versions).

## Read back

```bash
az boards query --wiql "SELECT [System.Id],[System.State],[System.Tags],[System.IterationPath],[System.AreaPath],[System.Title] \
FROM WorkItems WHERE [System.TeamProject] = @project AND [System.Id] IN (<id>, <id>)" -o json
```

Add the profile's required and always-filled custom fields to the `SELECT`.

## Dates for metrics

`System.CreatedDate` and `Microsoft.VSTS.Common.ClosedDate` are always populated. `Microsoft.VSTS.Common.ResolvedDate` is only set when the type's workflow passes through a Resolved-category state — many processes never do. Check how many closed items have it before using it for anything.

## Fallback — REST without `az`

Only when the CLI isn't available. The token comes from an environment variable, never a literal in the script (scripts end up in repos):

```python
import base64, json, os, urllib.parse, urllib.request

ORG, PROJECT = os.environ["ADO_ORG"], os.environ["ADO_PROJECT"]
auth = base64.b64encode(f":{os.environ['AZURE_DEVOPS_EXT_PAT']}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json-patch+json"}

def create(item_type, fields):
    url = (f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/wit/workitems/"
           f"${urllib.parse.quote(item_type)}?api-version=7.1")
    body = json.dumps([{"op": "add", "path": f"/fields/{k}", "value": v} for k, v in fields.items()])
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())["id"]
```

A browser-side widget can't call the API — CORS blocks it. Always run locally.

## Errors and their causes

| Error | Cause | Fix |
|---|---|---|
| `TF401320: Rule Error for field <X> … Required` | A process rule requires `<X>` | Add it to the profile's required fields |
| `TF401347` / `Invalid tree name` | Iteration or area path in the wrong format | Re-resolve from the node names |
| `Access Denied: The Personal Access Token used has expired` | PAT expired | The user runs `az devops login` |
| `az rest` asks for credentials / `AADSTS700082` | The Azure AD refresh token expired | The user runs `az login` |
| `The specified operator cannot be used with long-text fields` | `=` or `<>` on tags | Use `CONTAINS` |
| `GitHub Commit link could not be read` | Wrong GUID or a third segment | Use the repo GUID and two segments |
| Link created but commit doesn't show | Commit not pushed yet | Push, then link |
| `Artifact links must have a valid name specified` | `relation add` can't set the name | Use `az rest` |
| Item created without an area or module | No rule requires it | Read back every time |
