"""
Import cycles between sibling packages of src/, from the static import graph (grimp).

For every package P, two of its children a, b are linked a -> b when any module inside a imports
any module inside b. A cycle is a strongly connected group of >= 2 siblings. Groups are compared
as sets of names, so the result does not depend on which import a tool would nominate to break it.

    python -m tests.architecture.import_cycles            # print current cycles
    python -m tests.architecture.import_cycles --update   # rewrite the committed baseline
"""

import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Set

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "import_cycles_baseline.json")


def sibling_edges(graph) -> Dict[str, Dict[str, Set[str]]]:
    """package -> child -> {children it imports}, from every direct import in src."""
    edges: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    for importer in graph.modules:
        for imported in graph.find_modules_directly_imported_by(importer):
            a, b = importer.split("."), imported.split(".")
            common = 0
            while common < min(len(a), len(b)) and a[common] == b[common]:
                common += 1
            if common == 0 or common >= len(a) or common >= len(b):
                continue                       # unrelated roots, or one contains the other
            package = ".".join(a[:common])
            edges[package][a[common]].add(b[common])
    return edges


def strongly_connected(nodes: Dict[str, Set[str]]) -> List[List[str]]:
    """Tarjan: groups of >= 2 mutually reachable nodes, each sorted, list sorted."""
    index, low, stack, on_stack, out = {}, {}, [], set(), []
    counter = [0]
    all_nodes = set(nodes) | {n for vs in nodes.values() for n in vs}

    def visit(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in nodes.get(v, ()):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            group = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                group.append(w)
                if w == v:
                    break
            if len(group) > 1:
                out.append(sorted(group))

    sys.setrecursionlimit(max(10_000, sys.getrecursionlimit()))
    for v in sorted(all_nodes):
        if v not in index:
            visit(v)
    return sorted(out)


def current_cycles() -> Dict[str, List[List[str]]]:
    import grimp
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    graph = grimp.build_graph("src", cache_dir=None)
    cycles = {}
    for package, nodes in sorted(sibling_edges(graph).items()):
        groups = strongly_connected(nodes)
        if groups:
            cycles[package] = groups
    return cycles


def load_baseline() -> Dict[str, List[List[str]]]:
    with open(BASELINE, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    found = current_cycles()
    if "--update" in sys.argv:
        with open(BASELINE, "w", encoding="utf-8") as f:
            json.dump(found, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"baseline written: {sum(len(v) for v in found.values())} cycle group(s) in {len(found)} package(s)")
    else:
        print(json.dumps(found, indent=2, sort_keys=True))
