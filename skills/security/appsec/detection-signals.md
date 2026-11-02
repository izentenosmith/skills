# Detection Signals — Grep and Pattern Appendix, per Stack

> Signals for the rubric's anti-patterns, each with its **confidence tag** (✅ decidable / ⚠️ proxy /
> 🔬 needs-data — see [`scoring.md`](scoring.md)). Run from the repository root. **A match is a
> candidate**: trace the value from its source to the sink and confirm the missing check before
> recording a finding. A concatenation over a constant is not injection; a "safe" API fed a
> request-derived identifier may be.
>
> Prefer real tools when present — they understand data flow: Semgrep (`p/owasp-top-ten`,
> `p/<language>`), CodeQL, `bandit`, `gosec`, `brakeman`, SpotBugs + find-sec-bugs,
> `eslint-plugin-security`, `gitleaks`, `trufflehog`, `osv-scanner`, `trivy fs`, `syft`/`grype`,
> ScanCode. Grep is the fallback and the triage scan.
>
> The .NET signals marked **(ONET)** come from Troy Hunt's book; the rest generalise the same
> anti-pattern to other stacks.

## Stack detection (run first)

| Stack | Markers |
|---|---|
| .NET | `*.csproj`, `*.sln`, `web.config`, `appsettings*.json`, `Program.cs` |
| Java / Spring | `pom.xml`, `build.gradle*`, `application*.properties\|yml`, `@SpringBootApplication` |
| Node | `package.json` (+ `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`); `express`, `@nestjs/*`, `next` |
| Python | `pyproject.toml`, `requirements*.txt`, `Pipfile.lock`, `poetry.lock`; `django`, `flask`, `fastapi` |
| PHP | `composer.json`/`composer.lock`; `laravel/framework`, `symfony/*` |
| Go | `go.mod`/`go.sum`; `net/http`, `gin`, `echo`, `fiber` |
| Ruby | `Gemfile`/`Gemfile.lock`; `rails` |

## Inventory

| What | Command |
|---|---|
| Routes (Express/Koa/Fastify) | `grep -rnE '\.(get\|post\|put\|patch\|delete\|all)\(\s*["'"'"'/]' --include='*.{js,ts}' . \| grep -v node_modules` |
| Routes (Spring) | `grep -rnE '@(Get\|Post\|Put\|Patch\|Delete\|Request)Mapping' --include='*.java' --include='*.kt' .` |
| Routes (ASP.NET) | `grep -rnE '\[(Http(Get\|Post\|Put\|Patch\|Delete)\|Route)\b' --include='*.cs' .`; `Map(Get\|Post\|Put\|Delete)\(` for minimal APIs |
| Routes (Django / Flask / FastAPI) | `grep -rnE '\b(path\|re_path)\(' --include='urls.py' .`; `grep -rnE '@(app\|router\|bp)\.(route\|get\|post\|put\|patch\|delete)\(' --include='*.py' .` |
| Routes (Laravel / Rails / Go) | `routes/*.php`; `config/routes.rb`; `grep -rnE '\.(HandleFunc\|Handle\|GET\|POST\|PUT\|DELETE)\(' --include='*.go' .` |
| Auth attributes / middleware | `[Authorize]`, `[AllowAnonymous]`, `@PreAuthorize`, `permitAll`, `@login_required`, `IsAuthenticated`, `auth` middleware, `before_action :authenticate` |
| Secrets (tree and history) | `gitleaks detect --redact`; `trufflehog git file://. --only-verified` — record kind and location only |

## input

| Anti-pattern | Stack | Signal | Conf. |
|---|---|---|---|
| SQL concatenation | .NET (ONET) | `new SqlCommand\(.*\+`; `"SELECT .*" \+ Request\.`; `ExecuteSqlRaw\(\$"`; `FromSqlRaw\(.*\+` | ✅ traced |
| SQL concatenation | Java | `(createStatement\|executeQuery\|executeUpdate\|prepareStatement)\(.*\+`; `createQuery\(.*\+`; `createNativeQuery\(.*\+`; `@Query\(.*\+` | ✅ traced |
| SQL concatenation | Node | `\.(query\|execute\|raw)\(\s*` + backtick containing `\$\{`; `sequelize\.query\(.*\$\{`; `knex\.raw\(.*\+` | ✅ traced |
| SQL concatenation | Python | `execute\(\s*f["']`; `execute\(.*%\s`; `execute\(.*\.format\(`; `\.raw\(`, `\.extra\(`, `RawSQL\(` (Django); `text\(f` (SQLAlchemy) | ✅ traced |
| SQL concatenation | PHP | `(mysqli_query\|->query)\(.*\$_(GET\|POST\|REQUEST\|COOKIE)`; `"SELECT.*\$` in `query(` | ✅ traced |
| SQL concatenation | Go / Ruby | `db\.(Query\|Exec\|QueryRow)\(fmt\.Sprintf`; `where\("\#\{`, `find_by_sql\(".*\#\{` | ✅ traced |
| Identifier from input | all | `ORDER BY` / table / column built from a request value (parameters can't carry identifiers) | ✅ traced |
| NoSQL operator injection | Node | `\.(find\|findOne\|updateOne\|deleteOne)\(\s*req\.(body\|query)`; `\$where` | ✅ |
| OS command | all | `Process\.Start\(`; `Runtime\.getRuntime\(\)\.exec\|ProcessBuilder\(`; `child_process\.(exec\|execSync)\(`; `os\.system\(\|subprocess\..*shell=True`; `exec\(\|system\(\|shell_exec\(\|passthru\(\|` + backticks (PHP); `exec\.Command\("(sh\|bash)", "-c"`; `system\(\|%x\(` (Ruby) | ✅ traced |
| LDAP / XPath | all | filter strings built with `+`/interpolation passed to `DirectorySearcher`, `search(`, `ldap_search`, `XPath` evaluate | ✅ traced |
| Template / eval injection | all | `eval\(`, `new Function\(`, `render_template_string\(` with data, `Template\(.*request`, `ERB\.new\(params` | ✅ traced |
| Request validation off | .NET (ONET) | `ValidateRequest="false"`; `<pages validateRequest="false"`; `requestValidationMode="2.0"` | ✅ |
| Raw output | .NET (ONET + current) | `Literal\.Text\s*=`, `Label\.Text\s*=.*Request`; `@Html\.Raw\(`; `<%=` where `<%:` belongs; `RegisterClientScriptBlock\(.*\+` | ✅ traced |
| Raw output | Java | `<%=\s*request\.getParameter`; `escapeXml="false"`; `th:utext` | ✅ traced |
| Raw output | Node / front end | EJS `<%-`; Handlebars `\{\{\{`; Pug `!=`; `dangerouslySetInnerHTML`; `v-html`; `\.innerHTML\s*=`, `outerHTML`, `insertAdjacentHTML`, `document\.write\(`; `res\.send\(req\.` | ✅ traced |
| Raw output | Python | `\|safe`; `mark_safe\(`; `\{% autoescape off`; `Markup\(` over input | ✅ traced |
| Raw output | PHP / Ruby / Go | `echo \$_(GET\|POST)`; `<\?= \$` without `htmlspecialchars\(.*ENT_QUOTES`; `\{!! .* !!\}` (Blade); `html_safe`, `raw\(` (Rails); `text/template` used for HTML, `template\.HTML\(` | ✅ traced |
| Encoder wrong for context | all | encoded value placed inside `<script>`, `on*=` attributes, `href=`/`src=` (javascript: URLs), `style=` | ✅ |
| XXE | .NET / Java / PHP / Python | `XmlDocument` with `XmlResolver` set / `DtdProcessing.Parse`; `DocumentBuilderFactory` without `disallow-doctype-decl`; `libxml_disable_entity_loader(false)` / `LIBXML_NOENT`; `lxml.etree.XMLParser(resolve_entities=True)` | ✅ |
| Native deserialisation | all | `BinaryFormatter`, `NetDataContractSerializer`, `TypeNameHandling\.(All\|Auto)`; `ObjectInputStream\.readObject`, `XMLDecoder`; `node-serialize`; `pickle\.loads?\(`, `yaml\.load\(` without `SafeLoader`; `unserialize\(\$_`; `Marshal\.load`, `YAML\.load\(` (Ruby < Psych 4) | ✅ traced |
| SSRF | all | `HttpClient\.(Get\|Send)`, `WebClient`, `RestTemplate`, `WebClient\.create\(`, `fetch\(\|axios\.\|got\(\|http\.get\(`, `requests\.(get\|post)\(\|urllib\.request\.urlopen\(`, `file_get_contents\(\$_\|curl_init\(\$`, `http\.Get\(`, `Net::HTTP\|open-uri` — with a request-derived URL | ✅ traced |
| Path traversal | all | `Path\.Combine\(.*Request`, `File\.(Open\|ReadAll)`; `new File\(.*getParameter`; `path\.join\(.*req\.`, `fs\.(readFile\|createReadStream)\(.*req\.`, `res\.sendFile\(.*req\.`; `open\(.*request\.`, `send_file\(.*request`; `include\(\$_\|fopen\(\$_`; `filepath\.Join\(.*r\.URL`; `send_file params` | ✅ traced |
| Static root too wide | Node | `express\.static\(['"]?\.['"]?\)`, `express\.static\(__dirname\)` | ✅ |
| Upload handling | all | multer/formidable/`IFormFile`/`MultipartFile`/`request.files` saved under `public`/`wwwroot`/`static` with `originalname`/`FileName`; no size limit | ✅ |
| Open redirect | all | `Response\.Redirect\(Request\.QueryString` **(ONET)**, `Redirect\(returnUrl\)` without `Url\.IsLocalUrl`; `sendRedirect\(request\.getParameter`, `"redirect:" \+`; `res\.redirect\(req\.(query\|body\|params)`; `HttpResponseRedirect\(request\.GET` without `url_has_allowed_host_and_scheme`, `redirect\(request\.args`; `header\("Location: " \. \$_`; `redirect_to params` | ✅ |
| Redirect parameter names | all | `[?&](url\|next\|return\|returnUrl\|redirect\|redirect_uri\|dest\|continue\|goto)=` in routes and links | ⚠️ |

## authentication

| Anti-pattern | Stack | Signal | Conf. |
|---|---|---|---|
| Session ID in URL | .NET (ONET) | `<sessionState cookieless="(true\|UseUri\|AutoDetect)"` | ✅ |
| Session ID in URL | Java / PHP | `;jsessionid=`, `tracking-modes` containing `URL`; `session.use_trans_sid\s*=\s*1`, `session.use_only_cookies\s*=\s*0` | ✅ |
| No rotation at login | Java / Node / PHP / Python | `sessionFixation\(\)\.none\(\)`; no `req\.session\.regenerate` in login; no `session_regenerate_id\(true\)`; Django `login()` bypassed by manual session writes | ✅ |
| Hand-rolled login | all | manual password compare then `Session\["User"\]`/`req\.session\.user =`/`$_SESSION\['user'\]`; identity read from `req\.cookies\.` | ✅ |
| Weak session store / secret | Node / Python | `express-session` with default `MemoryStore` in prod; `secret:\s*['"][^'"]{0,16}['"]`; hard-coded `SECRET_KEY`/`app.secret_key` | ✅ |
| Cookie flags | all | `httpOnlyCookies="false"`, `requireSSL="false"` **(ONET)**; `HttpCookie` without `.Secure`/`.HttpOnly`; `SESSION_COOKIE_SECURE = False`, `CSRF_COOKIE_SECURE = False`; `cookie:\s*\{[^}]*secure:\s*false`; `res\.cookie\([^)]*\)` without `httpOnly`/`secure`/`sameSite`; `session.cookie_secure\s*=\s*0`; `server.servlet.session.cookie.secure=false` | ✅ |
| Long sessions | all | `<forms .*timeout="[0-9]{4,}"`, `slidingExpiration="true"`; `SESSION_COOKIE_AGE` very large; `maxAge:` days+; `remember_me` storing credentials | ✅ |
| Password hashing | .NET (ONET) | `MD5\.Create\(\)`, `SHA1(Managed)?` over a password; `passwordFormat="(Clear\|Encrypted)"`; `enablePasswordRetrieval="true"`; `Rfc2898DeriveBytes` with low iterations | ✅ |
| Password hashing | others | `MessageDigest\.getInstance\("(MD5\|SHA-1\|SHA-256)"\)` on passwords, `NoOpPasswordEncoder`, `StandardPasswordEncoder`; `crypto\.createHash\('(md5\|sha1\|sha256)'\)` on passwords; `hashlib\.(md5\|sha1\|sha256)\(` on passwords, `UnsaltedMD5PasswordHasher`, `MD5PasswordHasher` first in `PASSWORD_HASHERS`; `md5\(\$pass\|sha1\(\$pass` (PHP, instead of `password_hash`); `Digest::(MD5\|SHA1)` (Ruby) | ✅ |
| JWT pitfalls | all | `algorithms:\s*\[.*none`, `verify=False`, `options=\{"verify_signature": False\}`, `jwt\.decode\(` without `algorithms`; `ValidateLifetime = false`, `ValidateIssuer = false`, `ValidateAudience = false`; `ignoreExpiration: true`; short HMAC secrets | ✅ |
| Recovery flow | all | `mail\(.*password`, templates that render a password; reset tokens without expiry column/TTL; `"no account"`/`"user not found"` strings in reset/login responses; auto `login()` in reset handlers | ✅ |
| No throttling | all | login/reset/MFA routes without a rate-limit middleware (`express-rate-limit`, `django-ratelimit`, `AspNetCore.RateLimiting`, `Rack::Attack`, Spring/bucket4j) | ⚠️ (🔬 if a gateway may throttle) |
| Weak policy | .NET (ONET) / all | `minRequiredPasswordLength="[0-7]"`; `AUTH_PASSWORD_VALIDATORS` empty; no breached-password check | ✅ |

## access

| Anti-pattern | Stack | Signal | Conf. |
|---|---|---|---|
| Missing function-level authz | .NET (ONET) | no `<location path="Admin"><system.web><authorization><deny users="*"`; controllers without `[Authorize]`; `[AllowAnonymous]` on state-changing actions; services (`.svc`, `[OperationContract]`, `[WebMethod]`) with no role demand; menu gating by `User.Identity.Name ==` | ✅ |
| Missing function-level authz | Java / Node / Python / PHP / Ruby / Go | `permitAll\(\)` on broad matchers, missing `@PreAuthorize`/`@Secured`; routers without auth middleware; views without `@login_required`/`LoginRequiredMixin`/`permission_classes`; DRF `AllowAny`; Laravel routes outside `auth` middleware; `skip_before_action :authenticate`; Go handlers registered outside the auth-wrapped mux | ✅ |
| UI-only check | all | `if (isAdmin)` / `v-if="user.isAdmin"` / `@if(User.IsInRole` with no matching server check on the target route | ✅ traced |
| IDOR | all | `Single\(.*== ?id\)` / `Find\(id\)` from a route value **(ONET)**; `findById\(id\)` / `repo\.findById`; `Model\.findById\(req\.params\.id\)`; `get_object_or_404\(Model, pk=` without owner filter, DRF `queryset = Model.objects.all()`; `WHERE id\s*=\s*\$_GET`; `Model\.find\(params\[:id\]\)` instead of `current_user.models.find` — with no `owner`/`user_id`/`tenant_id` predicate | ✅ traced |
| Tenant from request | all | `tenant_?[Ii]d` read from body/query/header and used in queries | ✅ |
| Client-controlled signal | all | branches on `User-Agent`, `Referer`, `X-Forwarded-For`, `req\.ip`, `REMOTE_ADDR`, `Accept`; `<input type="hidden" name="(price\|role\|isAdmin\|userId)` | ✅ |
| CSRF off | .NET / Java / Python / PHP / Rails | missing `[ValidateAntiForgeryToken]`/`AutoValidateAntiforgeryToken`; `csrf\(\)\.disable\(\)`; `@csrf_exempt`, `CsrfViewMiddleware` removed; Flask without `CSRFProtect`; `VerifyCsrfToken` `$except`; `skip_before_action :verify_authenticity_token`, `protect_from_forgery` absent | ✅ |
| CSRF off | Node | cookie-session app with no `csurf`/`csrf-csrf`/`lusca` and no `sameSite` | ✅ |
| State change on GET | all | GET routes that call `save`/`update`/`delete`/`insert` | ✅ |
| CORS | all | `AllowAnyOrigin\(\)\.AllowCredentials`, `SetIsOriginAllowed\(_ => true\)`; `@CrossOrigin\("\*"\)`, `allowedOriginPatterns\("\*"\)` with credentials; `cors\(\{\s*origin:\s*(true\|'\*')`, `credentials:\s*true`; `CORS_ALLOW_ALL_ORIGINS = True`, `CORS_ORIGIN_ALLOW_ALL`; reflected `Access-Control-Allow-Origin` from the request | ✅ |
| Mass assignment | all | `TryUpdateModel\(`/binding entity types directly; `@ModelAttribute` on entities; `Model\.(create\|update)\(req\.body\)`, `Object\.assign\(model, req\.body\)`; DRF `fields = '__all__'`; Laravel `$guarded = \[\]`; Rails `params\.permit!` | ✅ |
| Race / workflow | all | read-then-write on balances/quotas/coupons without transaction, `SELECT … FOR UPDATE` or conditional update; confirm/finalise endpoints that don't check prior state; `price`/`amount` read from the request | ⚠️ |

## crypto

| Anti-pattern | Stack | Signal | Conf. |
|---|---|---|---|
| Weak cipher / mode | .NET (ONET) | `DESCryptoServiceProvider`, `TripleDES`, `RC2`; `CipherMode\.ECB`; `RijndaelManaged` with hard-coded key/IV | ✅ |
| Weak cipher / mode | others | `Cipher\.getInstance\("(DES\|DESede\|RC4\|AES)"\)` (default ECB), `"AES/ECB`; `crypto\.createCipher\(` (deprecated), `aes-.*-ecb`; `AES\.MODE_ECB`, `DES\.new`; `mcrypt_`, `openssl_encrypt\(.*ecb`; `des\.NewCipher`, `cipher\.NewCBCEncrypter` without MAC | ✅ |
| Weak hash for security | all | `MD5`/`SHA1` used for signatures, tokens, integrity or certificates; `hash\(key \+ message\)` instead of HMAC | ✅ |
| Non-crypto RNG | all | `new Random\(\)` (.NET/Java), `java\.util\.Random`, `Math\.random\(\)`, Python `random\.` (not `secrets`), `rand\(\)`/`mt_rand\(\)`/`uniqid\(\)` (PHP), `math/rand` (Go), `rand\(` (Ruby) — in token, ID, salt or IV generation | ✅ |
| Static IV / nonce | all | IV/nonce constants or zero arrays; nonce from a counter that resets | ✅ |
| Non-constant-time compare | all | `==`/`.equals`/`===` on HMACs, tokens, signatures (use `CryptographicOperations.FixedTimeEquals`, `MessageDigest.isEqual`, `crypto.timingSafeEqual`, `hmac.compare_digest`, `hash_equals`, `subtle.ConstantTimeCompare`, `ActiveSupport::SecurityUtils.secure_compare`) | ✅ |
| Hard-coded key / secret | all | `(password\|passwd\|secret\|api[_-]?key\|token\|private[_-]?key\|connectionstring)\s*[:=]\s*["'][^"']{6,}`; `<machineKey .*validationKey="[0-9A-F]` **(ONET)**; `-----BEGIN (RSA\|EC\|OPENSSH) PRIVATE KEY-----`; `AKIA[0-9A-Z]{16}`; `xox[baprs]-`; `ghp_[A-Za-z0-9]{36}` | ✅ — kind and location only |
| Plain config secrets | .NET (ONET) / others | `<connectionStrings>` with `Password=` not encrypted; `appsettings*.json` with `Password=`; `application.properties` `spring.datasource.password=`; committed `.env` | ✅ |
| TLS verification off | all | `ServerCertificateValidationCallback\s*=.*true`, `ServerCertificateCustomValidationCallback = .*=> true`; custom `X509TrustManager` with empty methods, `NoopHostnameVerifier`; `rejectUnauthorized:\s*false`, `NODE_TLS_REJECT_UNAUTHORIZED=0`; `verify=False`; `CURLOPT_SSL_VERIFYPEER.*(false\|0)`; `InsecureSkipVerify:\s*true`; `verify_mode.*VERIFY_NONE` | ✅ |

## configuration

| Anti-pattern | Stack | Signal | Conf. |
|---|---|---|---|
| Debug on | .NET (ONET) | `<compilation debug="true"`; `<trace enabled="true"` with `localOnly="false"`; `Trace\.(Warn\|Write)\(` carrying secrets; no `<deployment retail="true"/>` in machine config (🔬 off-repo) | ✅ |
| Debug on | others | `spring.devtools`, `server.error.include-stacktrace=always`; `NODE_ENV` unset/`development` in prod start scripts, `errorhandler()` in prod; `DEBUG\s*=\s*True`, `app\.run\(.*debug=True`; `display_errors\s*=\s*On`, `APP_DEBUG=true`; `config.consider_all_requests_local = true` in production.rb; `gin.SetMode(gin.DebugMode)` | ✅ |
| Verbose errors | .NET (ONET) / others | `<customErrors mode="Off"`, no `defaultRedirect`; `UseDeveloperExceptionPage\(\)` outside a dev guard; exception `.message`/`.stack`/`traceback` returned in responses | ✅ |
| Management exposure | all | `management.endpoints.web.exposure.include=\*`; GraphQL `introspection: true`/playground in prod; Swagger UI enabled in prod; `phpinfo\(\)`; `autoindex on`, `Options +Indexes`, `serve-index`; `/admin` routes without auth | ✅ |
| Hosts wildcard | Python / .NET | `ALLOWED_HOSTS = \['\*'\]`; `"AllowedHosts": "\*"` | ✅ |
| Headers missing | all | absence of `helmet\(`, `SecurityMiddleware` settings (`SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`), `UseHsts\(`, Spring `headers\(\)` config, `secure_headers` gem; `X-Powered-By` not disabled (`app.disable\('x-powered-by'\)`, `expose_php = Off`, `removeServerHeader`) | ⚠️ (🔬 if a proxy sets them) |
| Mixed content / http links | all | `http://` URLs for scripts, styles, forms and API bases in templates and config | ✅ |
| Fail-open | all | `catch\s*\([^)]*\)\s*\{\s*return (true\|null\|next\(\))` in auth/validation; `except.*:\s*(pass\|return True)` in permission checks | ✅ |
| Default creds / seed users | all | `admin/admin`, `password123`, `changeme` in seeds, migrations, `docker-compose*.yml`, `appsettings.Production.json` | ✅ |

## dependencies

| Anti-pattern | Signal | Conf. |
|---|---|---|
| Vulnerable components | `osv-scanner -r .`; `trivy fs .`; `npm audit --omit=dev`; `pip-audit`; `dotnet list package --vulnerable --include-transitive`; `mvn org.owasp:dependency-check-maven:check`; `composer audit`; `govulncheck ./...` (reachability-aware); `bundler-audit` — cross-check against a known-exploited list | ✅ presence; ⚠️ reachability unless the tool traces it |
| No lockfile | `package.json` without a lockfile; `requirements.txt` without hashes/pins; `Gemfile` without `Gemfile.lock`; `.csproj` floating `Version="*"` | ✅ |
| Floating ranges | `"\^\|~\|\*\|latest\|>="` in `package.json`; unpinned lines in `requirements.txt`; `implementation '.*:\+'` (Gradle) | ✅ |
| EOL runtime | `engines.node`, `.nvmrc`, `python_requires`, `TargetFramework`, `<java.version>`, `go` directive, `.ruby-version` vs vendor lifecycle | ✅ |
| 0.x in production | `"[a-z@/-]+":\s*"[\^~]?0\.` in runtime dependencies | ⚠️ |
| Install scripts / typosquats | `preinstall\|postinstall` in dependency manifests; names one edit away from popular packages | ⚠️ |
| Integrity | `<script src="https?://` without `integrity=`; `curl .* \| (sh\|bash)` in build files | ✅ |
| Vendored copies | `vendor/`, `third_party/`, `lib/` copies with version headers behind upstream | ✅ |
| Licence inventory | `syft . -o spdx-json` / `cyclonedx-*`; `scancode -l .`; `licensee detect`; `npx license-checker --summary`; `pip-licenses`; look for `GPL\|AGPL\|LGPL\|SSPL\|BUSL` in runtime dependencies; NOTICE/THIRD_PARTY files in release artefacts | ✅ |

## logging

| Anti-pattern | Signal | Conf. |
|---|---|---|
| Events not logged | login, logout, failed login, authorisation-denied, role-change, password/MFA-change and admin handlers without a log call | ✅ |
| Secrets in logs | `log.*(req\.body\|request\.body\|req\.headers\|Request\.Headers\|password\|token\|authorization\|cookie)`; `console\.log\(req`; morgan/serilog/logback patterns including `Authorization`/`Cookie`; failed-login logs that include the submitted password | ✅ |
| Log injection | `log.*\(.*\+\s*(req\.\|request\.\|params)` with plain-text formatters and no newline encoding | ✅ |
| Local-only logs | file appenders only, no shipper/collector config, containers writing to files not stdout | ✅/🔬 |
| No alerting | no alert rules in repo for auth failures/denials | 🔬 when alerts live elsewhere |

## browser

Read the **response headers** per route class as well as the code: `curl -sI` against an
environment the user owns and named, or the framework's header configuration. Signals marked **[G]**
generalise TW/WSD's point to a stack the books don't cover.

| Anti-pattern | Signal | Conf. |
|---|---|---|
| Type left to the browser (A25) | responses without `Content-Type: …; charset=`; no `X-Content-Type-Options: nosniff`; `res.type('text/plain'\|'application/octet-stream')` or `send_file(…, mimetype=<user>)` / `send_data type: params[…]` for user data; `Content-Type` copied from `req.headers`, a multipart part or a DB column; `charset=UTF8` | ✅ |
| User files on the app origin (A26) | uploads written under `public/`, `static/`, `wwwroot/`, `media/` on the app host; download handlers without `Content-Disposition: attachment` or with `inline`; file name from `originalname`/`FileName`/`filename`; `.svg`/`.html`/`.pdf` served as-is | ✅ |
| Header / response splitting (A27) | `setHeader\(`, `res\.header\(`, `header\(` (PHP), `response\.headers\[`, `HttpResponse\(.*\)\[`, `Response\.AddHeader`, `w\.Header\(\)\.Set\(` [G], `redirect\(` — with request-derived values and no CR/LF/NUL stripping; `Set-Cookie`/`Location` built by concatenation; mail `To`/`Subject` from input [G] | ✅ traced |
| Ad-hoc URL checks (A28) | `startsWith\(["']/["']\)`, `\.includes\(.*host`, `\.endsWith\(["'][a-z0-9.-]+["']\)`, `indexOf\(` on URLs; `url\.startswith\(["']http`; blacklists for `javascript:`/`data:`; `href=\{`, `:href=`, `[href]=`, `th:href` bound to request data; one parser for the check and another (or the raw string) for the use | ✅ traced |
| Unpinned messaging (A29) | `postMessage\(.*,\s*["']\*["']\)`; `addEventListener\(["']message` without `event\.origin ===`/`==` against a constant, or with `indexOf`/`includes`/`endsWith`/regex; `document\.domain\s*=`; `window\.name`, `location\.hash` read as data; message data into `innerHTML`/`eval`/`Function` | ✅ |
| CORS (A30) | `Access-Control-Allow-Origin` set from `req.headers.origin`/`Request.Headers["Origin"]`; `null` allowed; `*` with `Access-Control-Allow-Credentials: true`; `allowedOriginPatterns\("\*"\)`; `cors\(\{\s*origin:\s*true`; `CORS_ALLOW_ALL_ORIGINS`; regex origin checks without anchors; no `Vary: Origin` [G]; `Access-Control-Allow-Headers: *` | ✅ |
| Cookie scope (A31) | `Domain=\.?[a-z0-9-]+\.[a-z]+` on session/auth cookies; session cookie without the `__Host-` prefix; CSRF validation comparing `cookies\[…\] == (params\|headers)\[…\]` with no session binding or HMAC; DNS (if supplied): `localhost.<domain>` → `127.0.0.1`, wildcard records, `CNAME` to a deprovisioned S3/Azure/GitHub Pages/Heroku target [G] | ✅ / 🔬 for DNS |
| Framing / opener (A32) | no `frame-ancestors` in CSP and no `X-Frame-Options`; `top\.location\s*!=\s*self\.location` frame-busters as the only defence; `<iframe` for user or third-party content without `sandbox`, or `sandbox="[^"]*allow-scripts[^"]*allow-same-origin`; `window\.open\(`/`target="_blank"` on untrusted links without `noopener` | ✅ |
| XSSI / JSONP (A33) | `req\.query\.callback`, `request\.GET\[["']callback`, `jsonp`, `JSONP_CALLBACK` reflected; cookie-authenticated GET endpoints returning JS/JSON with no token or custom header; user data served as `application/javascript` or `text/html` | ✅ |
| Third-party code (A34) | `<script src="http://`; off-origin `<script src` or `<link rel="stylesheet"` without `integrity=` and `crossorigin`; tag-manager snippets; ad iframes without `sandbox`; DNS targets answering NXDOMAIN or a provider "not found" page | ✅ / 🔬 for DNS |
| Cache and Host (A35) | authenticated responses without `Cache-Control: no-store`, or with `public`; CDN rules caching `/account`, `/api`, `/me`; `request\.get_host\(\)`, `req\.headers\.host`, `X-Forwarded-Host`, `Request\.Host`, `r\.Host` [G] used to build links, e-mails or redirects; `ALLOWED_HOSTS\s*=\s*\[["']\*["']\]`; nginx `server_name _` serving the app | ✅ |
| HTML filtered by regex (A36) | `replace\(/<.*>/`, `re\.sub\(r?["']<`, `strip_tags`, custom `sanitize\(`; unquoted attributes in templates (`=\{\{`, `=<%=` without quotes); `id=`/`name=` from user data; concatenation after a sanitiser call | ✅ |
| Internal means trusted (A37) | apps with no auth middleware justified as internal; auth on `req\.ip`/`REMOTE_ADDR`/VPN ranges only; dev servers on `0.0.0.0` with no `Host` allow-list; webpack/vite `allowedHosts: 'all'` [G] | ✅ / ⚠️ |
| Mail authentication (A38) | `dig TXT <domain>`: no `v=spf1` or one ending `+all`; no DKIM selector record; `dig TXT _dmarc.<domain>` missing or `p=none` | ✅ when DNS supplied, 🔬 otherwise |
| Unbounded requests (A39) | nginx without `client_max_body_size`/`client_body_timeout`; body-parser/`express.json()` without `limit`; `MAX_CONTENT_LENGTH` unset (Flask); `zipfile.*extractall`, `tarfile.*extractall`, `ZipArchive::extractTo`, `ZipFile.ExtractToDirectory` without size/ratio/path checks; `limit\|pageSize\|per_page` from the query with no maximum; regexes with nested quantifiers on input; XML parsers with DTDs on | ✅ |

## api

### In code

| Anti-pattern | Stack | Signal | Conf. |
|---|---|---|---|
| Shadow / zombie versions (A40) | Express/Nest | `app\.use\(["']/(v[0-9]+\|internal\|beta\|test\|legacy)`; versioned routers still mounted | ✅ |
| | Spring | `@RequestMapping\(["']/api/v[0-9]`; `@Deprecated` controllers still mapped | ✅ |
| | Django/FastAPI | `path\(["']v[0-9]+/`, `include\(`; `APIRouter\(prefix=["']/v[0-9]` | ✅ |
| | ASP.NET | `\[ApiVersion\(["'][0-9.]+["']\)\]`, `[Obsolete]` endpoints still routed | ✅ |
| | Go | `HandleFunc\(["']/v[0-9]+/`; `PathPrefix\(["']/v[0-9]` | ✅ |
| Whole object out (A41) | all | `res\.json\((user\|account\|doc\|entity\|model)\)`, `res\.send\(doc\)`; returning an `@Entity`; `return Ok\(entity\)`; DRF `fields = ["']__all__["']`; FastAPI routes without `response_model`; `model_to_dict`; Go structs encoded without `json:"-"` on sensitive fields; `SELECT \*` feeding a response; `passwordHash`, `isAdmin`, `mfa` fields in serialised types | ✅ |
| Unchecked writes (A41) | all | `Object\.assign\(.*req\.body\)`, `Model\.create\(req\.body\)`, `@RequestBody` on an entity, `[FromBody]` on an entity, `params\.permit!`, `$guarded = \[\]`, Go `json.Decode` straight into a model | ✅ |
| Unmetered consumption (A42) | all | absence of `express-rate-limit`/`@nestjs/throttler`/DRF throttles/`django-ratelimit`/bucket4j/Resilience4j/`AddRateLimiter`/`x/time/rate` on login, OTP, reset and search routes; limiter `keyGenerator` reading `x-forwarded-for`; `app\.set\(["']trust proxy["'],\s*true\)` with no proxy; `limit`/`pageSize`/`first` without a max; GraphQL server without depth/complexity limits (`graphql-depth-limit`, `graphql-query-complexity`, `AddMaxExecutionDepthRule`, gqlgen `FixedComplexityLimit`) or with `allowBatchedHttpRequests` | ✅ / ⚠️ |
| Discovery artefacts (A43) | all | FastAPI without `docs_url=None`/`openapi_url=None` in prod; `UseSwagger\(\)`/`UseSwaggerUI` or springdoc outside a development guard; `introspection:\s*true`, `graphiql`, `playground` enabled in prod config; gates on a cookie or header value (`req\.cookies\.env`, `base64` flags) | ✅ |
| Existence oracle (A16) | all | branches returning 403 for found-but-unowned and 404 for missing; `response-time`/`Server-Timing`/`X-Response-Time` middleware in prod; distinct "no such user" / "wrong password" messages | ✅ |
| Gateway as only check (A9, A5) | all | comments like "validated by gateway"/"auth at the edge"; `createProxyMiddleware\(\{.*pathRewrite` or Spring Cloud Gateway `RewritePath` built from request data; `NewSingleHostReverseProxy` with concatenated paths; internal services with no authorisation middleware | ✅ / ⚠️ |
| Readable / forgeable tokens (A7, A17) | all | `jwt\.sign\(.*,\s*["'][^"']{0,20}["']` or `\|\| ["']secret["']`; `jwt\.(verify\|decode)\(` without `algorithms`; PyJWT `verify_signature["']?:\s*False`; `ValidateIssuerSigningKey\s*=\s*false`; `jwt\.sign\(user` with a whole row; API keys in built JS bundles (`gitleaks` over `dist/`, `build/`), mobile config, or query strings | ✅ |
| Consumer-chosen flags (A11) | all | login/registration handlers reading `mfa`, `skip_verification`, `role`, `is_admin`, `verified` from the body | ✅ |

### In the OpenAPI / GraphQL schema

Spectral-style rules (Practice) — run Spectral, `vacuum` or a schema linter if one is present; otherwise
read the spec:

| Rule | Anti-pattern | Conf. |
|---|---|---|
| Every operation (or the global spec) has a `security` requirement; anonymous operations are an explicit, listed exception | A9 | ✅ |
| Request bodies set `additionalProperties: false`; privileged properties are absent from create/update schemas or `readOnly` | A41 | ✅ |
| Read and write shapes are separate schemas, or use `readOnly`/`writeOnly` | A41 | ✅ |
| Strings have `maxLength`, arrays `maxItems`, numbers `maximum`; page-size parameters have `maximum` | A39, A42 | ✅ |
| `401`, `403` and `429` responses are defined where they can occur; `Retry-After` documented | A42 | ✅ |
| No `http://` entries in `servers`; no test or dev hosts in the production spec | A20, A40 | ✅ |
| `deprecated: true` operations have a retirement date and still enforce the current controls | A40 | ✅ |
| Operations with `{id}` or tenant-scoped inputs document their refusal (403/404) | A10 | ⚠️ |
| `description` text saying "internal", "admin only", "do not use" matches an enforcing check in code | A43 | ⚠️ traced |
| GraphQL: introspection disabled in production; resolvers carry authorisation directives; depth and complexity limits configured | A43, A9, A42 | ✅ |
| Spec vs routes: generate the spec (or route list) from code and diff it against the committed one — routes missing from the spec are shadow APIs | A40 | ✅ |

### Safe verification (owned, named test environment only)

| Check | Method | Expect |
|---|---|---|
| Object-level (A10) | A-B-A: user A creates; user B reads, updates and deletes it through every method and every ID-bearing field; user A re-reads (HAPI ch10, pp.253–256) | B refused on every call; A's object unchanged |
| Function-level (A9) | the admin operations, called with a low-privilege test token and with no token | refused |
| Properties (A41) | diff response keys per role against the spec; send one extra privileged property as a test user, re-read | no unlisted keys; property ignored or `400`, never persisted |
| Versions (A40) | replay one baseline request on `/v1`, `/v2`, `/test`, `/internal` variants | the same refusal and limits everywhere, or `404`/`410` |
| Oracles (A16) | request another user's object and a non-existent ID | identical status, body and length |
| Limits (A42) | small bursts against the OTP or login endpoint on a throwaway account until `429`; repeat on a path variant and with a spoofed forwarding header | limit hit, keyed to the account, not reset by the header — stop at the limit; never sustained load |
| Docs (A43) | unauthenticated GET to the documentation and introspection paths | `401`/`404` outside development |
