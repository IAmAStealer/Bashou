"""Imports go one way: a module never imports, even inside a function, one that imports it back
(directly or through others). A loop hid behind imports inside functions until one ran in the wrong
order; it also made every module need all the others to be tested."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "bashou"


def name_of(path):
    parts = list(path.relative_to(ROOT.parent).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def graph():
    """module -> the Bashou modules it imports (anywhere in the file). Importing a.b also runs a."""
    modules = {name_of(p): p for p in ROOT.rglob("*.py")}
    edges = {}
    for mod, path in modules.items():
        package = mod if path.name == "__init__.py" else mod.rpartition(".")[0]
        found = edges.setdefault(mod, set())
        for node in ast.walk(ast.parse(path.read_text())):
            if not (isinstance(node, ast.ImportFrom) and node.level):
                continue
            base = package.split(".")[:len(package.split(".")) - node.level + 1]
            target = ".".join(base + ([node.module] if node.module else []))
            for alias in node.names:
                full = f"{target}.{alias.name}"
                name = full if full in modules else target
                while name and name != mod:
                    if name in modules and not mod.startswith(name + "."):
                        found.add(name)
                    name = name.rpartition(".")[0]
    return edges


def loops(edges):
    """The groups of modules that import each other (Tarjan's strongly connected components)."""
    index, low, stack, found, counter = {}, {}, [], [], [0]

    def visit(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        for w in edges.get(v, ()):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            group = []
            while True:
                w = stack.pop()
                group.append(w)
                if w == v:
                    break
            if len(group) > 1:
                found.append(sorted(group))

    for v in sorted(edges):
        if v not in index:
            visit(v)
    return found


class LayersTest(unittest.TestCase):
    def test_no_import_loops(self):
        edges = graph()
        report = [f"{group}: " + ", ".join(f"{a} -> {b}" for a in group for b in sorted(edges[a]) if b in group)
                  for group in loops(edges)]
        self.assertEqual(report, [])

    def test_the_save_and_translations_stay_low(self):
        """i18n and the save are used by everything: they import no game module above them."""
        edges = graph()
        self.assertEqual(edges["bashou.i18n"], set())
        self.assertLessEqual(edges["bashou.state"], {"bashou.i18n", "bashou.creatures", "bashou.achievements",
                                                     "bashou.render", "bashou.which"})

    def test_loops_are_found(self):
        self.assertEqual(loops({"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"a"}}), [["a", "b", "c"]])


if __name__ == "__main__":
    unittest.main()
