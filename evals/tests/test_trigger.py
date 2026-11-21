"""The triggering eval: reading a stream-json transcript for the first skill a
run picked, and the summary built from the per-run results. The transcripts in
data/trigger/ are recorded runs (claude 2.1.295), trimmed to the fields the
parser reads and with machine paths replaced.
Run: python3 -m unittest discover evals/tests"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data" / "trigger"
sys.path.insert(0, str(HERE.parent / "trigger"))

import run_trigger as rt  # noqa: E402


def events(name):
    return rt.parse_events((DATA / name).read_text().splitlines())


def assistant(mid, *blocks, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"id": mid, "content": list(blocks)}}


def tool(name, **inp):
    return {"type": "tool_use", "name": name, "input": inp}


class Transcript(unittest.TestCase):
    def test_skill_tool_call_is_the_pick(self):
        ev = events("skill-then-read.jsonl")
        self.assertEqual(rt.first_skill(ev), {"skill": "hotfix", "via": "Skill", "turn": 1})
        self.assertIn("hotfix", rt.listed_skills(ev))

    def test_run_stopped_at_the_skill_call(self):
        ev = events("stopped-at-skill.jsonl")
        self.assertEqual(rt.first_skill(ev)["skill"], "hotfix")
        usage, cost = rt.usage_of(ev)
        self.assertIsNone(cost)                      # killed before its result event
        self.assertEqual(usage["cache_creation_input_tokens"], 12672)

    def test_no_skill_picked(self):
        ev = events("no-skill.jsonl")
        pick = rt.first_skill(ev)
        self.assertEqual((pick["skill"], pick["via"]), (None, None))
        self.assertEqual(pick["turn"], 3)            # three messages, more content blocks
        self.assertGreater(rt.usage_of(ev)[1], 0)

    def test_usage_counts_a_message_once(self):
        ev = events("skill-then-read.jsonl")
        once = {}
        for e in ev:
            if e["type"] == "assistant":
                once[e["message"]["id"]] = e["message"]["usage"]["output_tokens"]
        self.assertEqual(rt.usage_of(ev)[0]["output_tokens"], sum(once.values()))

    def test_reading_a_staged_skill_file_counts(self):
        ev = [assistant("m1", tool("Glob", pattern="*")),
              assistant("m2", tool("Read", file_path="/tmp/x/skills-home/.claude/skills/dbaudit/SKILL.md")),
              assistant("m3", tool("Skill", skill="dbdesign"))]
        self.assertEqual(rt.first_skill(ev), {"skill": "dbaudit", "via": "Read", "turn": 2})

    def test_reading_a_skills_other_files_does_not(self):
        ev = [assistant("m1", tool("Read", file_path="/tmp/x/.claude/skills/hotfix/discovery.md"))]
        self.assertIsNone(rt.first_skill(ev)["skill"])

    def test_plugin_prefix_and_subagents(self):
        ev = [assistant("s1", tool("Skill", skill="ticket"), parent="toolu_1"),
              assistant("m1", tool("Skill", skill="repo:backlog"))]
        self.assertEqual(rt.first_skill(ev)["skill"], "backlog")

    def test_broken_lines_are_dropped(self):
        ev = rt.parse_events(['{"type": "system", "subtype": "init", "skills": ["a"]}', "", '{"type": "assi', "[1]"])
        self.assertEqual(len(ev), 1)
        self.assertEqual(rt.listed_skills(ev), ["a"])
        self.assertIsNone(rt.listed_skills([]))


def result(skill, expected, picked, split="train", status="ok"):
    case = {"skill": skill, "should_trigger": expected == skill, "expected": expected}
    r = dict(case, split=split, picked=picked, status=status, outcome=None, expected_ok=False)
    if status == "ok":
        r.update(rt.outcome(case, picked))
    return r


class Summary(unittest.TestCase):
    def test_outcomes(self):
        o = lambda r: (r["outcome"], r["expected_ok"])
        self.assertEqual(o(result("hotfix", "hotfix", "hotfix")), ("hit", True))
        self.assertEqual(o(result("hotfix", "hotfix", "incident-fix")), ("miss", False))
        self.assertEqual(o(result("hotfix", "hotfix", None)), ("miss", False))
        self.assertEqual(o(result("hotfix", "incident-fix", "hotfix")), ("false_trigger", False))
        self.assertEqual(o(result("hotfix", "incident-fix", "incident-fix")), ("quiet", True))
        # Left the skill under test alone, but did not find the neighbour either.
        self.assertEqual(o(result("hotfix", "incident-fix", None)), ("quiet", False))
        self.assertEqual(o(result("hotfix", None, None)), ("quiet", True))

    def test_rates_and_confusion_per_split(self):
        rs = [result("hotfix", "hotfix", "hotfix"),
              result("hotfix", "hotfix", "incident-fix"),
              result("hotfix", "incident-fix", "hotfix"),
              result("hotfix", None, None),
              result("ticket", "ticket", None, status="error"),
              result("ticket", "ticket", "ticket", split="heldout"),
              result("ticket", "backlog", "backlog", split="heldout")]
        s = rt.summarize(rs)
        tr, ho = s["train"], s["heldout"]
        self.assertEqual((tr["hits"], tr["should"], tr["trigger_rate"]), (1, 2, 0.5))
        self.assertEqual((tr["false_triggers"], tr["should_not"], tr["false_trigger_rate"]), (1, 2, 0.5))
        self.assertEqual((tr["runs"], tr["errors"]), (5, 1))
        self.assertEqual(tr["per_skill"], {"hotfix": {"should": 2, "hits": 1, "should_not": 2, "false_triggers": 1}})
        self.assertEqual(tr["confusion"], {"(none)": {"(none)": 1},
                                           "hotfix": {"hotfix": 1, "incident-fix": 1},
                                           "incident-fix": {"hotfix": 1}})
        self.assertEqual((ho["trigger_rate"], ho["false_trigger_rate"], ho["expected_ok_rate"]), (1.0, 0.0, 1.0))
        text = rt.render(s, {"model": "m", "reps": 1})
        self.assertIn("| train | 1/2 (50%) | 1/2 (50%) |", text)
        self.assertIn("| hotfix | incident-fix ✗ | 1 |", text)

    def test_empty_split_has_no_rate(self):
        s = rt.summarize([result("hotfix", "hotfix", "hotfix")])
        self.assertIsNone(s["heldout"]["trigger_rate"])
        self.assertIn("n/a", rt.render(s, {}))


class Cases(unittest.TestCase):
    def setUp(self):
        self.cases = rt.load_cases()

    def test_balanced_and_split(self):
        skills = {c["skill"] for c in self.cases}
        self.assertGreaterEqual(len(skills), 8)
        for skill in skills:
            for should in (True, False):
                group = [c for c in self.cases if c["skill"] == skill and c["should_trigger"] is should]
                self.assertEqual(len(group), 3, (skill, should))
                self.assertEqual(sorted(c["split"] for c in group), ["heldout", "train", "train"])

    def test_cases_name_real_skills_and_never_the_skill(self):
        names = set(rt.repo_skills())
        for c in self.cases:
            self.assertIn(c["skill"], names)
            self.assertTrue(c["expected"] is None or c["expected"] in names, c["id"])
            # A prompt that names a skill tests nothing about its description.
            words = set(c["prompt"].lower().replace("/", " ").split())
            self.assertFalse(words & {c["skill"], c["expected"] or c["skill"]}, c["id"])

    def test_select(self):
        self.assertEqual({c["split"] for c in rt.select(self.cases, "heldout")}, {"heldout"})
        self.assertEqual(len(rt.select(self.cases, "all", {"hotfix"})), 6)
        self.assertEqual([c["id"] for c in rt.select(self.cases, ids={"ticket-no-2"})], ["ticket-no-2"])


class Staging(unittest.TestCase):
    def test_stage_keeps_skills_out_of_the_working_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            work, home, names = rt.stage(tmp)
            self.assertEqual(list(work.iterdir()), [])
            self.assertEqual(sorted(p.parent.name for p in home.glob(".claude/skills/*/SKILL.md")), sorted(names))
            self.assertIn("hotfix", names)

    def test_dry_run_touches_nothing(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(rt.main(["--dry-run", "--model", "haiku", "--split", "train"]), 0)
        out = buf.getvalue()
        self.assertIn("76 cases × 1 rep(s) = 76 runs", out)
        self.assertIn("estimated cost", out)
        self.assertIn("nothing staged, nothing run", out)

    def test_description_hash_follows_the_description_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "SKILL.md"
            p.write_text("---\nname: x\ndescription: one\n---\nbody\n")
            a = rt.description_hash(p)
            p.write_text("---\nname: x\ndescription: one\n---\nanother body\n")
            self.assertEqual(a, rt.description_hash(p))
            p.write_text("---\nname: x\ndescription: two\n---\nbody\n")
            self.assertNotEqual(a, rt.description_hash(p))


if __name__ == "__main__":
    unittest.main()
