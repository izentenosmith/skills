# Detection Signals — Reproducible Grep/Regex Appendix

> Canonical, copy-pasteable detection commands for every anti-pattern in the rubric, each with its
> **confidence tag** (✅ decidable / ⚠️ proxy / 🔬 needs-data — see
> [`scoring.md`](scoring.md)). Run these from the root of the DDL dumps. They make
> evaluations reproducible and feed the triage signal-scan. A match is a *candidate* finding; ✅
> signals are usually conclusive, ⚠️ require reading the object, 🔬 require a live instance.

All examples assume the working directory is the dump root, one folder per database (`<db>`), and one
file per object type (`tables.sql`, `indexes.sql`, `views.sql`, `procedures.sql`, `triggers.sql`).
Adapt the paths to whatever layout the dumps actually have — a migrations folder works the same way
with `grep -r`.

## Engine notes

The patterns are written for **SQL Server (T-SQL)**, the most common legacy source. On another engine
the *anti-pattern* holds; the *signal* changes:

| Concern | SQL Server signal | Oracle | MySQL / MariaDB | PostgreSQL |
|---|---|---|---|---|
| Multi-row trigger defect | scalar `SELECT @x = … FROM INSERTED/DELETED` | statement-level trigger reading a package variable set by a row trigger | n/a — triggers are always `FOR EACH ROW` (look for per-row cost instead) | statement trigger assuming one row in a transition table |
| RBAR | `CURSOR`, `@@FETCH_STATUS`, `WHILE` | `CURSOR … LOOP`, `FOR r IN (SELECT …) LOOP` | `DECLARE … CURSOR`, `LOOP`/`WHILE` | `FOR r IN SELECT … LOOP` |
| Dynamic SQL | `EXEC(@sql)` | `EXECUTE IMMEDIATE` with concatenation | `PREPARE` from `CONCAT` | `EXECUTE` with `||` instead of `format()`/`USING` |
| Cross-database reference | `DB..table`, `DB.dbo.obj` | `@dblink` | `otherdb.table` | `dblink`/foreign tables |
| Identity | `IDENTITY` | `SEQUENCE` / `GENERATED … AS IDENTITY` | `AUTO_INCREMENT` | `serial` / `GENERATED … AS IDENTITY` |
| Untrusted constraint | `WITH NOCHECK` | `NOVALIDATE` / `DISABLE` | FKs on MyISAM (not enforced) | `NOT VALID` / `NOT ENFORCED` |
| Deprecated LOB | `text`, `ntext`, `image` | `LONG`, `LONG RAW` | — | — |

> ⚠️ **These are triage starting points, not a validated linter.** Single-line `grep` cannot fully
> parse SQL: rules phrased as "a `CREATE TABLE` block with no `PRIMARY KEY`", cross-file comparisons
> (FK-vs-index, heap detection), and the cross-DB three-part-name patterns need block-aware parsing
> or a two-pass script — the commands below *locate candidates*, after which a human (or a real
> parser) confirms. Treat a match as "look here", not "defect proven", except for the ✅ signals whose
> pattern is unambiguous on its own.

## Tables (`tables.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| Missing primary key | ✅ | per `CREATE TABLE` block: no `PRIMARY KEY` → `grep -i "CREATE TABLE" <db>/tables.sql` then check each block lacks `PRIMARY KEY` |
| `char(n)` for variable text | ✅ | `grep -nioE "char\([0-9]+\)" <db>/tables.sql` |
| `float`/`numeric(n,0)` as ID/code | ⚠️ | `grep -niE "(id_|cod_)[a-z_]* +(float|numeric\([0-9]+,0\))" <db>/tables.sql` |
| Uniform `varchar(255)` | ⚠️ | `grep -nioc "varchar(255)" <db>/tables.sql` |
| Deprecated LOB types | ✅ | `grep -niwE "(text|ntext|image)" <db>/tables.sql` |
| Magic-value sentinel default | ⚠️ | `grep -niE "DEFAULT *'(9999|0000|)" <db>/tables.sql` |
| Polymorphic/generic column | ⚠️ | `grep -niE "(payload|misc_data|config_blob|extra_info|value) +(varchar|text|image|varbinary)" <db>/tables.sql` |
| Shadow/backup/versioned table | ✅ | `grep -niE "CREATE TABLE.*(_COPIA|_BAK|_OLD|_TMP|[0-9]{6,8})" <db>/tables.sql` |
| Tooling junk table | ✅ | `grep -ni "dtproperties" <db>/tables.sql` |
| Repeating-group column family | ⚠️ | `grep -noiE "^\s*\[?[a-z_]+_?[0-9]\]? " <db>/tables.sql` then group by table and stem — ≥ 2 columns sharing a stem with different trailing digits |
| Generic arc (type + id, no FK) | ⚠️ | `grep -niE "\[?(tipo|type|origen)_?[a-z_]*\]? " <db>/tables.sql` → for each table, an `id_*` sibling not listed in any `FOREIGN KEY` |
| Mandatory recursive FK | ✅ | `FOREIGN KEY (col) REFERENCES <same table>` where `col` is declared `NOT NULL` — block-aware check |
| Intersection table without pair uniqueness | ✅ | tables whose only FKs are two parents, with no `PRIMARY KEY`/`UNIQUE` covering both FK columns |
| Stored derived attribute | ⚠️ | `grep -niE "\[?(total|cant_total|promedio|saldo|suma)[a-z_]*\]? " <db>/tables.sql`, then confirm a proc/trigger recomputes it |
| Collation drift (estate) | ✅ | `grep -rhoiE "COLLATE [A-Za-z0-9_]+" */tables.sql \| sort \| uniq -c` |
| INT key near ceiling | 🔬 | structural flag only — needs row counts |

## Indexes (`indexes.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| Nonclustered index duplicating clustered key | ⚠️ | compare `CREATE UNIQUE CLUSTERED INDEX … (cols)` vs `CREATE NONCLUSTERED INDEX … (same cols)` per table in `<db>/indexes.sql` |
| Leftmost-prefix redundancy | ⚠️ | list index key lists per table; flag single-col index that prefixes a composite |
| Heap (no clustered index) | ✅ | tables in `tables.sql` with no `CLUSTERED` index/PK in `indexes.sql` → `grep -i "CLUSTERED" <db>/indexes.sql` and diff against table list |
| Missing FK index (cross-file) | ✅ | FK cols in `tables.sql` (`FOREIGN KEY`) absent from any index key in `indexes.sql` |
| Blanket fill factor | ⚠️ | `grep -nioc "FILLFACTOR = 100" <db>/indexes.sql` |
| Low cardinality | 🔬 | flag indexes keyed on `flag_*`/`char(1)`; confirm with `COUNT(DISTINCT)` on a live instance |
| Function-based suppression | ⚠️ | `grep -niE "WHERE.*(YEAR|MONTH|UPPER|LOWER|CONVERT|CAST) *\(" <db>/{views,procedures}.sql` |

## Procedures & functions (`procedures.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| RBAR (cursors / loops) | ✅ | `grep -niwc "cursor" <db>/procedures.sql` ; `grep -niw "@@FETCH_STATUS" <db>/procedures.sql` |
| No error handling | ✅ | files with `BEGIN TRAN` but no `BEGIN TRY`: `grep -Li "begin try" <db>/procedures.sql` vs `grep -li "begin tran" <db>/procedures.sql` |
| Dynamic SQL | ✅ | `grep -nioE "exec(ute)? *\(" <db>/procedures.sql` |
| Unlength cast | ✅ | `grep -nioE "cast\([^)]* as +varchar\)" <db>/procedures.sql` (no length) |
| Comma joins | ⚠️ | `grep -niE "FROM +[a-z_]+ *, *[a-z_]+" <db>/procedures.sql` |
| `SELECT *` | ✅ | `grep -nioc "select \*" <db>/procedures.sql` |
| Missing `SET NOCOUNT` | ✅ | `grep -Li "set nocount" <db>/procedures.sql` |
| Hardcoded cross-DB call | ✅ | `grep -niE "[A-Z_]+\.dbo\.\|[A-Z_]+\.\." <db>/procedures.sql` |
| No sniffing mitigation (estate-level) | 🔬 | `grep -ric "option *( *recompile\|optimize for" */procedures.sql` — absence is an estate observation, **not** a per-proc defect |

## Views (`views.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| `TOP 100 PERCENT … ORDER BY` hack | ✅ | `grep -niB2 "ORDER BY" <db>/views.sql \| grep -i "TOP 100 PERCENT"` |
| Nested view pyramid | ✅ | cross-reference: a view whose `FROM`/`JOIN` names another `CREATE VIEW` in the dumps |
| `UNION` vs `UNION ALL` | ✅ | `grep -niwE "union" <db>/views.sql \| grep -viw "union all"` |
| `SELECT *` in view | ✅ | `grep -nioc "select \*" <db>/views.sql` |
| Missing `SCHEMABINDING` | ✅ | `grep -Li "schemabinding" <db>/views.sql` |
| `CREATE OR ALTER` era-mismatch | ✅ | `grep -ni "CREATE OR ALTER" <db>/views.sql` |
| Catch-all (many joins) | ⚠️ | count `JOIN`/`,` sources per view; flag outliers |

## Triggers (`triggers.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| Multi-row scalar-from-pseudo-table (CRITICAL) | ✅ | `grep -niE "SELECT +@[A-Za-z0-9_]+ *=.*FROM +(DELETED|INSERTED)" <db>/triggers.sql` |
| Hidden side-effect (writes other tables) | ⚠️ | `grep -niE "(UPDATE\|INSERT\|DELETE)" <db>/triggers.sql` targeting a table ≠ trigger's own |
| Transaction-scope inflation | ✅ | `grep -niwE "cursor\|while" <db>/triggers.sql` |
| Hardcoded cross-DB write | ✅ | `grep -niE "[A-Z_]+\.\." <db>/triggers.sql` |
| Cascading/recursive | ⚠️ | build a trigger→table→trigger graph; flag cycles |

## Security & data sensitivity (`audit-lenses.md` §6)

| Anti-pattern | Conf. | Command |
|---|---|---|
| Untrusted/disabled constraint | ✅ | `grep -niE "WITH +NOCHECK\|NOCHECK +CONSTRAINT" <db>/*.sql` |
| Elevated execution context | ✅ | `grep -ni "EXECUTE AS" <db>/procedures.sql` |
| Plaintext secret in body | ⚠️ | `grep -niE "(password\|pwd\|secret\|connectionstring) *=" <db>/*.sql` |
| PII/sensitive column | 🔬 | identify by name (`rut`, `ap_paterno`, `sueldo`, `pago`, `nombre`); sensitivity is contextual |

> Note: GRANTs, role memberships, logins, and Always Encrypted metadata are typically **not** present
> in these DDL dumps — those security aspects are out of static scope and must be checked on the
> server.
