"""Fundamentals (owner, 2026-11-02 and 2026-11-11, TODO.md): a theme of small lessons that say what a thing is
for and when it is used, with no practice and no fights. Each path pulls in its own fundamentals, which open
the path's lessons; Fundamentals alone gives every fundamental and no other path."""

import unittest

from bashou import challenges, fight, lesson, skills, state
from bashou.adventure import quiz, world

LESSONS = lesson.load("en")
BY_ID = {le["id"]: le for le in LESSONS}

# fundamental: (paths that pull it in, lessons it opens). The plan in TODO.md, as the owner decided it.
PLAN = {
    "fund_addresses": ({"network", "linux"}, {"network", "fund_osi"}),
    "fund_osi": ({"network"}, {"ip_addr"}),
    "fund_arp": ({"network"}, {"net_debug"}),
    "fund_tcp_udp": ({"network"}, {"tcp", "dns_tools"}),
    "fund_multicast": ({"network"}, set()),
    "fund_crypto": ({"linux", "network"}, {"keys"}),
    "fund_users": ({"linux", "debian", "rocky"}, {"users", "permissions"}),
    "fund_processes": ({"linux"}, {"processes", "services"}),
    "fund_complexity": ({"logic"}, {"logic_cost"}),
    "fund_codes": ({"logic"}, {"logic_ecc"}),
    "fund_git": ({"bash"}, {"git"}),
    "fund_regex": ({"bash"}, {"regex"}),
    "fund_databases": ({"sql"}, {"sql_select"}),
    "fund_code": ({"c", "rust", "python"}, {"compilation", "py_start", "rust_vars"}),
    "ai_context": ({"ai"}, {"ai_plan"}),
    # Owner, 2026-11-12: the five proposals of the 2026-11-11 audit, before closing Bashou until the Rust rewrite.
    "fund_text": ({"bash"}, {"streams", "pipes"}),
    "fund_automation": ({"script", "python"}, {"scripts", "py_start"}),
    "fund_packages": ({"debian", "rocky"}, {"packages"}),
    "fund_memory": ({"c", "rust"}, {"stack_heap", "rust_vars"}),
    "fund_ci": ({"cicd"}, {"pipeline"}),
}

COMMON = {le["id"] for le in LESSONS if not lesson.skills_of(le)}


def player(picked):
    s = state.default()
    s["skills"] = picked
    s.setdefault("settings", {})["os"] = "both"
    return s


class FundamentalsTest(unittest.TestCase):
    def test_a_skill_and_a_topic(self):
        self.assertIn("fundamentals", skills.SKILLS)
        self.assertEqual(world.TOPICS["fundamentals"][2], "Layer Lich")
        self.assertGreaterEqual(len(quiz.bank("fundamentals", "en")), 3 * len(PLAN))

    def test_every_planned_fundamental_and_who_pulls_it(self):
        found = {le["id"] for le in LESSONS if "fundamentals" in lesson.skills_of(le)}
        self.assertEqual(found, set(PLAN))
        for lid, (paths, _) in PLAN.items():
            with self.subTest(lesson=lid):
                self.assertEqual(set(lesson.skills_of(BY_ID[lid])), paths | {"fundamentals"})

    def test_no_fights_and_right_answers_pass_them(self):
        for lid in PLAN:
            with self.subTest(lesson=lid):
                le = BY_ID[lid]
                self.assertEqual(le.get("fights", []), [], "owner: lessons and questions only")
                self.assertGreaterEqual(len(le.get("questions", [])), lesson.QUIZ_PASS)
                self.assertTrue(any(m.startswith("answered ") for m in le["masters"]),
                                "mastered with right answers, like the AI lessons")
        self.assertFalse([c.id for c in challenges.ALL if c.skill == "fundamentals"])

    def test_they_open_the_path_lessons(self):
        for lid, (_, opens) in PLAN.items():
            for after in opens:
                with self.subTest(fundamental=lid, opens=after):
                    self.assertIn(lid, BY_ID[after].get("after", []))

    def test_they_need_no_more_shell_than_the_common_lessons(self):
        for lid in PLAN:
            for before in BY_ID[lid].get("after", []):
                with self.subTest(lesson=lid, after=before):
                    self.assertTrue(before in COMMON or before in PLAN, before)

    def test_fundamentals_alone(self):
        s = player(["fundamentals"])
        shown = {le["id"] for le in lesson.shown(s, LESSONS)}
        self.assertEqual(shown, COMMON | set(PLAN))
        self.assertEqual(fight.remaining(s), [])

    def test_a_path_pulls_its_own_fundamentals(self):
        for k in skills.SKILLS:
            if k == "fundamentals":
                continue
            with self.subTest(path=k):
                shown = {le["id"] for le in lesson.shown(player([k]), LESSONS)}
                self.assertEqual(shown & set(PLAN), {lid for lid, (paths, _) in PLAN.items() if k in paths})

    def test_the_owner_examples(self):
        network = {le["id"] for le in lesson.shown(player(["network"]), LESSONS)}
        self.assertTrue({"fund_osi", "fund_arp", "fund_tcp_udp"} <= network)
        logic = {le["id"] for le in lesson.shown(player(["logic"]), LESSONS)}
        self.assertTrue({"fund_complexity", "fund_codes"} <= logic)
        self.assertFalse(logic & {"fund_osi", "fund_arp", "fund_tcp_udp", "fund_multicast"})


if __name__ == "__main__":
    unittest.main()
