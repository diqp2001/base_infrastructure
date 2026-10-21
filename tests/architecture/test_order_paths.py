"""BI-005: one order path to IBKR, guarded by the connected-account check.

Every connection path (project trainers, broker_factory, api_service, the hard-coded 7497 defaults) may
read data, but an order reaches TWS only through IBTWSClient.place_order, which verifies the account TWS
is logged into against IBKR_ACCOUNT_MODE before sending. A second placeOrder call would bypass it."""

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"
ALLOWED = ("src/application/services/misbuffet/brokers/ibkr/IBTWSClient.py", "place_order")


def _order_calls():
    """(file, enclosing function, line) of every `.placeOrder(...)` / `placeOrder(...)` call in src."""
    found = []
    for py in SRC.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = py.relative_to(SRC.parent).as_posix()
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(func):
                if isinstance(node, ast.Call):
                    name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                    if name == "placeOrder":
                        found.append((rel, func.name, node.lineno))
    return found


def test_only_ibtwsclient_place_order_sends_orders():
    calls = _order_calls()
    assert calls, "placeOrder call not found: update this test if the order path moved"
    assert {(f, fn) for f, fn, _ in calls} == {ALLOWED}, calls


def test_the_order_path_checks_the_connected_account_before_sending():
    path = SRC.parent / ALLOWED[0]
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == ALLOWED[1])
    lines = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            lines.setdefault(name, node.lineno)
    assert "verify_connected_accounts" in lines, "IBTWSClient.place_order must call verify_connected_accounts"
    assert lines["verify_connected_accounts"] < lines["placeOrder"]
