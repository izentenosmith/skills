Answer key for `hotfix-jvm/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.


# hotfix-jvm — `hotfix` on a JVM service with no build tool (eval 9)

`Paginator.pageCount` uses integer division, so a partial last page is dropped.

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | Two callers: `ReportExporter` (the report) and `ApiController` (`totalPages`) | adds a `+1` in the exporter's loop |
| 2 | No Maven/Gradle; tests run through `./run-tests.sh`, which is what CI runs | goes looking for a build tool, or runs `javac` ad hoc and calls it the suite |
| 3 | `CONTRIBUTING.md`: merge requests; tags deploy to **staging**, production is a manual promote | ships without planning staging verification, or ignores the MR convention |
| 4 | `PaginatorTest` covers only exact multiples (`100 / 10`) | can't say why no test caught it |
