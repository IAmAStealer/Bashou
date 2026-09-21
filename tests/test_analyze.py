import unittest

from bashou.analyze import analyze


class AnalyzeTest(unittest.TestCase):
    def test_pipeline(self):
        a = analyze("cat log | grep ERROR | sort | uniq -c")
        self.assertEqual(a.tools, {"cat", "grep", "sort", "uniq"})
        self.assertEqual(a.pipes, 4)

    def test_quotes_hide_operators(self):
        a = analyze("awk -F'|' '{ s += $(NF) } END { print s }' data.csv")
        self.assertEqual(a.tools, {"awk"})
        self.assertEqual(a.pipes, 1)
        self.assertNotIn("subst", a.constructs)

    def test_wrappers(self):
        self.assertEqual(analyze("sudo find / -name x").tools, {"sudo", "find"})
        self.assertEqual(analyze("find . -name '*.log' | xargs -I{} rm {}").tools, {"find", "xargs", "rm"})
        self.assertEqual(analyze("strace -e trace=open -o out ls").tools, {"strace", "ls"})
        self.assertEqual(analyze("LANG=C sort file").tools, {"sort"})

    def test_substitutions(self):
        a = analyze('echo "today: $(date +%F)" && diff <(ls a) <(ls b)')
        self.assertEqual(a.tools, {"echo", "date", "diff", "ls"})
        self.assertEqual(a.constructs, {"subst", "procsub"})
        self.assertNotIn("subst", analyze("echo $((1 + 2))").constructs)

    def test_loops_and_redirects(self):
        a = analyze("for f in *.txt; do wc -l \"$f\" 2>&1; done")
        self.assertEqual(a.tools, {"wc"})
        self.assertEqual(a.constructs, {"loop", "stderr"})
        self.assertIn("loop", analyze("while read -r l; do echo $l; done < f").constructs)

    def test_heredoc_body_is_not_commands(self):
        a = analyze("cat <<EOF > out\nrm -rf everything\nEOF\nls")
        self.assertEqual(a.tools, {"cat", "ls"})
        self.assertIn("heredoc", a.constructs)

    def test_paths_and_comments(self):
        self.assertEqual(analyze("/usr/bin/find . # grep here").tools, {"find"})
        self.assertEqual(analyze("ls > out.txt 2>/dev/null").commands, [("ls", [])])


if __name__ == "__main__":
    unittest.main()
