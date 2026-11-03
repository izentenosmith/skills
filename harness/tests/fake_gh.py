#!/usr/bin/env python3
"""A stand-in for `gh` so prreview.py's --pr and --post paths can be tested without GitHub.

FAKE_GH_HEAD is the PR's head sha, FAKE_GH_BODY its description. Every call is appended to FAKE_GH_LOG as
one JSON line: argv, and the parsed --input payload for `gh api`.
"""
import json
import os
import sys

argv = sys.argv[1:]
entry = {"argv": argv}
if argv[:1] == ["api"] and "--input" in argv:
    with open(argv[argv.index("--input") + 1]) as fh:
        entry["input"] = json.load(fh)
if os.environ.get("FAKE_GH_LOG"):
    with open(os.environ["FAKE_GH_LOG"], "a") as fh:
        fh.write(json.dumps(entry) + "\n")

if argv[:2] == ["pr", "view"]:
    fields = argv[argv.index("--json") + 1]
    if "comments" in fields:
        print(json.dumps({"comments": [{"body": "Fixed in the next commit."}], "reviews": []}))
    else:
        print(json.dumps({"number": int(argv[2]), "title": "Apply percentage discounts",
                          "body": os.environ.get("FAKE_GH_BODY", ""), "url": "https://example.test/pr/7",
                          "baseRefName": "main", "headRefOid": os.environ["FAKE_GH_HEAD"], "commits": [],
                          "state": "OPEN", "isDraft": False}))
elif argv[:2] == ["issue", "view"]:
    print(json.dumps({"number": int(argv[2]), "title": "Discounts", "body": "Round to cents."}))
elif argv[:2] == ["repo", "view"]:
    print("acme/shop")
elif argv[:1] == ["api"]:
    print(json.dumps({"id": 1234}))
else:
    sys.exit(f"fake_gh: unexpected {argv}")
