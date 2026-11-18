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

**PostgreSQL dumps.** `pg_dump --schema-only` writes one file; each object is preceded by a header
`-- Name: <obj>; Type: <TABLE|INDEX|FK CONSTRAINT|TRIGGER|FUNCTION|ACL|POLICY>; Schema: <s>; Owner: <o>`.
Split on that header to get the per-type layout above. FKs appear as `ALTER TABLE ONLY … ADD CONSTRAINT
… FOREIGN KEY`, separate from `CREATE TABLE`, so the FK-index cross-check reads both; PK/`UNIQUE`-backed
indexes have no `CREATE INDEX` line.

## Engine notes

The patterns are written for **SQL Server (T-SQL)**, the most common legacy source. On another engine
the *anti-pattern* holds; the *signal* changes — and some criteria don't exist at all (**n/a**: leave
them out of that file's base, scoring.md):

| Concern | SQL Server signal | Oracle | MySQL / MariaDB | PostgreSQL |
|---|---|---|---|---|
| Multi-row trigger defect | scalar `SELECT @x = … FROM INSERTED/DELETED` | statement-level trigger reading a package variable set by a row trigger | n/a — triggers are always `FOR EACH ROW` (look for per-row cost instead) | statement trigger assuming one row in a transition table |
| RBAR | `CURSOR`, `@@FETCH_STATUS`, `WHILE` | `CURSOR … LOOP`, `FOR r IN (SELECT …) LOOP` | `DECLARE … CURSOR`, `LOOP`/`WHILE` | `FOR r IN SELECT … LOOP` |
| Dynamic SQL | `EXEC(@sql)` with `+ @` | `EXECUTE IMMEDIATE` with concatenation | `PREPARE` from `CONCAT` | `EXECUTE` with `\|\|` instead of `format()`/`USING` |
| Cross-database reference | `DB..table`, `DB.dbo.obj` | `@dblink` | `otherdb.table` | `dblink`/foreign tables |
| Identity | `IDENTITY` | `SEQUENCE` / `GENERATED … AS IDENTITY` | `AUTO_INCREMENT` | `GENERATED ALWAYS AS IDENTITY` (good); `serial` (legacy, Low) |
| Untrusted constraint | `WITH NOCHECK` | `NOVALIDATE` / `DISABLE` | FKs on MyISAM (not enforced) | `NOT VALID` (legacy rows unchecked, ⚠️ Medium); `NOT ENFORCED` (no rows checked, ✅ High unless documented); `DISABLE TRIGGER ALL` |
| Deprecated LOB | `text`, `ntext`, `image` | `LONG`, `LONG RAW` | — | n/a (`text` is recommended) |
| Heap / clustered | no `CLUSTERED` index/PK = heap | heap by default; IOT = `ORGANIZATION INDEX` | InnoDB always clustered on PK | n/a — every table is a heap; `CLUSTER` is one-off |
| Schemabinding | missing `WITH SCHEMABINDING` | — | — | n/a for views (dependencies always tracked); functions: prefer `BEGIN ATOMIC` SQL bodies |
| Error handling | `BEGIN TRAN` without `BEGIN TRY` | `EXCEPTION WHEN OTHERS THEN NULL` | `DECLARE CONTINUE HANDLER` swallowing errors | n/a (atomic); flag `EXCEPTION WHEN OTHERS THEN NULL` |
| `SET NOCOUNT` | missing | — | — | n/a |
| Blanket fill factor | uniform `FILLFACTOR = 100` | `PCTFREE` | — | n/a (heap 100 is right for insert-mostly) |
| FK auto-indexed | no | no | **yes** (InnoDB) — skip the missing-FK-index check | no |
| Inexact numeric | `float`, `real` | `BINARY_FLOAT`, `BINARY_DOUBLE` (`FLOAT` is exact) | `FLOAT`, `DOUBLE`, `REAL` | `real`, `double precision` |
| NULL quirks | `UNIQUE` admits **one** NULL; `SET ANSI_NULLS OFF` | `''` **is** NULL; all-NULL keys not indexed (`col IS NULL` can't use a one-column index) | `<=>` null-safe equality; `ONLY_FULL_GROUP_BY` off = arbitrary values for non-grouped columns | `UNIQUE` admits many NULLs unless `NULLS NOT DISTINCT` |
| Dirty-read hint | `WITH (NOLOCK)`, `READ UNCOMMITTED` | n/a (no dirty reads) | `READ UNCOMMITTED` | n/a (`READ UNCOMMITTED` behaves as read committed) |
| Catch-all predicate | `(@p IS NULL OR col = @p)`, `ISNULL(@p, col)` | `(:p IS NULL OR …)`, `NVL(:p, col)` | `(? IS NULL OR …)`, `IFNULL` | `($1 IS NULL OR …)`, `coalesce($1, col)` |
| Offset paging | `OFFSET … FETCH`, `ROW_NUMBER() … BETWEEN` | `ROWNUM` wrapping, `OFFSET … FETCH` | `LIMIT n, m`, `LIMIT … OFFSET` | `LIMIT … OFFSET`, `OFFSET … FETCH` |
| Optimizer directive | `WITH (INDEX())`, `OPTION (… JOIN / FORCE ORDER)` | `/*+ INDEX(…) */` | `FORCE/USE INDEX`, `STRAIGHT_JOIN` | `pg_hint_plan` comments; `SET enable_* = off` |
| Security objects in the dump | usually absent | usually absent | usually absent | present by default (owners, grants, policies) |

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
| Reducible key | ✅ | block-aware: per table, compare `PRIMARY KEY (…)` / `UNIQUE (…)` column sets; flag a strict superset of another that is not the target of any `REFERENCES t (…)` |
| Surrogate key with no alternate key | ✅/⚠️ | tables whose PK is an `IDENTITY`/`serial`/`uuid` column and that have no `UNIQUE` constraint or unique index; then judge whether a natural identifier exists |
| `char(n)` for variable text | ⚠️ | `grep -niE "(^\|[^a-z])(n?char\|character)\s*\([0-9]+\)" <db>/tables.sql` (doesn't match `varchar`); read whether the column is a truly fixed-length code |
| `float`/`numeric(n,0)` as ID/code | ⚠️ | `grep -niE "(id_\|cod_)[a-z_]* +(float\|numeric\([0-9]+,0\))" <db>/tables.sql` |
| Inexact type on money/quantity | ⚠️ | `grep -niE "\[?[a-z_]*(price\|precio\|amount\|monto\|cost\|costo\|valor\|importe\|saldo\|balance\|sueldo\|salary\|rate\|tarifa\|qty\|cantidad\|quantity\|hours\|horas)[a-z_]*\]? +(float\|real\|double)" <db>/tables.sql` (Oracle: `BINARY_FLOAT`/`BINARY_DOUBLE`) |
| Representation-typed date/time | ⚠️ | `grep -niE "\[?(fec\|fecha\|date\|dt\|hora)[a-z_]*\]? +(n?char\|n?varchar\|int\|numeric)" <db>/tables.sql` |
| Type drift / FK type ≠ key type | ✅/⚠️ | extract `(column, type)` pairs from every `CREATE TABLE`; group by name or synonym (`zip\|postal\|cp\|codigo_postal`) and list names with > 1 type or length (⚠️); compare each FK column's type to the referenced column (✅) |
| Uniform `varchar(255)` | ⚠️ | `grep -nioc "varchar(255)" <db>/tables.sql` |
| Deprecated LOB types | ✅ | SQL Server dumps only: `grep -niwE "(text\|ntext\|image)" <db>/tables.sql` |
| Magic-value sentinel default | ⚠️ | `grep -niE "DEFAULT *\(?('(9999\|0000)[^']*'\|''\|-1\b)" <db>/tables.sql`; block-aware: `*_id … NOT NULL DEFAULT (0\|-1)` (placeholder parent) |
| Overloaded NULL | ⚠️ | nullable columns on a table with a `tipo_*`/`*_type` column and no `CHECK` naming it; nullable `fecha_fin`/`hasta`/`valid_to` beside a start date |
| Partial-NULL composite FK | ✅ | block-aware: a multi-column `FOREIGN KEY` whose columns are not all `NOT NULL`, with no `MATCH FULL` and no `num_nulls` `CHECK` |
| `CHECK` on a nullable column | ⚠️ | a `CHECK` naming a column declared without `NOT NULL` and without `IS NOT NULL` in the predicate |
| `CHECK` calling a cross-table function | ⚠️ | `grep -niE "CHECK *\(.*\b[A-Za-z_]+\.[A-Za-z_]+ *\(" <db>/tables.sql`, then read the function body for `FROM` (n/a on Oracle and MySQL 8, which forbid it) |
| Time-relative `CHECK` | ✅ | `grep -niE "CHECK *\(.*(getdate\|sysdatetime\|getutcdate\|current_timestamp\|current_date\|now *\()" <db>/tables.sql` (n/a on Oracle and MySQL 8) |
| Polymorphic/generic column | ⚠️ | `grep -niE "(payload\|misc_data\|config_blob\|extra_info\|value) +(varchar\|text\|image\|varbinary)" <db>/tables.sql` |
| CSV id list | ⚠️ | `grep -niE "\[?[a-z_]*(_ids\|_list\|lista_[a-z_]*)\]? +n?(var)?char\|\[?(id\|cod)_[a-z_]+\]? +n?varchar\((max\|[5-9][0-9]\|[1-9][0-9]{2,})\)" <db>/tables.sql` ; code: `grep -niE "CHARINDEX *\( *','\|STRING_SPLIT\|FIND_IN_SET\|LIKE +'%,' *\+\|string_to_array" <db>/{procedures,views}.sql` |
| EAV table | ⚠️ | block-aware: a column matching `(attr(ibute)?_?(name\|key)\|prop(erty)?(_?name)?\|field_?name\|param(eter)?_?name\|nombre_atributo\|atributo)` and one matching `(attr_?)?(value\|valor\|val)(_[a-z]+)?` and little else; code: `grep -nicE "(attr_name\|attribute_name\|atributo) *= *N?'" <db>/{procedures,views}.sql` |
| Shadow/backup/versioned table | ✅ | `grep -niE "CREATE TABLE.*(_COPIA\|_BAK\|_OLD\|_TMP\|[0-9]{6,8})" <db>/tables.sql` |
| Per-value clone table | ⚠️ | `grep -noiE "CREATE TABLE +[^ (]*_?(19\|20)[0-9]{2}(_?(0[1-9]\|1[0-2]\|q[1-4]))?\]?[ (]" <db>/tables.sql`, then group by stem and diff column lists; exclude `PARTITION OF` |
| Per-value clone column | ⚠️ | `grep -noiE "^\s*\[?[a-z_]+_?(19\|20)[0-9]{2}\]? " <db>/tables.sql` — ≥ 2 columns sharing a stem |
| Table name built at run time | ✅ | `grep -niE "(FROM\|INTO\|UPDATE\|JOIN) +\[?[A-Za-z_]+_?' *\+ *@" <db>/procedures.sql` |
| Value list in column definition | ⚠️ | `grep -niE "CHECK *\( *\[?[a-z_]+\]? +IN *\(\|\bENUM *\(\|AS +ENUM" <db>/tables.sql` on status/type/category columns |
| Tooling junk table | ✅ | `grep -ni "dtproperties" <db>/tables.sql` |
| Repeating-group column family | ⚠️ | `grep -noiE "^\s*\[?[a-z_]+_?[0-9]\]? " <db>/tables.sql` then group by table and stem — ≥ 2 columns sharing a stem with different trailing digits; drop distinct roles (`reported_by`/`assigned_to`) |
| Relationship without FK | ⚠️ | two-pass: PK column names from `tables.sql` vs columns of the same name (or `<tbl>_id` / `id_<tbl>` / `cod_<tbl>`) absent from every `FOREIGN KEY`; corroborate: `grep -niE "LEFT +(OUTER +)?JOIN .* IS NULL" <db>/procedures.sql` near a `DELETE` |
| Generic arc (type + id, no FK) | ⚠️ | `grep -niE "\[?(tipo\|type\|origen)_?[a-z_]*\]? \|\[?[a-z_]*(able_type\|entity_type\|object_type\|owner_type\|parent_type\|target_type\|ref_table\|table_name\|nombre_tabla)\]? " <db>/tables.sql` → an `id_*` sibling not listed in any `FOREIGN KEY`; a `CHECK` listing table names |
| Mandatory recursive FK | ✅ | `FOREIGN KEY (col) REFERENCES <same table>` where `col` is declared `NOT NULL` — block-aware check |
| Intersection table without pair uniqueness | ✅ | tables whose only FKs are two parents, with no `PRIMARY KEY`/`UNIQUE` covering both FK columns |
| All-key multi-parent table | ⚠️ | per `CREATE TABLE`, the PK column list equals the column list and has ≥ 3 entries with ≥ 2 FKs |
| RI-less tree encoding | ⚠️ | `grep -niE "\[?(lft\|rgt\|nsleft\|nsright\|path\|lineage\|ruta)\]? \|\bhierarchyid\b" <db>/tables.sql` with no parent FK |
| Stored derived attribute | ⚠️ | `grep -niE "\[?(total\|cant_total\|promedio\|saldo\|suma\|edad\|age\|antiguedad)[a-z_]*\]? " <db>/tables.sql`, then confirm a proc/trigger recomputes it |
| History without non-overlap | ⚠️ | PK/`UNIQUE` containing `*_from`/`*_to`/`desde`/`hasta`/`inicio`/`fin`/`valid*`/`effective*` and no `EXCLUDE`/`WITHOUT OVERLAPS` on the table |
| External file by path | ⚠️ | `grep -niE "\[?[a-z_]*(_path\|_file\|ruta\|archivo\|_url)\]? +n?varchar" <db>/tables.sql` |
| Collation drift (estate) | ✅ | `grep -rhoiE "COLLATE [A-Za-z0-9_]+" */tables.sql \| sort \| uniq -c` |
| Referential cycle without deferral | ✅ | build the FK graph; flag cycles of length ≥ 2 whose FKs are all `NOT NULL` and not `DEFERRABLE` |
| INT key near ceiling | 🔬 | structural flag only — needs row counts |
| PG: legacy `serial` | ✅ | `grep -niwE "(small\|big)?serial" <dump>.sql` |
| PG: naive timestamp for an instant | ⚠️ | `grep -niE "timestamp( *\([0-6]\))?( +without time zone)?( \|,\|$)" <dump>.sql`, excluding `with time zone`; read whether it is an event instant |
| PG: `timetz`, `money`, `json` | ✅ | `grep -niwE "timetz\|time with time zone\|money\|json" <dump>.sql` (word `json`, not `jsonb`) |
| PG: unlogged business table | ⚠️ | `grep -niE "CREATE UNLOGGED TABLE" <dump>.sql` |
| PG: inheritance partitioning | ✅ | `grep -niE "INHERITS *\(" <dump>.sql` |
| PG: rewrite rules | ✅ | `grep -niE "CREATE (OR REPLACE )?RULE" <dump>.sql` |

## Indexes (`indexes.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| Nonclustered index duplicating clustered key | ⚠️ | compare `CREATE UNIQUE CLUSTERED INDEX … (cols)` vs `CREATE NONCLUSTERED INDEX … (same cols)` per table in `<db>/indexes.sql` (PG: an index equal to the PK's columns) |
| Prefix redundancy | ⚠️ | list index key lists per table; flag any that is a leading prefix of another and isn't `UNIQUE` or filtered |
| Heap (no clustered index) | ✅ | SQL Server only: tables in `tables.sql` with no `CLUSTERED` index/PK in `indexes.sql` → `grep -i "CLUSTERED" <db>/indexes.sql` and diff against table list |
| Missing FK index (cross-file) | ✅ | FK column lists in `tables.sql` that are not the **leading** columns (any order among themselves) of some index or PK/`UNIQUE` key in `indexes.sql`; then grade High/Medium by whether the parent is deleted or key-updated in `procedures.sql`/`triggers.sql` |
| Blanket fill factor | ⚠️ | SQL Server only: `grep -nioc "FILLFACTOR = 100" <db>/indexes.sql` |
| Low cardinality | 🔬 | flag indexes keyed on `flag_*`/`char(1)`; confirm with `COUNT(DISTINCT)` and a histogram on a live instance |
| Non-sargable predicate | ⚠️ | `grep -niE "(WHERE\|AND\|OR\|ON)\b.*\b(YEAR\|MONTH\|DAY\|UPPER\|LOWER\|LTRIM\|RTRIM\|SUBSTRING\|LEFT\|RIGHT\|CONVERT\|CAST\|ISNULL\|COALESCE\|DATEADD\|DATEDIFF\|DATEPART\|TO_CHAR) *\( *\[?[A-Za-z_]+\]?\.\[?[A-Za-z_]+" <db>/{views,procedures}.sql` (also catches `JOIN … ON`; read multi-line predicates) |
| Leading-wildcard `LIKE` | ✅ | `grep -niE "LIKE +N?'%\|LIKE +'%' *(\+\|\|\|)\|REGEXP\|~\*" <db>/{views,procedures}.sql` |
| Composite order vs predicates | ⚠️ | per composite index, collect the predicates on its columns in view/procedure bodies; flag a range on column 1 with equality on column 2, or column 1 never constrained |
| Index count per table | ⚠️ | `grep -ioE "ON +\[?[a-z_]+\]?\.?\[?[a-z_]+\]?" <db>/indexes.sql \| sort \| uniq -c \| sort -rn` |

## Procedures & functions (`procedures.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| RBAR (cursors / loops) | ✅ | `grep -niwc "cursor" <db>/procedures.sql` ; `grep -niw "@@FETCH_STATUS" <db>/procedures.sql` |
| Per-row hidden query | ✅/⚠️ | `CREATE FUNCTION` bodies containing `FROM` × call sites in views/procedures (✅); `SELECT` lists containing `(SELECT` (⚠️) |
| No error handling | ✅ | files with `BEGIN TRAN` but no `BEGIN TRY`: `grep -Li "begin try" <db>/procedures.sql` vs `grep -li "begin tran" <db>/procedures.sql` |
| Inflated transaction scope | ⚠️ | `CURSOR`/`WHILE`/`WAITFOR`/`sp_send_dbmail`/`xp_cmdshell`/linked-server names between `BEGIN TRAN` and `COMMIT`; `COMMIT` inside a loop |
| Distributed transaction | ✅ | `grep -niE "begin +distributed +tran\|openquery\|[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+" <db>/{procedures,triggers}.sql` |
| Dirty-read hint | ✅ | `grep -niE "nolock\|readuncommitted\|isolation level read uncommitted" <db>/{procedures,views,triggers}.sql` — count per file |
| Lost update (read-modify-write) | ⚠️ | `grep -niE "select +@[a-z0-9_]+ *= *[a-z_]+ +from" <db>/procedures.sql`, then read for a paired `UPDATE … SET <col> = @v` with no `UPDLOCK` |
| Check-then-act | ⚠️ | `grep -niE -A3 "if +(not +)?exists *\(\|if *\( *select +(count\|sum\|max)" <db>/procedures.sql`, then check for a locking hint or a backing `UNIQUE` |
| `MAX()+1` / manual keys | ✅ | `grep -niE "max *\([^)]*\) *\+ *1\|count *\( *\* *\) *\+ *1" <db>/{procedures,triggers}.sql` ; `grep -niE "IDENTITY_INSERT +[^ ]+ +ON\|CHECKIDENT" <db>/procedures.sql` (PG: `setval(`; Oracle: `ALTER SEQUENCE … RESTART`) |
| Elevated isolation without retry | ⚠️ | `grep -niE "isolation level (serializable\|snapshot)" <db>/procedures.sql` in bodies with no `1205\|3960\|40001\|40P01` handling |
| `= NULL` predicate | ✅ | `grep -niE "(WHERE\|AND\|OR\|ON\|WHEN\|IF)\b[^;]*[A-Za-z0-9_\]\)@] *(=\|<>\|!=) *NULL\b" <db>/{procedures,views,triggers}.sql` (excludes `SET x = NULL`) |
| `NOT IN (SELECT` | ✅/⚠️ | `grep -niE "NOT +IN *\( *SELECT" <db>/{views,procedures}.sql` → check the column's nullability in `tables.sql` |
| `ANSI_NULLS OFF` | ✅ | `grep -ni "SET ANSI_NULLS OFF" <db>/*.sql` |
| Catch-all predicate | ✅ | `grep -niE "@[A-Za-z0-9_]+ +IS +NULL +OR\|OR +@[A-Za-z0-9_]+ +IS +NULL\|= *(ISNULL\|COALESCE) *\( *@" <db>/{procedures,views}.sql` |
| `COUNT(*)` existence test | ✅ | `grep -niE "SELECT +@[A-Za-z0-9_]+ *= *COUNT *\( *\* *\)\|IF *\( *SELECT +COUNT" <db>/procedures.sql` |
| Offset pagination | ⚠️ | `grep -niE "OFFSET .* ROWS\|LIMIT .* OFFSET\|ROW_NUMBER *\( *\) *OVER" <db>/{procedures,views}.sql` |
| Dynamic SQL with concatenated values | ✅ | `grep -nioE "exec(ute)? *\(" <db>/procedures.sql`, then confirm `+ @`/`\|\|` concatenation into the string |
| Dynamic identifier without quoting | ⚠️ | `grep -niE "(ORDER BY\|FROM\|JOIN\|UPDATE\|INTO) *' *\+ *@" <db>/procedures.sql \| grep -vi quotename` |
| DDL in procedures | ✅ | `grep -niE "(CREATE\|ALTER\|DROP) +TABLE +[^#]\|TRUNCATE +TABLE" <db>/procedures.sql` |
| Optimizer directive | ✅ | `grep -niE "WITH *\( *INDEX *\(\|OPTION *\(.*(JOIN\|FORCE ORDER\|USE PLAN)\|/\*\+" <db>/{procedures,views}.sql` |
| `INSERT` without column list | ✅ | `grep -niE "INSERT +(INTO +)?[A-Za-z0-9_.#@\[\]]+ +(VALUES\|SELECT\|EXEC)\b" <db>/{procedures,triggers}.sql` |
| Random sampling by sort | ✅ | `grep -niE "ORDER BY +(NEWID\|RAND\|RANDOM\|DBMS_RANDOM\.VALUE) *\(" <db>/{views,procedures}.sql` |
| Unlength cast | ✅ | `grep -nioE "cast\([^)]* as +varchar\)" <db>/procedures.sql` (no length) |
| Comma joins | ⚠️ | `grep -niE "FROM +[a-z_]+ *, *[a-z_]+" <db>/procedures.sql` |
| `SELECT *` | ✅ | `grep -nioc "select \*" <db>/procedures.sql` |
| Missing `SET NOCOUNT` | ✅ | SQL Server only: `grep -Li "set nocount" <db>/procedures.sql` |
| Hardcoded cross-DB call | ✅ | `grep -niE "[A-Z_]+\.dbo\.\|[A-Z_]+\.\." <db>/procedures.sql` |
| No sniffing mitigation (estate-level) | 🔬 | `grep -ric "option *( *recompile\|optimize for" */procedures.sql` — absence is an estate observation, **not** a per-proc defect |
| PG: false `IMMUTABLE` | ⚠️ | `CREATE FUNCTION … IMMUTABLE` blocks whose body contains `FROM`, `now()`, `current_setting` |
| PG: concatenated `EXECUTE` | ✅ | `grep -niE "EXECUTE +'[^']*' *\|\|" <dump>.sql` |
| PG: swallowed errors | ✅ | `grep -niE -A1 "WHEN +OTHERS +THEN" <dump>.sql \| grep -iE "NULL;\|RAISE NOTICE"` |

## Views (`views.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| `TOP 100 PERCENT … ORDER BY` hack | ✅ | `grep -niB2 "ORDER BY" <db>/views.sql \| grep -i "TOP 100 PERCENT"` |
| Nested view pyramid | ✅ | cross-reference: a view whose `FROM`/`JOIN` names another `CREATE VIEW` in the dumps |
| View re-joined to its base table | ⚠️ | consumer `FROM`/`JOIN` list ∩ the referenced view's `FROM`/`JOIN` list ≠ ∅ |
| Bag view | ⚠️ | select list with no PK/`UNIQUE` column set of any source and no `DISTINCT`/`GROUP BY`; `UNION ALL` with no branch-distinguishing literal column |
| Fan-out aggregate | ⚠️ | `GROUP BY` with ≥ 2 joins to different child tables on one parent key; `grep -niE "(SUM\|COUNT) *\( *DISTINCT" <db>/views.sql` beside several joins |
| `DISTINCT` over join | ⚠️ | `grep -niE "SELECT +DISTINCT" <db>/views.sql` → confirm ≥ 2 sources |
| Needless `UNION` | ⚠️ | `grep -niwE "union" <db>/views.sql \| grep -viw "union all"` → branches provably disjoint |
| Updatable view without `CHECK OPTION` | ✅/⚠️ | `CREATE VIEW` blocks containing `WHERE` and no `check option` (✅); written through by procedures or an `INSTEAD OF` trigger (⚠️) |
| `INSTEAD OF` trigger on a view | ✅ | `grep -niE "INSTEAD +OF" <db>/triggers.sql` naming a view |
| `SELECT *` in view | ✅ | `grep -nioc "select \*" <db>/views.sql` |
| Missing `SCHEMABINDING` | ✅ | SQL Server only: `grep -Li "schemabinding" <db>/views.sql` |
| `CREATE OR ALTER` era-mismatch | ✅ | `grep -ni "CREATE OR ALTER" <db>/views.sql` |
| Catch-all (many joins) | ⚠️ | count `JOIN`/`,` sources per view; flag outliers |
| PG: view over RLS table without `security_invoker` | ✅ | views selecting from a table that has `ENABLE ROW LEVEL SECURITY`, with no `security_invoker = true` |

## Triggers (`triggers.md`)

| Anti-pattern | Conf. | Command |
|---|---|---|
| Multi-row scalar-from-pseudo-table (CRITICAL) | ✅ | `grep -niE "SELECT +@[A-Za-z0-9_]+ *=.*FROM +(DELETED\|INSERTED)" <db>/triggers.sql` |
| Trigger-emulated constraint / cross-row validation | ⚠️ | `grep -niE -B2 -A4 "if +(not +)?exists *\(" <db>/triggers.sql` with `ROLLBACK\|RAISERROR\|THROW` in the branch and no `UPDLOCK\|HOLDLOCK\|SERIALIZABLE\|TABLOCKX`; child `DELETE` keyed on `DELETED` |
| Hidden side-effect (writes other tables) | ⚠️ | `grep -niE "(UPDATE\|INSERT\|DELETE)" <db>/triggers.sql` targeting a table ≠ trigger's own |
| Non-transactional side effect | ✅ | `grep -niE "sp_send_dbmail\|xp_cmdshell\|sp_OA\|dblink\|http_\|plpython3?u\|plperlu" <db>/triggers.sql` |
| Transaction-scope inflation | ✅ | `grep -niwE "cursor\|while" <db>/triggers.sql` |
| Hardcoded cross-DB write | ✅ | `grep -niE "[A-Z_]+\.\." <db>/triggers.sql` |
| Cascading/recursive | ⚠️ | build a trigger→table→trigger graph; flag cycles |
| Fires on replication / load | ⚠️ | side-effect triggers with no `NOT FOR REPLICATION` (SQL Server) / no `session_replication_role` guard (PG) |
| PG: `NEW` assigned in an `AFTER` trigger | ⚠️ | functions assigning `NEW.` attached by `CREATE TRIGGER … AFTER … FOR EACH ROW` |
| PG: order-dependent triggers | ⚠️ | count `CREATE TRIGGER … ON t` per (table, timing, event) > 1 |

## Security & data sensitivity (`audit-lenses.md` §6)

| Anti-pattern | Conf. | Command |
|---|---|---|
| Untrusted/disabled constraint | ✅ | `grep -niE "WITH +NOCHECK\|NOCHECK +CONSTRAINT\|NOT +VALID\|NOT +ENFORCED" <db>/*.sql` (grade `NOT VALID` and `NOT ENFORCED` separately — engine table) |
| Integrity switched off in scripts | ✅ | `grep -niE "DISABLE TRIGGER (ALL\|USER)\|session_replication_role" <db-or-migrations>` |
| Elevated execution context | ✅ | `grep -ni "EXECUTE AS" <db>/procedures.sql` |
| Plaintext secret in body | ⚠️ | `grep -niE "(password\|pwd\|secret\|connectionstring) *=" <db>/*.sql` |
| Password column (shape) | ⚠️ | `grep -niE "\[?(password\|passwd\|pwd\|clave\|contrase(n\|ñ)a)\]? +n?(var)?char\(([1-9]\|[1-3][0-9])\)" <db>/tables.sql` — short width and no hash/salt sibling |
| Weak or fast hash on credentials | ✅ | `grep -niE "HASHBYTES *\( *'(MD2\|MD4\|MD5\|SHA\|SHA1)'\|\bMD5 *\(\|\bSHA1 *\(\|STANDARD_HASH *\(.*'(MD5\|SHA1)'" <db>/*.sql` |
| Reversible password encryption | ⚠️ | `grep -niE "(ENCRYPT\|DECRYPT)BY(PASSPHRASE\|KEY\|CERT)\|AES_(EN\|DE)CRYPT\|pgp_sym_(en\|de)crypt" <db>/*.sql` near a password column |
| Plaintext password compare in SQL | ⚠️ | `grep -niE "(password\|pwd\|clave) *= *@" <db>/procedures.sql` |
| PII/sensitive column | 🔬 | identify by name (`rut`, `ap_paterno`, `sueldo`, `pago`, `nombre`); sensitivity is contextual |
| PG: `SECURITY DEFINER` without `search_path` | ✅ | `grep -niE "SECURITY DEFINER" <dump>.sql`, then check the same function has `SET search_path` (block-aware) |
| PG: definer function executable by `PUBLIC` | ✅ | a `SECURITY DEFINER` function with no `REVOKE EXECUTE … FROM PUBLIC` |
| PG: untrusted language | ✅ | `grep -niE "LANGUAGE +'?(plpython3?u\|plperlu\|pltclu\|c)'?" <dump>.sql` |
| PG: broad grants | ✅ | `grep -niE "GRANT .* TO PUBLIC\|GRANT (ALL\|CREATE) ON SCHEMA public" <dump>.sql` |
| PG: ownership | ⚠️ | `grep -nioE "OWNER TO [a-z_]+" <dump>.sql \| sort \| uniq -c` — expect one `NOLOGIN` owner role per schema |
| PG: RLS policy not active | ✅ | `CREATE POLICY … ON t` with no `ALTER TABLE t ENABLE ROW LEVEL SECURITY`; `ENABLE` without `FORCE` when the app connects as owner |
| PG: missing schema `USAGE` / default privileges | ⚠️ | grants on tables but no `GRANT USAGE ON SCHEMA`; no `ALTER DEFAULT PRIVILEGES … FOR ROLE <owner>` |

> Note: on SQL Server and Oracle, GRANTs, role memberships, logins and encryption metadata are
> typically **not** present in these DDL dumps — those security aspects are out of static scope and
> must be checked on the server. A default PostgreSQL schema dump does include them (audit-lenses §6).
