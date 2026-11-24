"""The deterministic routing check: the stemmer, BM25 ranking and TF-IDF
similarity on a tiny corpus, and the three checks passing and failing on
synthetic cases and a fake tree. The check over the real repo runs as its own
CI step (python3 .github/scripts/routing.py), so it is not repeated here.
Run: python3 -m unittest discover evals/tests"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
import unittest.mock

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".github/scripts"))

import routing  # noqa: E402

CORPUS = {
    "hotfix": "Fix an urgent bug in production today; ship a patch fast with a red test.",
    "incident-fix": "Respond to an outage: contain it, roll back, repair corrupted data, write a post-mortem.",
    "ticket": "Create, update or close a ticket or issue in Jira, Linear or Azure DevOps.",
    "dbaudit": "Audit a relational database schema for normalization and key problems.",
}


def case(cid, skill, prompt, yes=True, expected="same"):
    return {"id": cid, "skill": skill, "should_trigger": yes, "split": "train", "prompt": prompt,
            "expected": skill if expected == "same" else expected}


class Stemmer(unittest.TestCase):
    def test_porter_reference_words(self):
        # From Porter's 1980 paper and its reference vocabulary.
        for word, want in {"caresses": "caress", "ponies": "poni", "cats": "cat", "feed": "feed",
                           "agreed": "agre", "plastered": "plaster", "motoring": "motor", "sing": "sing",
                           "hopping": "hop", "falling": "fall", "filing": "file", "happy": "happi",
                           "relational": "relat", "generalization": "gener", "adjustment": "adjust",
                           "adoption": "adopt", "goodness": "good"}.items():
            self.assertEqual(routing.stem(word), want, word)

    def test_inflections_meet(self):
        self.assertEqual({routing.stem(w) for w in ("review", "reviews", "reviewing", "reviewed")}, {"review"})
        self.assertEqual(routing.stem("incidents"), routing.stem("incident"))

    def test_tokens_drop_stopwords_and_split_hyphens(self):
        self.assertEqual(routing.tokens("Can you review the peer-review of THIS?"),
                         ["review", "peer", "review"])


class Ranking(unittest.TestCase):
    def setUp(self):
        self.ix = routing.Index(routing.documents(CORPUS))

    def test_the_matching_document_ranks_first(self):
        self.assertEqual(self.ix.rank("prod is down, we need to roll back")[0][0], "incident-fix")
        self.assertEqual(self.ix.rank("open a Jira issue for this")[0][0], "ticket")
        self.assertEqual(self.ix.rank("is our schema normalized?")[0][0], "dbaudit")

    def test_no_overlap_scores_zero_and_ranks_stably(self):
        ranked = self.ix.rank("the weather in Lisbon")
        self.assertTrue(all(s == 0 for _, s in ranked))
        self.assertEqual([n for n, _ in ranked], sorted(CORPUS))

    def test_rarer_terms_weigh_more(self):
        # "bug" is in one document; "fix" is in two (hotfix, incident-fix via its name).
        self.assertGreater(self.ix.idf["bug"], self.ix.idf["fix"])

    def test_cosine(self):
        self.assertAlmostEqual(self.ix.cosine("hotfix", "hotfix"), 1.0)
        self.assertEqual(self.ix.cosine("ticket", "dbaudit"), 0.0)
        sims = self.ix.pairs()
        self.assertEqual(len(sims), 6)
        self.assertEqual(sims, sorted(sims, key=lambda p: -p[0]))


class Checks(unittest.TestCase):
    def setUp(self):
        self.ix = routing.Index(routing.documents(CORPUS))

    def run_checks(self, cases, k=1, collision=0.99, known=None):
        return routing.failures(self.ix, cases, k=k, collision=collision, known=known or {})

    def test_clean_cases_pass(self):
        msgs, notes = self.run_checks([
            case("hotfix-yes", "hotfix", "an urgent bug, can you ship a patch today?"),
            case("hotfix-no", "hotfix", "prod is down and data is corrupted", yes=False, expected="incident-fix"),
        ])
        self.assertEqual((msgs, notes), ([], []))

    def test_positive_outside_top_k_fails(self):
        c = case("ticket-yes", "ticket", "audit our database schema keys")
        msgs, _ = self.run_checks([c], k=1)
        self.assertEqual(len(msgs), 1)
        self.assertIn("ticket-yes: ticket ranks", msgs[0])
        self.assertEqual(self.run_checks([c], k=4)[0], [])

    def test_near_miss_ranked_first_fails(self):
        msgs, _ = self.run_checks([case("hotfix-no", "hotfix", "urgent bug patch", yes=False,
                                        expected="incident-fix")])
        self.assertEqual(len(msgs), 1)
        self.assertIn("near-miss ranks hotfix first (expected incident-fix)", msgs[0])

    def test_near_miss_needing_no_skill_is_not_failed(self):
        # A lexical ranker always ranks something first; it has no "none" to pick.
        msgs, _ = self.run_checks([case("hotfix-no", "hotfix", "urgent bug patch", yes=False,
                                        expected=None)])
        self.assertEqual(msgs, [])

    def test_collision_fails_above_threshold(self):
        top = self.ix.pairs()[0]
        msgs, _ = self.run_checks([], collision=top[0] - 0.001)
        self.assertTrue(any(f"{top[1]} and {top[2]}: descriptions too alike" in m for m in msgs))
        self.assertEqual(self.run_checks([], collision=top[0])[0], [])

    def test_known_failure_is_excused_then_stale(self):
        bad = case("hotfix-no", "hotfix", "urgent bug patch", yes=False, expected="incident-fix")
        msgs, notes = self.run_checks([bad], known={"hotfix-no": "why"})
        self.assertEqual(msgs, [])
        self.assertEqual(notes, ["known failure hotfix-no: why"])
        good = case("hotfix-no", "hotfix", "close the Jira ticket", yes=False, expected="ticket")
        msgs, _ = self.run_checks([good], known={"hotfix-no": "why"})
        self.assertIn("passes now; remove it from KNOWN_FAILURES", msgs[0])
        msgs, _ = self.run_checks([], known={"gone": "why"})
        self.assertIn("KNOWN_FAILURES names gone", msgs[0])

    def test_unknown_skill_is_reported(self):
        msgs, _ = self.run_checks([case("x-yes", "nosuch", "anything")])
        self.assertIn("names skill 'nosuch'", msgs[0])


class Main(unittest.TestCase):
    """main() against a fake tree: frontmatter parsed as registry.py does, exit codes."""

    def tree(self, cases):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        for name, desc in CORPUS.items():
            md = root / "skills/fam" / name / "SKILL.md"
            md.parent.mkdir(parents=True)
            md.write_text(f'---\nname: {name}\ndescription: "{desc}"\n---\nbody\n')
        (root / "evals/trigger").mkdir(parents=True)
        (root / routing.CASES).write_text(json.dumps({"cases": cases}))
        return root

    def main(self, root, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), unittest.mock.patch.object(routing, "KNOWN_FAILURES", {}):
            code = routing.main(["--root", str(root), *args])
        return code, out.getvalue()

    def test_descriptions_are_read_from_frontmatter(self):
        root = self.tree([])
        self.assertEqual(routing.descriptions(root), CORPUS)

    def test_exit_codes_and_report(self):
        ok = self.tree([case("t-yes", "ticket", "close the Linear issue")])
        code, out = self.main(ok, "--report")
        self.assertEqual(code, 0)
        self.assertIn("4 skills indexed", out)
        self.assertIn("Slack", out)
        self.assertIn("routing: 4 skills; 1 should-trigger", out)
        bad = self.tree([case("t-no", "ticket", "close the Linear issue", yes=False, expected="hotfix")])
        code, out = self.main(bad)
        self.assertEqual(code, 1)
        self.assertIn("✗ t-no: near-miss ranks ticket first", out)


if __name__ == "__main__":
    unittest.main()
